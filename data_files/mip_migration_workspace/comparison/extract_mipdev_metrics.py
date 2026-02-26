#!/usr/bin/env python3
"""
Extract metrics from a mip-dev output DB into the same JSON format as
run_v4_comparison.py, enabling apples-to-apples comparison.

Reads from v3.1 output tables:
  - Output_Objective  -> objective
  - Output_V_Capacity -> capacity by tech/period
  - Output_VFlow_Out  -> flow by tech/period

Tech names have region prefixes stripped (TRE_wind_1 -> wind_1) to align
with the v4 stripped database naming.

Usage:
  python extract_mipdev_metrics.py <mipdev_output.sqlite> \\
    --scenario jan_4week_mipdev \\
    --output mipdev_metrics.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def get_regions(conn: sqlite3.Connection) -> list[str]:
    """Get region names from the database for prefix stripping."""
    # Try v3.1 regions table patterns
    for table, col in [('regions', 'regions'), ('region', 'region')]:
        try:
            cur = conn.execute(f'SELECT {col} FROM {table}')
            regions = [r[0] for r in cur.fetchall()]
            if regions:
                return sorted(regions, key=len, reverse=True)
        except sqlite3.OperationalError:
            continue
    return []


def strip_region_prefix(tech: str, regions: list[str]) -> str:
    """Strip region prefix from a tech name.

    Handles both prefix (TRE_wind_1) and embedded (water_import_TRE_hydro)
    patterns. Regions are tried longest-first so TREW matches before TRE.
    """
    for r in regions:
        prefix = r + '_'
        if tech.startswith(prefix):
            return tech[len(prefix) :]

    for r in regions:
        pattern = '_' + r + '_'
        if pattern in tech:
            return tech.replace(pattern, '_', 1)

    return tech


def extract_metrics(db_path: Path, scenario: str) -> dict:
    """Extract metrics from a mip-dev (v3.1) output database."""
    conn = sqlite3.connect(db_path)
    regions = get_regions(conn)

    metrics: dict = {
        'branch': 'mip-dev',
        'database': str(db_path),
        'scenario': scenario,
    }

    # Objective
    try:
        cur = conn.execute(
            'SELECT total_system_cost FROM Output_Objective WHERE scenario = ?',
            (scenario,),
        )
        row = cur.fetchone()
        metrics['objective'] = row[0] if row else None
    except sqlite3.OperationalError:
        metrics['objective'] = None

    # Capacity by tech and period
    try:
        cur = conn.execute(
            """
            SELECT t_periods, tech, SUM(capacity) as total_cap
            FROM Output_V_Capacity
            WHERE scenario = ?
            GROUP BY t_periods, tech
            ORDER BY t_periods, tech
        """,
            (scenario,),
        )
        capacity = {}
        for period, tech, cap in cur.fetchall():
            stripped = strip_region_prefix(tech, regions)
            key = f'{stripped}_{period}'
            # Aggregate in case multiple regions map to same stripped name
            capacity[key] = round(capacity.get(key, 0) + cap, 4)
        metrics['capacity'] = capacity
    except sqlite3.OperationalError:
        metrics['capacity'] = {}

    # Flow out by tech and period (annual sums)
    # Prefer Output_VFlow_Out_Annual, fall back to Output_VFlow_Out, then Output_VFlow_Out2
    flows = {}
    for flow_table in ['Output_VFlow_Out_Annual', 'Output_VFlow_Out', 'Output_VFlow_Out2']:
        try:
            cur = conn.execute(
                f"""
                SELECT t_periods, tech, SUM(vflow_out) as total_flow
                FROM {flow_table}
                WHERE scenario = ?
                GROUP BY t_periods, tech
                ORDER BY t_periods, tech
            """,
                (scenario,),
            )
            rows = cur.fetchall()
            if rows:
                for period, tech, flow in rows:
                    stripped = strip_region_prefix(tech, regions)
                    key = f'{stripped}_{period}'
                    flows[key] = round(flows.get(key, 0) + flow, 4)
                break
        except sqlite3.OperationalError:
            continue
    metrics['flow_out'] = flows

    # Wrap in results dict for consistency with v4 metrics format
    results = {
        'objective': metrics.pop('objective'),
        'capacity': metrics.pop('capacity'),
        'flow_out': metrics.pop('flow_out'),
    }
    metrics['results'] = results

    conn.close()
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description='Extract metrics from a mip-dev output DB')
    parser.add_argument('database', type=Path, help='mip-dev output SQLite database')
    parser.add_argument(
        '--scenario',
        required=True,
        help='Scenario name to extract',
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help='Output JSON file (default: mipdev_metrics.json next to DB)',
    )
    args = parser.parse_args()

    if not args.database.exists():
        print(f'Error: database not found: {args.database}')
        sys.exit(1)

    output_json = args.output or args.database.parent / 'mipdev_metrics.json'

    print(f'Extracting metrics from: {args.database}')
    print(f'Scenario: {args.scenario}')

    metrics = extract_metrics(args.database, args.scenario)

    # Print summary
    results = metrics.get('results', {})
    obj = results.get('objective')
    n_cap = len(results.get('capacity', {}))
    n_flow = len(results.get('flow_out', {}))

    print(f'\nObjective: {obj}')
    print(f'Capacity entries: {n_cap}')
    print(f'Flow entries: {n_flow}')

    with open(output_json, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f'\nMetrics written to: {output_json}')


if __name__ == '__main__':
    main()
