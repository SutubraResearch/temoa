#!/usr/bin/env python3
"""
Create a 4-week subset from a full 52-week legacy Temoa DB.

Keeps seasons 1-4 and removes seasons 5-52 from time_season and all time-indexed
tables. Output is a smaller DB suitable for faster migration testing.

CRITICAL: This script adjusts ALL required parameters for a time-subset DB:
  1. Deletes data for removed seasons
  2. Rescales SegFrac to sum to 1.0
  3. Rescales DemandSpecificDistribution to sum to 1.0
  4. Adjusts Demand to reflect actual demand for kept seasons

NOTE: After migration to v4, you must ALSO set:
  - days_per_period = 28 (in metadata)
  - capacity_to_activity = 672 (28 days × 24 hours)

See MIGRATION_LOG.md section "CRITICAL: Creating a Time-Subset Database" for details.

Usage:
  python create_4week_subset.py <source.sqlite> <output_4week.sqlite>

Example:
  python create_4week_subset.py \\
    data_files/server_current_policies_noIRA_52_week_retire_HighGasCapex.sqlite \\
    data_files/server_current_policies_4week.sqlite
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from pathlib import Path


def parse_sort_key(label: str) -> tuple[int, str]:
    """Natural-ish ordering for labels like h1, h2, s1, s2, ..."""
    prefix = ''.join(ch for ch in str(label) if not ch.isdigit())
    digits = ''.join(ch for ch in str(label) if ch.isdigit())
    if digits:
        return (int(digits), prefix)
    return (10**9, str(label))


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Create a time-subset from a full 52-week legacy Temoa DB.',
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('source', help='Path to source 52-week SQLite DB')
    parser.add_argument('output', help='Path for output subset SQLite DB')
    parser.add_argument(
        '--weeks', type=int, default=4, help='Number of weeks to keep (default: 4)'
    )
    parser.add_argument(
        '--week-start',
        type=int,
        default=1,
        help='First week to keep, 1-based (default: 1). E.g. --week-start 30 --weeks 6 keeps weeks 30-35.',
    )
    args = parser.parse_args()

    source = Path(args.source)
    output = Path(args.output)
    weeks = args.weeks
    week_start = args.week_start
    start_idx = week_start - 1  # convert to 0-based

    if not source.exists():
        print(f'Error: source DB not found: {source}')
        sys.exit(1)

    print(f'Copying {source} → {output}')
    shutil.copy2(source, output)

    conn = sqlite3.connect(output)
    conn.execute('PRAGMA foreign_keys = OFF')

    # Get all seasons and sort (same logic as migrate_to_v4)
    seasons = [r[0] for r in conn.execute('SELECT t_season FROM time_season').fetchall()]
    sorted_seasons = sorted(seasons, key=parse_sort_key)

    if start_idx + weeks > len(sorted_seasons):
        print(
            f'Error: week_start={week_start} + weeks={weeks} = {week_start + weeks - 1} '
            f'exceeds available seasons ({len(sorted_seasons)})'
        )
        sys.exit(1)

    if len(sorted_seasons) <= weeks and start_idx == 0:
        print(f'Warning: only {len(sorted_seasons)} seasons in source, keeping all')
        kept = sorted_seasons
    else:
        kept = sorted_seasons[start_idx : start_idx + weeks]

    to_remove = [s for s in sorted_seasons if s not in kept]
    print(f'Keeping seasons: {kept}')
    print(
        f'Removing seasons: {to_remove[:10]}{"..." if len(to_remove) > 10 else ""} ({len(to_remove)} total)'
    )

    if not to_remove:
        print(f'Nothing to remove (source already has ≤{weeks} seasons).')
        conn.close()
        print(f'\n✓ Created {weeks}-week subset: {output}')
        return

    placeholders = ','.join('?' * len(to_remove))
    kept_placeholders = ','.join('?' * len(kept))

    # =========================================================================
    # STEP 1: Calculate demand adjustment BEFORE deleting DSD rows
    # =========================================================================
    print('\n--- Step 1: Calculate demand for kept seasons ---')

    # Get the fraction of demand in kept seasons for each (region, period, demand)
    demand_adjustments = {}
    try:
        cur = conn.execute(
            f"""
            SELECT regions, periods, demand_name, SUM(dds) as kept_fraction
            FROM DemandSpecificDistribution
            WHERE season_name IN ({kept_placeholders})
            GROUP BY regions, periods, demand_name
        """,
            tuple(kept),
        )

        for row in cur.fetchall():
            regions, periods, demand_name, kept_fraction = row
            demand_adjustments[(regions, periods, demand_name)] = kept_fraction

        print(
            f'  Calculated demand fractions for {len(demand_adjustments)} (region, period, demand) combinations'
        )
    except sqlite3.OperationalError as e:
        if 'no such table' not in str(e).lower():
            raise
        print('  DemandSpecificDistribution table not found, skipping demand adjustment')

    # Fallback for demand commodities without DSD (e.g., DEMAND_CRYPTO, DEMAND_SERVERS)
    # These have no DemandSpecificDistribution entries, so we scale by the SegFrac sum
    # for kept seasons (= 4/52 for uniform SegFrac).
    try:
        all_demands = conn.execute(
            'SELECT DISTINCT regions, periods, demand_comm FROM Demand'
        ).fetchall()
        sf_fracs = {}
        for row in conn.execute(
            f"""SELECT periods, SUM(segfrac) FROM SegFrac
                WHERE season_name IN ({kept_placeholders}) GROUP BY periods""",
            tuple(kept),
        ).fetchall():
            sf_fracs[row[0]] = row[1]

        fallback_count = 0
        for regions, periods, demand_comm in all_demands:
            if (regions, periods, demand_comm) not in demand_adjustments:
                frac = sf_fracs.get(periods, 1.0)
                demand_adjustments[(regions, periods, demand_comm)] = frac
                fallback_count += 1
                print(
                    f'  {regions}/{periods}/{demand_comm}: no DSD, '
                    f'using SegFrac fraction {frac:.6f}'
                )
        if fallback_count:
            print(f'  Applied SegFrac fallback to {fallback_count} demand commodities')
    except sqlite3.OperationalError:
        pass  # Demand or SegFrac table missing — nothing to do

    # =========================================================================
    # STEP 2: Delete rows for removed seasons
    # =========================================================================
    print('\n--- Step 2: Delete data for removed seasons ---')

    # Tables with season_name column (references time_season.t_season)
    tables_season_name = [
        'SegFrac',
        'time_seasons_per_period',
        'DemandSpecificDistribution',
        'CapacityFactorTech',
        'CapacityFactorProcess',
    ]

    for table in tables_season_name:
        try:
            cur = conn.execute(
                f'DELETE FROM "{table}" WHERE season_name IN ({placeholders})',
                tuple(to_remove),
            )
            if cur.rowcount > 0:
                print(f'  {table}: deleted {cur.rowcount} rows')
        except sqlite3.OperationalError as e:
            if 'no such table' in str(e).lower():
                pass
            else:
                raise

    # Tables with t_season column (Output tables - may reference seasons)
    tables_t_season = [
        'Output_VFlow_Out',
        'Output_VFlow_Out2',
        'Output_VFlow_In',
        'Output_Curtailment',
    ]
    for table in tables_t_season:
        try:
            cur = conn.execute(
                f'DELETE FROM "{table}" WHERE t_season IN ({placeholders})',
                tuple(to_remove),
            )
            if cur.rowcount > 0:
                print(f'  {table}: deleted {cur.rowcount} rows')
        except sqlite3.OperationalError as e:
            if 'no such table' in str(e).lower():
                pass
            else:
                raise

    # Finally, delete from time_season
    cur = conn.execute(
        f'DELETE FROM time_season WHERE t_season IN ({placeholders})',
        tuple(to_remove),
    )
    print(f'  time_season: deleted {cur.rowcount} rows')

    # =========================================================================
    # STEP 3: Rescale SegFrac so fractions sum to 1.0
    # =========================================================================
    print('\n--- Step 3: Rescale SegFrac to sum to 1.0 ---')
    scale_factor = len(sorted_seasons) / len(kept)
    try:
        cur = conn.execute('UPDATE SegFrac SET segfrac = segfrac * ?', (scale_factor,))
        print(f'  SegFrac: rescaled {cur.rowcount} rows by {scale_factor}')

        # Verify
        cur = conn.execute('SELECT SUM(segfrac) FROM SegFrac')
        total = cur.fetchone()[0]
        if total:
            # SegFrac may be per-period, so total could be > 1 if multiple periods
            cur = conn.execute('SELECT COUNT(DISTINCT periods) FROM SegFrac')
            num_periods = cur.fetchone()[0] or 1
            print(f'  Verification: sum = {total:.6f} across {num_periods} period(s)')
    except sqlite3.OperationalError:
        print('  SegFrac table not found, skipping')

    # =========================================================================
    # STEP 4: Rescale DemandSpecificDistribution so fractions sum to 1.0
    # =========================================================================
    print('\n--- Step 4: Rescale DemandSpecificDistribution to sum to 1.0 ---')
    try:
        # Get current sums per (region, period, demand)
        cur = conn.execute("""
            SELECT regions, periods, demand_name, SUM(dds) as current_sum
            FROM DemandSpecificDistribution
            GROUP BY regions, periods, demand_name
        """)

        dsd_scales = {}
        for row in cur.fetchall():
            regions, periods, demand_name, current_sum = row
            if current_sum and current_sum > 0:
                dsd_scales[(regions, periods, demand_name)] = 1.0 / current_sum

        # Apply scaling
        for (regions, periods, demand_name), scale in dsd_scales.items():
            conn.execute(
                """
                UPDATE DemandSpecificDistribution
                SET dds = dds * ?
                WHERE regions = ? AND periods = ? AND demand_name = ?
            """,
                (scale, regions, periods, demand_name),
            )

        print(f'  Rescaled {len(dsd_scales)} (region, period, demand) combinations')

        # Verify
        cur = conn.execute("""
            SELECT regions, periods, demand_name, SUM(dds)
            FROM DemandSpecificDistribution
            GROUP BY regions, periods, demand_name
            LIMIT 3
        """)
        print('  Verification (sample):')
        for row in cur.fetchall():
            print(f'    {row[0]} {row[1]} {row[2]}: {row[3]:.6f}')
    except sqlite3.OperationalError:
        print('  DemandSpecificDistribution table not found, skipping')

    # =========================================================================
    # STEP 5: Adjust Demand to reflect actual demand for kept seasons
    # =========================================================================
    print('\n--- Step 5: Adjust Demand for kept seasons ---')
    if demand_adjustments:
        try:
            updated = 0
            for (regions, periods, demand_name), fraction in demand_adjustments.items():
                cur = conn.execute(
                    """
                    UPDATE Demand
                    SET demand = demand * ?
                    WHERE regions = ? AND periods = ? AND demand_comm = ?
                """,
                    (fraction, regions, periods, demand_name),
                )
                updated += cur.rowcount

            print(f'  Updated {updated} Demand rows (multiplied by kept-season DSD fraction)')

            # Verify
            cur = conn.execute('SELECT regions, periods, demand_comm, demand FROM Demand LIMIT 3')
            print('  Verification (sample):')
            for row in cur.fetchall():
                print(f'    {row[0]} {row[1]} {row[2]}: {row[3]:,.0f}')
        except sqlite3.OperationalError as e:
            print(f'  Error updating Demand: {e}')
    else:
        print('  No demand adjustments calculated, skipping')

    conn.commit()

    # =========================================================================
    # Final verification
    # =========================================================================
    print('\n--- Final verification ---')
    remaining = [
        r[0] for r in conn.execute('SELECT t_season FROM time_season ORDER BY t_season').fetchall()
    ]
    print(f'Remaining seasons: {remaining}')

    # =========================================================================
    # Step 6: Auto-set C2A = N_kept_seasons * 168
    # =========================================================================
    print('\n--- Step 6: Auto-set CapacityToActivity ---')
    c2a_value = float(len(kept) * 168)
    try:
        cur = conn.execute('UPDATE CapacityToActivity SET c2a = ?', (c2a_value,))
        print(f'  C2A set to {c2a_value:.0f} ({len(kept)} seasons x 168 hours)')
        print(f'  Updated {cur.rowcount} rows')
    except sqlite3.OperationalError as e:
        print(f'  Warning: could not update C2A: {e}')

    conn.commit()
    conn.close()

    print(f'\n✓ Created {len(kept)}-week subset: {output}')
    print(f'  C2A = {c2a_value:.0f}')
    print(f'  For v4 migration, days_per_period should be {len(kept) * 7}')


if __name__ == '__main__':
    main()
