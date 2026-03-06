#!/usr/bin/env python3
"""
Unified pipeline to convert a base v3.1 national Temoa DB into v4-compliant
databases for any region/time subset.

Replaces the old multi-script pipeline (step2/8/9/10 SQL, create_4week_subset,
migrate_to_v4, strip_region_prefixes) with a single parameterized invocation.

Starts from the TRUE BASE: the full national v3.1 DB.

Pipeline steps:
  1. Copy source DB to working copy
  2. Filter regions (if --regions specified)
  3. Clean technologies (delete techs not in Efficiency, cascade)
  4. Clean groups (remove orphan group memberships)
  5. Clean commodities (remove orphans, preserve emission commodities)
  6. Subset time (if --weeks < 52) and auto-set C2A
  7. Optionally output v3.1 subset (if --output-v3 given)
  8. Migrate to v4 (schema conversion)
  9. Strip region prefixes (tech name cleanup)
  10. Validate consistency

Usage:
  python build_v4_db.py \\
    --source base_52week.sqlite \\
    --regions TRE,TREW \\
    --weeks 4 \\
    --output-v4 output_v4.sqlite \\
    --output-v3 output_v3.sqlite \\
    --schema temoa/db_schema/temoa_schema_v4.sql

  # Full 52-week, all regions
  python build_v4_db.py --source base.sqlite --output-v4 full_v4.sqlite

  # 8-week, single region
  python build_v4_db.py --source base.sqlite --regions TRE --weeks 8 --output-v4 tre_8week.sqlite
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


def parse_sort_key(label: str) -> tuple[int, str]:
    """Natural-ish ordering for labels like h1, h2, s1, s2, ..."""
    prefix = ''.join(ch for ch in str(label) if not ch.isdigit())
    digits = ''.join(ch for ch in str(label) if ch.isdigit())
    if digits:
        return (int(digits), prefix)
    return (10**9, str(label))


# =============================================================================
# Step 2: Filter regions
# =============================================================================


def filter_regions(conn: sqlite3.Connection, keep_regions: list[str]) -> None:
    """Delete all data for regions NOT in keep_regions.

    Also keeps inter-regional transfer combinations (e.g. TRE-TREW, TREW-TRE).
    """
    print(f'\n--- Step 2: Filter regions (keeping {keep_regions}) ---')

    # Build the full set of regions to keep (including inter-regional combos)
    keep_set = set(keep_regions)
    combos = []
    for r1 in keep_regions:
        for r2 in keep_regions:
            if r1 != r2:
                combos.append(f'{r1}-{r2}')
                keep_set.add(f'{r1}-{r2}')

    keep_list = sorted(keep_set)
    placeholders = ','.join('?' * len(keep_list))

    # Discover all tables with a 'regions' column
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()

    deleted_total = 0
    for (table_name,) in tables:
        cols = [row[1] for row in conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()]
        if 'regions' in cols:
            cur = conn.execute(
                f'DELETE FROM "{table_name}" WHERE regions NOT IN ({placeholders})',
                tuple(keep_list),
            )
            if cur.rowcount > 0:
                print(f'  {table_name}: deleted {cur.rowcount} rows')
                deleted_total += cur.rowcount

    # Also handle the 'regions' table itself (it has column 'regions', not a region FK)
    try:
        cur = conn.execute(
            f'DELETE FROM regions WHERE regions NOT IN ({placeholders})',
            tuple(keep_list),
        )
        if cur.rowcount > 0:
            print(f'  regions table: deleted {cur.rowcount} rows')
    except sqlite3.OperationalError:
        pass

    # Clear region_combinations (rebuild would be needed for remaining regions)
    try:
        cur = conn.execute('DELETE FROM region_combinations')
        if cur.rowcount > 0:
            print(f'  region_combinations: cleared {cur.rowcount} rows')
    except sqlite3.OperationalError:
        pass

    print(f'  Total rows deleted: {deleted_total}')
    conn.commit()


# =============================================================================
# Step 3: Clean technologies
# =============================================================================


def clean_technologies(conn: sqlite3.Connection) -> None:
    """Delete techs not in Efficiency, then cascade to all dependent tables."""
    print('\n--- Step 3: Clean technologies ---')

    # Delete from technologies table first
    cur = conn.execute(
        'DELETE FROM technologies WHERE tech NOT IN (SELECT DISTINCT tech FROM Efficiency)'
    )
    print(f'  technologies: deleted {cur.rowcount} orphan techs')

    # Cascade to all tables with a 'tech' column
    cascade_tables = [
        'ExistingCapacity',
        'CostInvest',
        'CostFixed',
        'CostVariable',
        'CapacityCredit',
        'CapacityToActivity',
        'CapacityFactorTech',
        'CapacityFactorProcess',
        'DiscountRate',
        'LifetimeTech',
        'LifetimeLoanTech',
        'StorageDuration',
        'MaxCapacity',
        'MaxNewCapacity',
        'MinCapacity',
        'MinAnnualCapacityFactor',
        'MaxResource',
        'EmissionActivity',
        'RampUp',
        'RampDown',
        'tech_curtailment',
        'tech_reserve',
        'tech_ramping',
        'tech_groups',
    ]

    for table in cascade_tables:
        try:
            cur = conn.execute(
                f'DELETE FROM "{table}" WHERE tech NOT IN (SELECT tech FROM technologies)'
            )
            if cur.rowcount > 0:
                print(f'  {table}: deleted {cur.rowcount} rows')
        except sqlite3.OperationalError:
            pass  # Table doesn't exist

    conn.commit()


# =============================================================================
# Step 4: Clean groups
# =============================================================================


def clean_groups(conn: sqlite3.Connection) -> None:
    """Remove orphan group memberships (techs no longer in the technology table)
    and then empty groups. Preserves all valid group data including RPS/CES."""
    print('\n--- Step 4: Clean groups ---')

    # Remove tech_groups memberships for techs that were deleted in earlier steps
    try:
        cur = conn.execute(
            """
            DELETE FROM tech_groups
            WHERE tech NOT IN (SELECT tech FROM technologies)
            """
        )
        if cur.rowcount > 0:
            print(f'  tech_groups: deleted {cur.rowcount} orphan membership rows')
    except sqlite3.OperationalError:
        pass

    # Remove groups that no longer have any members
    try:
        cur = conn.execute(
            """
            DELETE FROM groups
            WHERE group_name NOT IN (SELECT DISTINCT group_name FROM tech_groups)
            """
        )
        if cur.rowcount > 0:
            print(f'  groups: deleted {cur.rowcount} empty group rows')
    except sqlite3.OperationalError:
        pass

    # Remove MinActivityGroup/MaxActivityGroup etc. entries for deleted groups
    for table in ['MinActivityGroup', 'MaxActivityGroup', 'MinCapacityGroup', 'MaxCapacityGroup']:
        try:
            cur = conn.execute(
                f"""
                DELETE FROM "{table}"
                WHERE group_name NOT IN (SELECT group_name FROM groups)
                """
            )
            if cur.rowcount > 0:
                print(f'  {table}: deleted {cur.rowcount} rows for removed groups')
        except sqlite3.OperationalError:
            pass

    # Report what's preserved
    try:
        remaining = conn.execute('SELECT COUNT(*) FROM tech_groups').fetchone()[0]
        groups = conn.execute('SELECT COUNT(*) FROM groups').fetchone()[0]
        print(f'  Preserved {remaining} tech_groups memberships across {groups} groups')
    except sqlite3.OperationalError:
        pass

    conn.commit()


# =============================================================================
# Step 5: Clean commodities
# =============================================================================


def clean_commodities(conn: sqlite3.Connection) -> None:
    """Remove orphan commodities, preserving emission commodities."""
    print('\n--- Step 5: Clean commodities ---')

    cur = conn.execute("""
        DELETE FROM commodities WHERE comm_name NOT IN (
            SELECT DISTINCT input_comm FROM Efficiency
            UNION
            SELECT DISTINCT output_comm FROM Efficiency
            UNION
            SELECT DISTINCT demand_comm FROM Demand
            UNION
            SELECT DISTINCT emis_comm FROM EmissionActivity
        )
    """)
    print(f'  commodities: deleted {cur.rowcount} orphan commodities')
    conn.commit()


# =============================================================================
# Step 6: Subset time
# =============================================================================


def subset_time(conn: sqlite3.Connection, weeks: int, week_start: int = 1) -> int:
    """Subset to N weeks starting at week_start (1-based), rescale SegFrac/DSD/Demand, auto-set C2A.

    Returns the number of kept seasons (= weeks, since each season = 1 week).
    """
    start_idx = week_start - 1  # convert to 0-based
    print(f'\n--- Step 6: Subset time ({weeks} weeks starting at week {week_start}) ---')

    seasons = [r[0] for r in conn.execute('SELECT t_season FROM time_season').fetchall()]
    sorted_seasons = sorted(seasons, key=parse_sort_key)

    if start_idx + weeks > len(sorted_seasons):
        print(
            f'  ERROR: week_start={week_start} + weeks={weeks} = {week_start + weeks - 1} '
            f'exceeds available seasons ({len(sorted_seasons)})'
        )
        sys.exit(1)

    if len(sorted_seasons) <= weeks and start_idx == 0:
        print(f'  Source has {len(sorted_seasons)} seasons, keeping all (no subsetting needed)')
        n_kept = len(sorted_seasons)
    else:
        kept = sorted_seasons[start_idx : start_idx + weeks]
        to_remove = [s for s in sorted_seasons if s not in kept]
        print(f'  Keeping {len(kept)} of {len(sorted_seasons)} seasons')

        placeholders_rm = ','.join('?' * len(to_remove))
        kept_placeholders = ','.join('?' * len(kept))

        # --- 6a: Calculate demand adjustments BEFORE deleting DSD rows ---
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
        except sqlite3.OperationalError:
            pass

        # Fallback for commodities without DSD (e.g. DEMAND_CRYPTO, DEMAND_SERVERS)
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

            for regions, periods, demand_comm in all_demands:
                if (regions, periods, demand_comm) not in demand_adjustments:
                    frac = sf_fracs.get(periods, 1.0)
                    demand_adjustments[(regions, periods, demand_comm)] = frac
                    print(f'  {regions}/{periods}/{demand_comm}: no DSD, SegFrac frac={frac:.6f}')
        except sqlite3.OperationalError:
            pass

        # --- 6b: Delete rows for removed seasons ---
        season_tables = [
            ('SegFrac', 'season_name'),
            ('time_seasons_per_period', 'season_name'),
            ('DemandSpecificDistribution', 'season_name'),
            ('CapacityFactorTech', 'season_name'),
            ('CapacityFactorProcess', 'season_name'),
            ('Output_VFlow_Out', 't_season'),
            ('Output_VFlow_Out2', 't_season'),
            ('Output_VFlow_In', 't_season'),
            ('Output_Curtailment', 't_season'),
        ]

        for table, col in season_tables:
            try:
                cur = conn.execute(
                    f'DELETE FROM "{table}" WHERE "{col}" IN ({placeholders_rm})',
                    tuple(to_remove),
                )
                if cur.rowcount > 0:
                    print(f'  {table}: deleted {cur.rowcount} rows')
            except sqlite3.OperationalError:
                pass

        conn.execute(
            f'DELETE FROM time_season WHERE t_season IN ({placeholders_rm})',
            tuple(to_remove),
        )

        # --- 6c: Rescale SegFrac to sum to 1.0 ---
        scale_factor = len(sorted_seasons) / len(kept)
        conn.execute('UPDATE SegFrac SET segfrac = segfrac * ?', (scale_factor,))
        print(f'  SegFrac: rescaled by {scale_factor:.4f}')

        # --- 6d: Rescale DSD to sum to 1.0 ---
        try:
            cur = conn.execute("""
                SELECT regions, periods, demand_name, SUM(dds)
                FROM DemandSpecificDistribution
                GROUP BY regions, periods, demand_name
            """)
            for row in cur.fetchall():
                regions, periods, demand_name, current_sum = row
                if current_sum and current_sum > 0:
                    conn.execute(
                        """
                        UPDATE DemandSpecificDistribution
                        SET dds = dds * ?
                        WHERE regions = ? AND periods = ? AND demand_name = ?
                    """,
                        (1.0 / current_sum, regions, periods, demand_name),
                    )
        except sqlite3.OperationalError:
            pass

        # --- 6e: Adjust Demand values ---
        for (regions, periods, demand_name), fraction in demand_adjustments.items():
            conn.execute(
                """
                UPDATE Demand SET demand = demand * ?
                WHERE regions = ? AND periods = ? AND demand_comm = ?
            """,
                (fraction, regions, periods, demand_name),
            )

        n_kept = len(kept)

    # --- 6f: Auto-set C2A ---
    c2a_value = float(n_kept * 168)  # N_kept_seasons * hours_per_week
    conn.execute('UPDATE CapacityToActivity SET c2a = ?', (c2a_value,))
    print(f'  C2A auto-set to {c2a_value:.0f} ({n_kept} seasons x 168 hours)')

    conn.commit()
    return n_kept


# =============================================================================
# Step 7: Output v3.1 subset
# =============================================================================


def save_v3_output(working_db: Path, output_v3: Path) -> None:
    """Copy the cleaned/subsetted v3.1 DB to the v3 output path."""
    print('\n--- Step 7: Save v3.1 output ---')
    shutil.copy2(working_db, output_v3)
    print(f'  Saved: {output_v3}')


# =============================================================================
# Step 8: Migrate to v4
# =============================================================================


def migrate_to_v4(
    working_db: Path, schema_path: Path, output_v4: Path, n_kept_seasons: int
) -> None:
    """Run migrate_to_v4.py to convert v3.1 -> v4."""
    print('\n--- Step 8: Migrate to v4 ---')

    migrate_script = Path(__file__).parent / 'migrate_to_v4.py'
    if not migrate_script.exists():
        print(f'  ERROR: migrate_to_v4.py not found at {migrate_script}')
        sys.exit(1)

    days = n_kept_seasons * 7
    cmd = [
        sys.executable,
        str(migrate_script),
        '--source',
        str(working_db),
        '--schema',
        str(schema_path),
        '--out',
        str(output_v4),
        '--days-per-period',
        str(days),
    ]
    print(f'  Running: {" ".join(cmd)}')
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f'  STDERR:\n{result.stderr}')
        sys.exit(1)

    # Print key lines from migration output
    for line in result.stdout.splitlines():
        if any(
            kw in line.lower() for kw in ['unlim', 'orphan', 'flag', 'error', 'warning', 'done']
        ):
            print(f'  {line}')

    print(f'  Migration complete: {output_v4}')


# =============================================================================
# Step 9: Strip region prefixes
# =============================================================================


def strip_prefixes(output_v4: Path) -> None:
    """Run strip_region_prefixes.py to remove region names from tech names."""
    print('\n--- Step 9: Strip region prefixes ---')

    strip_script = Path(__file__).parent / 'strip_region_prefixes.py'
    if not strip_script.exists():
        print(f'  ERROR: strip_region_prefixes.py not found at {strip_script}')
        sys.exit(1)

    cmd = [sys.executable, str(strip_script), str(output_v4)]
    print(f'  Running: {" ".join(cmd)}')
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f'  STDERR:\n{result.stderr}')
        sys.exit(1)

    for line in result.stdout.splitlines():
        if any(kw in line.lower() for kw in ['renamed', 'dedup', 'verif', 'error', 'summary']):
            print(f'  {line}')

    print('  Prefix stripping complete')


# =============================================================================
# Step 10: Validate
# =============================================================================


def validate_v4(output_v4: Path, n_kept_seasons: int) -> None:
    """Run consistency checks on the final v4 DB."""
    print('\n--- Step 10: Validate v4 output ---')

    conn = sqlite3.connect(output_v4)
    errors = []

    # 10a: C2A x SegFrac ~ 1.0
    expected_c2a = n_kept_seasons * 168.0
    c2a_vals = conn.execute('SELECT DISTINCT c2a FROM capacity_to_activity').fetchall()
    for (c2a,) in c2a_vals:
        if abs(c2a - expected_c2a) > 0.01:
            errors.append(f'C2A mismatch: found {c2a}, expected {expected_c2a}')

    # Check product
    rows = conn.execute(
        """
        SELECT ? * segment_fraction AS product
        FROM time_segment_fraction WHERE period = (
            SELECT MIN(period) FROM time_segment_fraction
        ) LIMIT 5
    """,
        (expected_c2a,),
    ).fetchall()
    for (product,) in rows:
        if abs(product - 1.0) > 0.01:
            errors.append(f'C2A x SegFrac = {product:.4f}, expected ~1.0')
            break

    # 10b: days_per_period consistency
    expected_days = n_kept_seasons * 7
    days_row = conn.execute("SELECT value FROM metadata WHERE element='days_per_period'").fetchone()
    if days_row:
        days_val = int(days_row[0])
        if days_val != expected_days:
            errors.append(f'days_per_period = {days_val}, expected {expected_days}')
        c2a_from_days = days_val * 24
        if abs(c2a_from_days - expected_c2a) > 0.01:
            errors.append(f'days_per_period*24 = {c2a_from_days}, C2A = {expected_c2a}')
    else:
        errors.append('days_per_period not found in metadata')

    # 10c: SegFrac sums to 1.0 per period
    periods = conn.execute('SELECT DISTINCT period FROM time_segment_fraction').fetchall()
    for (p,) in periods:
        total = conn.execute(
            'SELECT SUM(segment_fraction) FROM time_segment_fraction WHERE period=?', (p,)
        ).fetchone()[0]
        if total and abs(total - 1.0) > 1e-4:
            errors.append(f'SegFrac sum for period {p} = {total:.6f}, expected 1.0')

    # 10d: No orphan techs
    orphans = conn.execute("""
        SELECT DISTINCT tech FROM efficiency
        WHERE tech NOT IN (SELECT tech FROM technology)
    """).fetchall()
    if orphans:
        errors.append(f'{len(orphans)} orphan techs in efficiency not in technology table')

    # 10e: DSD sums
    try:
        dsd_sums = conn.execute("""
            SELECT region, period, demand_name, SUM(dsd) as total
            FROM demand_specific_distribution
            GROUP BY region, period, demand_name
            HAVING ABS(total - 1.0) > 1e-4
        """).fetchall()
        for r, p, d, total in dsd_sums:
            errors.append(f'DSD sum for {r}/{p}/{d} = {total:.6f}, expected 1.0')
    except sqlite3.OperationalError:
        pass

    conn.close()

    if errors:
        print('  VALIDATION ERRORS:')
        for e in errors:
            print(f'    - {e}')
    else:
        print('  All checks passed')


# =============================================================================
# Main
# =============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Build v4 Temoa DB from base v3.1 national DB',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--source',
        required=True,
        help='Path to base v3.1 national SQLite DB',
    )
    parser.add_argument(
        '--regions',
        help='Comma-separated regions to keep (e.g. TRE,TREW). Omit for all.',
    )
    parser.add_argument(
        '--weeks',
        type=int,
        default=52,
        help='Number of weeks to keep (default: 52 = full year)',
    )
    parser.add_argument(
        '--week-start',
        type=int,
        default=1,
        help='First week to keep, 1-based (default: 1). E.g. --week-start 30 --weeks 6 keeps weeks 30-35.',
    )
    parser.add_argument(
        '--output-v4',
        required=True,
        help='Path for v4 output SQLite DB',
    )
    parser.add_argument(
        '--output-v3',
        help='Path for cleaned v3.1 output (optional, for mip-dev runs)',
    )
    parser.add_argument(
        '--schema',
        default='temoa/db_schema/temoa_schema_v4.sql',
        help='Path to v4 schema SQL file (default: temoa/db_schema/temoa_schema_v4.sql)',
    )
    args = parser.parse_args()

    source = Path(args.source)
    output_v4 = Path(args.output_v4)
    schema_path = Path(args.schema)

    if not source.exists():
        print(f'Error: source DB not found: {source}')
        sys.exit(1)
    if not schema_path.exists():
        print(f'Error: schema file not found: {schema_path}')
        sys.exit(1)

    # Step 1: Copy to working location
    print('=== Build v4 DB Pipeline ===')
    print(f'Source: {source}')
    print(f'Regions: {args.regions or "ALL"}')
    print(f'Weeks: {args.weeks} (starting at week {args.week_start})')

    with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
        working_db = Path(tmp.name)

    print('\n--- Step 1: Copy source to working DB ---')
    shutil.copy2(source, working_db)
    print(f'  Working copy: {working_db}')

    conn = sqlite3.connect(working_db)
    conn.execute('PRAGMA foreign_keys = OFF')

    # Step 2: Filter regions
    if args.regions:
        keep_regions = [r.strip() for r in args.regions.split(',')]
        filter_regions(conn, keep_regions)

    # Step 3: Clean technologies
    clean_technologies(conn)

    # Step 4: Clean groups
    clean_groups(conn)

    # Step 5: Clean commodities
    clean_commodities(conn)

    conn.close()

    # Step 6: Subset time (reopens connection internally)
    conn = sqlite3.connect(working_db)
    conn.execute('PRAGMA foreign_keys = OFF')
    n_kept = subset_time(conn, args.weeks, args.week_start)
    conn.close()

    # Step 7: Optionally save v3.1 output
    if args.output_v3:
        save_v3_output(working_db, Path(args.output_v3))

    # Step 8: Migrate to v4
    migrate_to_v4(working_db, schema_path, output_v4, n_kept)

    # Step 9: Strip region prefixes
    strip_prefixes(output_v4)

    # Step 10: Validate
    validate_v4(output_v4, n_kept)

    # Cleanup
    working_db.unlink(missing_ok=True)

    print('\n=== Pipeline complete ===')
    print(f'v4 output: {output_v4}')
    if args.output_v3:
        print(f'v3 output: {args.output_v3}')
    print(f'C2A = {n_kept * 168} ({n_kept} seasons x 168 hours)')
    print(f'days_per_period = {n_kept * 7}')


if __name__ == '__main__':
    main()
