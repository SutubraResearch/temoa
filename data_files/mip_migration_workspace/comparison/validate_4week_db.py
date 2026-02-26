#!/usr/bin/env python3
"""
Validate a time-subset Temoa database (v3 or v4 schema).

Checks:
  - Correct number of seasons (default 4, configurable with --weeks)
  - Segment fractions sum to 1.0 (+-1e-6) per period
  - Demand distribution sums to 1.0 per (region, period, demand)
  - All demand values positive
  - capacity_to_activity matches weeks * 168 (both v3 and v4)
  - metadata.days_per_period matches weeks * 7 (v4 only)
  - No orphan tech references in efficiency
  - Output tables empty

Usage:
  python validate_4week_db.py <database.sqlite> --schema v4
  python validate_4week_db.py <database.sqlite> --schema v3
  python validate_4week_db.py <database.sqlite> --schema v4 --weeks 8
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

TOLERANCE = 1e-6


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone()[0] > 0


def check_seasons(conn: sqlite3.Connection, schema: str, weeks: int = 4) -> list[str]:
    errors = []
    if schema == 'v4':
        seasons = [r[0] for r in conn.execute('SELECT DISTINCT season FROM time_season').fetchall()]
    else:
        seasons = [r[0] for r in conn.execute('SELECT t_season FROM time_season').fetchall()]

    if len(seasons) != weeks:
        errors.append(f'Expected {weeks} seasons, found {len(seasons)}: {seasons}')
    else:
        print(f'  [OK] {weeks} seasons: {sorted(seasons)}')
    return errors


def check_segment_fractions(conn: sqlite3.Connection, schema: str) -> list[str]:
    errors = []
    if schema == 'v4':
        table = 'time_segment_fraction'
        col = 'segment_fraction'
        period_col = 'period'
    else:
        table = 'SegFrac'
        col = 'segfrac'
        period_col = 'periods'

    if not table_exists(conn, table):
        errors.append(f'{table} table not found')
        return errors

    cur = conn.execute(f'SELECT {period_col}, SUM({col}) FROM {table} GROUP BY {period_col}')
    for period, total in cur.fetchall():
        if total is None or abs(total - 1.0) > TOLERANCE:
            errors.append(
                f'Segment fraction sum for period {period} = {total} (expected 1.0 +- {TOLERANCE})'
            )
    if not errors:
        print('  [OK] Segment fractions sum to 1.0 per period')
    return errors


def check_demand_distribution(conn: sqlite3.Connection, schema: str) -> list[str]:
    errors = []
    if schema == 'v4':
        table = 'demand_specific_distribution'
        region_col = 'region'
        period_col = 'period'
        demand_col = 'demand_name'
        frac_col = 'dsd'
    else:
        table = 'DemandSpecificDistribution'
        region_col = 'regions'
        period_col = 'periods'
        demand_col = 'demand_name'
        frac_col = 'dds'

    if not table_exists(conn, table):
        errors.append(f'{table} table not found')
        return errors

    cur = conn.execute(f"""
        SELECT {region_col}, {period_col}, {demand_col}, SUM({frac_col})
        FROM {table}
        GROUP BY {region_col}, {period_col}, {demand_col}
    """)

    bad_count = 0
    total_count = 0
    for region, period, demand, total in cur.fetchall():
        total_count += 1
        if total is None or abs(total - 1.0) > TOLERANCE:
            bad_count += 1
            if bad_count <= 3:
                errors.append(
                    f'DSD sum for ({region}, {period}, {demand}) = {total}'
                    f' (expected 1.0 +- {TOLERANCE})'
                )

    if bad_count > 3:
        errors.append(f'... and {bad_count - 3} more DSD sum errors')

    if not errors:
        print(f'  [OK] DSD sums to 1.0 for all {total_count} (region, period, demand) groups')
    return errors


def check_demand_positive(conn: sqlite3.Connection, schema: str) -> list[str]:
    errors = []
    if schema == 'v4':
        table = 'demand'
        val_col = 'demand'
    else:
        table = 'Demand'
        val_col = 'demand'

    if not table_exists(conn, table):
        errors.append(f'{table} table not found')
        return errors

    cur = conn.execute(f'SELECT COUNT(*) FROM {table} WHERE {val_col} <= 0')
    bad = cur.fetchone()[0]
    if bad > 0:
        errors.append(f'{bad} demand rows have non-positive values')
    else:
        print('  [OK] All demand values positive')
    return errors


def check_c2a(conn: sqlite3.Connection, schema: str, weeks: int = 4) -> list[str]:
    errors = []
    expected = float(weeks * 168)  # N_weeks * hours_per_week
    if schema == 'v4':
        table = 'capacity_to_activity'
    else:
        table = 'CapacityToActivity'
    col = 'c2a'

    if not table_exists(conn, table):
        errors.append(f'{table} table not found')
        return errors

    cur = conn.execute(f'SELECT DISTINCT {col} FROM {table}')
    vals = [r[0] for r in cur.fetchall()]
    if len(vals) != 1 or abs(vals[0] - expected) > 0.1:
        errors.append(f'capacity_to_activity values: {vals} (expected all {expected})')
    else:
        print(f'  [OK] capacity_to_activity = {expected}')
    return errors


def check_metadata_days(conn: sqlite3.Connection, schema: str, weeks: int = 4) -> list[str]:
    errors = []
    if schema != 'v4':
        print('  [SKIP] metadata.days_per_period (v3 does not use this)')
        return errors

    expected_days = weeks * 7

    if not table_exists(conn, 'metadata'):
        errors.append('metadata table not found')
        return errors

    cur = conn.execute("SELECT value FROM metadata WHERE element = 'days_per_period'")
    row = cur.fetchone()
    if row is None:
        errors.append('days_per_period not set in metadata')
    elif int(row[0]) != expected_days:
        errors.append(f'days_per_period = {row[0]} (expected {expected_days})')
    else:
        print(f'  [OK] days_per_period = {expected_days}')
    return errors


def check_orphan_techs(conn: sqlite3.Connection, schema: str) -> list[str]:
    errors = []
    if schema == 'v4':
        eff_table = 'efficiency'
        tech_table = 'technology'
        tech_col = 'tech'
    else:
        eff_table = 'Efficiency'
        tech_table = 'technologies'
        tech_col = 'tech'

    if not table_exists(conn, eff_table) or not table_exists(conn, tech_table):
        print(f'  [SKIP] Orphan tech check (missing {eff_table} or {tech_table})')
        return errors

    cur = conn.execute(f"""
        SELECT DISTINCT e.tech FROM {eff_table} e
        LEFT JOIN {tech_table} t ON e.tech = t.{tech_col}
        WHERE t.{tech_col} IS NULL
    """)
    orphans = [r[0] for r in cur.fetchall()]
    if orphans:
        errors.append(f'{len(orphans)} orphan techs in efficiency: {orphans[:5]}')
    else:
        print('  [OK] No orphan tech references in efficiency')
    return errors


def check_output_tables_empty(conn: sqlite3.Connection, schema: str) -> list[str]:
    errors = []
    if schema == 'v4':
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
    else:
        output_tables = [
            'Output_Objective',
            'Output_V_Capacity',
            'Output_V_NewCapacity',
            'Output_V_RetiredCapacity',
            'Output_VFlow_Out',
            'Output_VFlow_In',
            'Output_Emissions',
        ]

    non_empty = []
    for table in output_tables:
        if not table_exists(conn, table):
            continue
        cur = conn.execute(f'SELECT COUNT(*) FROM [{table}]')
        count = cur.fetchone()[0]
        if count > 0:
            non_empty.append(f'{table} ({count} rows)')

    if non_empty:
        errors.append(f'Non-empty output tables: {", ".join(non_empty)}')
    else:
        print('  [OK] All output tables empty')
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description='Validate a time-subset Temoa database')
    parser.add_argument('database', type=Path, help='Path to SQLite database')
    parser.add_argument(
        '--schema',
        choices=['v3', 'v4'],
        required=True,
        help='Database schema version',
    )
    parser.add_argument(
        '--weeks',
        type=int,
        default=4,
        help='Expected number of weeks/seasons (default: 4)',
    )
    args = parser.parse_args()

    if not args.database.exists():
        print(f'Error: database not found: {args.database}')
        sys.exit(1)

    print(f'Validating: {args.database} (schema: {args.schema}, weeks: {args.weeks})')
    print('=' * 60)

    conn = sqlite3.connect(args.database)
    all_errors: list[str] = []
    weeks = args.weeks

    # Checks that need the weeks parameter
    checks_with_weeks = [
        ('Seasons', lambda c, s: check_seasons(c, s, weeks)),
        ('Segment fractions', check_segment_fractions),
        ('Demand distribution', check_demand_distribution),
        ('Demand values', check_demand_positive),
        ('Capacity-to-activity', lambda c, s: check_c2a(c, s, weeks)),
        ('Metadata days_per_period', lambda c, s: check_metadata_days(c, s, weeks)),
        ('Orphan tech refs', check_orphan_techs),
        ('Output tables empty', check_output_tables_empty),
    ]

    for name, check_fn in checks_with_weeks:
        print(f'\nChecking: {name}')
        errors = check_fn(conn, args.schema)
        all_errors.extend(errors)
        for e in errors:
            print(f'  [FAIL] {e}')

    conn.close()

    print('\n' + '=' * 60)
    if all_errors:
        print(f'VALIDATION FAILED: {len(all_errors)} error(s)')
        for e in all_errors:
            print(f'  - {e}')
        sys.exit(1)
    else:
        print('VALIDATION PASSED: All checks OK')


if __name__ == '__main__':
    main()
