#!/usr/bin/env python3
"""
Create a 4-week subset from a full 52-week Temoa v4 schema DB.

Keeps the first 4 seasons and removes the rest from time_season and all
time-indexed tables. Output is a smaller DB suitable for faster comparison
testing between v4/unstable and mip-dev.

Adjustments made automatically:
  1. Deletes data for removed seasons from all time-indexed tables
  2. Rescales time_segment_fraction to sum to 1.0 per period
  3. Rescales demand_specific_distribution to sum to 1.0 per (region, period, demand)
  4. Adjusts demand to reflect actual demand for kept seasons
  5. Sets capacity_to_activity = 672.0 (28 days x 24h)
  6. Sets metadata days_per_period = 28
  7. Clears all output tables

Usage:
  python create_4week_subset_v4.py <source_v4.sqlite> <output_4week_v4.sqlite>

Example:
  python create_4week_subset_v4.py \\
    data_files/test_TRE_TREW_52week_v4_stripped.sqlite \\
    data_files/jan_TRE_TREW_4week_v4_stripped.sqlite
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path


def parse_sort_key(label: str) -> tuple[int, str]:
    """Natural-ish ordering for labels like p1, p2, s1, s2, ..."""
    prefix = ''.join(ch for ch in str(label) if not ch.isdigit())
    digits = ''.join(ch for ch in str(label) if ch.isdigit())
    if digits:
        return (int(digits), prefix)
    return (10**9, str(label))


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    source = Path(sys.argv[1])
    output = Path(sys.argv[2])

    if not source.exists():
        print(f'Error: source DB not found: {source}')
        sys.exit(1)

    print(f'Copying {source} -> {output}')
    shutil.copy2(source, output)

    conn = sqlite3.connect(output)
    conn.execute('PRAGMA foreign_keys = OFF')

    # Get all distinct seasons and sort
    seasons = [r[0] for r in conn.execute('SELECT DISTINCT season FROM time_season').fetchall()]
    sorted_seasons = sorted(seasons, key=parse_sort_key)

    if len(sorted_seasons) < 4:
        print(f'Warning: only {len(sorted_seasons)} seasons in source, keeping all')
        kept = sorted_seasons
    else:
        kept = sorted_seasons[:4]

    to_remove = [s for s in sorted_seasons if s not in kept]
    print(f'Keeping seasons: {kept}')
    print(
        f'Removing seasons: {to_remove[:10]}'
        f'{"..." if len(to_remove) > 10 else ""} ({len(to_remove)} total)'
    )

    if not to_remove:
        print('Nothing to remove (source already has <=4 seasons).')
        conn.close()
        print(f'\nCreated 4-week subset: {output}')
        return

    placeholders = ','.join('?' * len(to_remove))
    kept_placeholders = ','.join('?' * len(kept))

    # =========================================================================
    # STEP 1: Calculate demand adjustment BEFORE deleting DSD rows
    # =========================================================================
    print('\n--- Step 1: Calculate demand for kept seasons ---')

    demand_adjustments: dict[tuple, float] = {}
    try:
        cur = conn.execute(
            f"""
            SELECT region, period, demand_name, SUM(dsd) as kept_fraction
            FROM demand_specific_distribution
            WHERE season IN ({kept_placeholders})
            GROUP BY region, period, demand_name
        """,
            tuple(kept),
        )

        for row in cur.fetchall():
            region, period, demand_name, kept_fraction = row
            demand_adjustments[(region, period, demand_name)] = kept_fraction

        print(
            f'  Calculated demand fractions for {len(demand_adjustments)}'
            ' (region, period, demand) combinations'
        )
    except sqlite3.OperationalError as e:
        if 'no such table' not in str(e).lower():
            raise
        print('  demand_specific_distribution table not found, skipping demand adjustment')

    # Fallback for demand commodities without DSD (e.g., DEMAND_CRYPTO, DEMAND_SERVERS)
    # These have no demand_specific_distribution entries, so we scale by the
    # time_segment_fraction sum for kept seasons (= 4/52 for uniform SegFrac).
    try:
        all_demands = conn.execute(
            'SELECT DISTINCT region, period, commodity FROM demand'
        ).fetchall()
        sf_fracs = {}
        for row in conn.execute(
            f"""SELECT period, SUM(segment_fraction) FROM time_segment_fraction
                WHERE season IN ({kept_placeholders}) GROUP BY period""",
            tuple(kept),
        ).fetchall():
            sf_fracs[row[0]] = row[1]

        fallback_count = 0
        for region, period, commodity in all_demands:
            if (region, period, commodity) not in demand_adjustments:
                frac = sf_fracs.get(period, 1.0)
                demand_adjustments[(region, period, commodity)] = frac
                fallback_count += 1
                print(f'  {region}/{period}/{commodity}: no DSD, using SegFrac fraction {frac:.6f}')
        if fallback_count:
            print(f'  Applied SegFrac fallback to {fallback_count} demand commodities')
    except sqlite3.OperationalError:
        pass  # demand or time_segment_fraction table missing — nothing to do

    # =========================================================================
    # STEP 2: Delete rows for removed seasons
    # =========================================================================
    print('\n--- Step 2: Delete data for removed seasons ---')

    # v4 input tables with 'season' column
    tables_with_season = [
        'time_segment_fraction',
        'demand_specific_distribution',
        'capacity_factor_tech',
        'capacity_factor_process',
        'efficiency_variable',
        'limit_storage_level_fraction',
        'reserve_capacity_derate',
        'limit_seasonal_capacity_factor',
    ]

    for table in tables_with_season:
        try:
            cur = conn.execute(
                f'DELETE FROM [{table}] WHERE season IN ({placeholders})',
                tuple(to_remove),
            )
            if cur.rowcount > 0:
                print(f'  {table}: deleted {cur.rowcount} rows')
        except sqlite3.OperationalError as e:
            if 'no such table' in str(e).lower():
                pass
            else:
                raise

    # v4 output tables with 'season' column
    output_tables_with_season = [
        'output_flow_out',
        'output_flow_in',
        'output_curtailment',
        'output_storage_level',
    ]
    for table in output_tables_with_season:
        try:
            cur = conn.execute(
                f'DELETE FROM [{table}] WHERE season IN ({placeholders})',
                tuple(to_remove),
            )
            if cur.rowcount > 0:
                print(f'  {table}: deleted {cur.rowcount} rows')
        except sqlite3.OperationalError as e:
            if 'no such table' in str(e).lower():
                pass
            else:
                raise

    # time_season and time_season_sequential
    cur = conn.execute(
        f'DELETE FROM time_season WHERE season IN ({placeholders})',
        tuple(to_remove),
    )
    print(f'  time_season: deleted {cur.rowcount} rows')

    try:
        cur = conn.execute(
            f'DELETE FROM time_season_sequential WHERE season IN ({placeholders})',
            tuple(to_remove),
        )
        if cur.rowcount > 0:
            print(f'  time_season_sequential: deleted {cur.rowcount} rows')
    except sqlite3.OperationalError:
        pass

    # =========================================================================
    # STEP 3: Rescale time_segment_fraction so fractions sum to 1.0 per period
    # =========================================================================
    print('\n--- Step 3: Rescale time_segment_fraction to sum to 1.0 ---')
    try:
        # Get current sums per period
        cur = conn.execute("""
            SELECT period, SUM(segment_fraction) as current_sum
            FROM time_segment_fraction
            GROUP BY period
        """)

        sf_scales = {}
        for row in cur.fetchall():
            period, current_sum = row
            if current_sum and current_sum > 0:
                sf_scales[period] = 1.0 / current_sum

        for period, scale in sf_scales.items():
            conn.execute(
                'UPDATE time_segment_fraction SET segment_fraction = segment_fraction * ?'
                ' WHERE period = ?',
                (scale, period),
            )

        print(f'  Rescaled {len(sf_scales)} period(s)')

        # Verify
        cur = conn.execute("""
            SELECT period, SUM(segment_fraction) FROM time_segment_fraction
            GROUP BY period LIMIT 3
        """)
        print('  Verification (sample):')
        for row in cur.fetchall():
            print(f'    period {row[0]}: sum = {row[1]:.6f}')
    except sqlite3.OperationalError:
        print('  time_segment_fraction table not found, skipping')

    # =========================================================================
    # STEP 4: Rescale demand_specific_distribution so fractions sum to 1.0
    # =========================================================================
    print('\n--- Step 4: Rescale demand_specific_distribution to sum to 1.0 ---')
    try:
        cur = conn.execute("""
            SELECT region, period, demand_name, SUM(dsd) as current_sum
            FROM demand_specific_distribution
            GROUP BY region, period, demand_name
        """)

        dsd_scales = {}
        for row in cur.fetchall():
            region, period, demand_name, current_sum = row
            if current_sum and current_sum > 0:
                dsd_scales[(region, period, demand_name)] = 1.0 / current_sum

        for (region, period, demand_name), scale in dsd_scales.items():
            conn.execute(
                """
                UPDATE demand_specific_distribution
                SET dsd = dsd * ?
                WHERE region = ? AND period = ? AND demand_name = ?
            """,
                (scale, region, period, demand_name),
            )

        print(f'  Rescaled {len(dsd_scales)} (region, period, demand) combinations')

        # Verify
        cur = conn.execute("""
            SELECT region, period, demand_name, SUM(dsd)
            FROM demand_specific_distribution
            GROUP BY region, period, demand_name
            LIMIT 3
        """)
        print('  Verification (sample):')
        for row in cur.fetchall():
            print(f'    {row[0]} {row[1]} {row[2]}: {row[3]:.6f}')
    except sqlite3.OperationalError:
        print('  demand_specific_distribution table not found, skipping')

    # =========================================================================
    # STEP 5: Adjust demand to reflect actual demand for kept seasons
    # =========================================================================
    print('\n--- Step 5: Adjust demand for kept seasons ---')
    if demand_adjustments:
        try:
            updated = 0
            for (region, period, demand_name), fraction in demand_adjustments.items():
                cur = conn.execute(
                    """
                    UPDATE demand
                    SET demand = demand * ?
                    WHERE region = ? AND period = ? AND commodity = ?
                """,
                    (fraction, region, period, demand_name),
                )
                updated += cur.rowcount

            print(f'  Updated {updated} demand rows (multiplied by kept-season DSD fraction)')

            # Verify
            cur = conn.execute('SELECT region, period, commodity, demand FROM demand LIMIT 3')
            print('  Verification (sample):')
            for row in cur.fetchall():
                print(f'    {row[0]} {row[1]} {row[2]}: {row[3]:,.0f}')
        except sqlite3.OperationalError as e:
            print(f'  Error updating demand: {e}')
    else:
        print('  No demand adjustments calculated, skipping')

    # =========================================================================
    # STEP 6: Set capacity_to_activity = 672.0 and metadata days_per_period = 28
    # =========================================================================
    print('\n--- Step 6: Set C2A and days_per_period ---')
    try:
        cur = conn.execute('UPDATE capacity_to_activity SET c2a = 672.0')
        print(f'  capacity_to_activity: set c2a = 672.0 for {cur.rowcount} rows')
    except sqlite3.OperationalError as e:
        print(f'  Error updating capacity_to_activity: {e}')

    try:
        cur = conn.execute("UPDATE metadata SET value = 28 WHERE element = 'days_per_period'")
        if cur.rowcount > 0:
            print('  metadata: set days_per_period = 28')
        else:
            # Insert if not present
            conn.execute("INSERT INTO metadata (element, value) VALUES ('days_per_period', 28)")
            print('  metadata: inserted days_per_period = 28')
    except sqlite3.OperationalError as e:
        print(f'  Error updating metadata: {e}')

    # =========================================================================
    # STEP 7: Clear all output tables
    # =========================================================================
    print('\n--- Step 7: Clear output tables ---')
    output_tables = [
        'output_objective',
        'output_cost',
        'output_flow_in',
        'output_flow_out',
        'output_flow_out_summary',
        'output_built_capacity',
        'output_retired_capacity',
        'output_net_capacity',
        'output_storage_level',
        'output_emission',
        'output_curtailment',
        'output_dual_variable',
    ]
    for table in output_tables:
        try:
            cur = conn.execute(f'DELETE FROM [{table}]')
            if cur.rowcount > 0:
                print(f'  {table}: cleared {cur.rowcount} rows')
        except sqlite3.OperationalError:
            pass

    conn.commit()

    # =========================================================================
    # Final verification
    # =========================================================================
    print('\n--- Final verification ---')
    remaining = [
        r[0]
        for r in conn.execute('SELECT DISTINCT season FROM time_season ORDER BY season').fetchall()
    ]
    print(f'Remaining seasons: {remaining}')

    cur = conn.execute('SELECT SUM(segment_fraction) FROM time_segment_fraction')
    sf_total = cur.fetchone()[0]
    n_periods = conn.execute('SELECT COUNT(DISTINCT period) FROM time_segment_fraction').fetchone()[
        0
    ]
    print(f'SegFrac total: {sf_total:.6f} across {n_periods} period(s)')

    cur = conn.execute("SELECT value FROM metadata WHERE element = 'days_per_period'")
    dpp = cur.fetchone()
    print(f'days_per_period: {dpp[0] if dpp else "NOT SET"}')

    cur = conn.execute('SELECT DISTINCT c2a FROM capacity_to_activity')
    c2a_vals = [r[0] for r in cur.fetchall()]
    print(f'capacity_to_activity c2a values: {c2a_vals}')

    conn.close()

    print(f'\nCreated 4-week v4 subset: {output}')


if __name__ == '__main__':
    main()
