#!/usr/bin/env python3
"""
Systematic v4 vs mip-dev diagnostic comparison.

Extracts inputs and outputs from both databases, computes scaling-invariant
metrics, and produces CSV files + a text report. Eliminates the need for
ad-hoc sqlite queries.

Usage:
  python diagnostic_comparison.py \
    --v4-db path/to/v4.sqlite \
    --v4-scenario jan_4week_v4 \
    --mipdev-db path/to/mipdev.sqlite \
    --mipdev-scenario jan_4week_mipdev \
    --output-dir diagnostics
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Region prefix stripping (reused from extract_mipdev_metrics.py)
# ---------------------------------------------------------------------------


def get_regions(conn: sqlite3.Connection) -> list[str]:
    """Get region names from the database for prefix stripping."""
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

    Handles prefix (TRE_wind_1) and embedded (water_import_TRE_hydro) patterns.
    Regions are tried longest-first so TREW matches before TRE.
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


def strip_col(df: pd.DataFrame, col: str, regions: list[str]) -> pd.DataFrame:
    """Strip region prefixes from a column in-place, return df."""
    if col in df.columns and regions:
        df[col] = df[col].apply(lambda t: strip_region_prefix(t, regions))
    return df


# ---------------------------------------------------------------------------
# Phase 1: Extract inputs
# ---------------------------------------------------------------------------


def extract_demand(conn: sqlite3.Connection, schema: str) -> pd.DataFrame:
    if schema == 'v4':
        return pd.read_sql_query('SELECT region, period, commodity, demand FROM demand', conn)
    else:
        df = pd.read_sql_query(
            'SELECT regions AS region, periods AS period, demand_comm AS commodity, '
            'demand FROM Demand',
            conn,
        )
        return df


def extract_segfrac(conn: sqlite3.Connection, schema: str) -> pd.DataFrame:
    if schema == 'v4':
        return pd.read_sql_query(
            'SELECT period, season, tod, segment_fraction AS segfrac FROM time_segment_fraction',
            conn,
        )
    else:
        return pd.read_sql_query(
            'SELECT periods AS period, season_name AS season, '
            'time_of_day_name AS tod, segfrac '
            'FROM SegFrac',
            conn,
        )


def extract_dsd(conn: sqlite3.Connection, schema: str) -> pd.DataFrame:
    if schema == 'v4':
        return pd.read_sql_query(
            'SELECT region, period, season, tod, demand_name, dsd '
            'FROM demand_specific_distribution',
            conn,
        )
    else:
        return pd.read_sql_query(
            'SELECT regions AS region, periods AS period, season_name AS season, '
            'time_of_day_name AS tod, demand_name, dds AS dsd '
            'FROM DemandSpecificDistribution',
            conn,
        )


def extract_c2a(conn: sqlite3.Connection, schema: str, regions: list[str]) -> pd.DataFrame:
    if schema == 'v4':
        return pd.read_sql_query('SELECT region, tech, c2a FROM capacity_to_activity', conn)
    else:
        df = pd.read_sql_query('SELECT regions AS region, tech, c2a FROM CapacityToActivity', conn)
        return strip_col(df, 'tech', regions)


def extract_capacity_factor(
    conn: sqlite3.Connection, schema: str, regions: list[str]
) -> pd.DataFrame:
    if schema == 'v4':
        return pd.read_sql_query(
            'SELECT region, period, season, tod, tech, factor FROM capacity_factor_tech', conn
        )
    else:
        df = pd.read_sql_query(
            'SELECT regions AS region, season_name AS season, '
            'time_of_day_name AS tod, tech, cf_tech AS factor '
            'FROM CapacityFactorTech',
            conn,
        )
        return strip_col(df, 'tech', regions)


def extract_efficiency(conn: sqlite3.Connection, schema: str, regions: list[str]) -> pd.DataFrame:
    if schema == 'v4':
        return pd.read_sql_query(
            'SELECT region, input_comm, tech, vintage, output_comm, efficiency FROM efficiency',
            conn,
        )
    else:
        df = pd.read_sql_query(
            'SELECT regions AS region, input_comm, tech, vintage, output_comm, '
            'efficiency FROM Efficiency',
            conn,
        )
        return strip_col(df, 'tech', regions)


def extract_existing_capacity(
    conn: sqlite3.Connection, schema: str, regions: list[str]
) -> pd.DataFrame:
    if schema == 'v4':
        return pd.read_sql_query(
            'SELECT region, tech, vintage, capacity FROM existing_capacity', conn
        )
    else:
        df = pd.read_sql_query(
            'SELECT regions AS region, tech, vintage, exist_cap AS capacity FROM ExistingCapacity',
            conn,
        )
        return strip_col(df, 'tech', regions)


def extract_days_per_period(conn: sqlite3.Connection, schema: str) -> int | None:
    if schema == 'v4':
        try:
            cur = conn.execute("SELECT value FROM metadata WHERE element = 'days_per_period'")
            row = cur.fetchone()
            return int(row[0]) if row else None
        except sqlite3.OperationalError:
            return None
    return None  # mip-dev has no days_per_period


# ---------------------------------------------------------------------------
# Phase 2: Extract outputs
# ---------------------------------------------------------------------------


def extract_net_capacity(
    conn: sqlite3.Connection, schema: str, scenario: str, regions: list[str]
) -> pd.DataFrame:
    if schema == 'v4':
        df = pd.read_sql_query(
            'SELECT region, period, tech, vintage, capacity '
            'FROM output_net_capacity WHERE scenario = ?',
            conn,
            params=(scenario,),
        )
    else:
        df = pd.read_sql_query(
            'SELECT regions AS region, t_periods AS period, tech, vintage, capacity '
            'FROM Output_V_Capacity WHERE scenario = ?',
            conn,
            params=(scenario,),
        )
        strip_col(df, 'tech', regions)
    return df


def extract_new_capacity(
    conn: sqlite3.Connection, schema: str, scenario: str, regions: list[str]
) -> pd.DataFrame:
    if schema == 'v4':
        df = pd.read_sql_query(
            'SELECT region, tech, vintage, capacity FROM output_built_capacity WHERE scenario = ?',
            conn,
            params=(scenario,),
        )
    else:
        df = pd.read_sql_query(
            'SELECT regions AS region, tech, vintage, capacity '
            'FROM Output_V_NewCapacity WHERE scenario = ?',
            conn,
            params=(scenario,),
        )
        strip_col(df, 'tech', regions)
    return df


def extract_flow_out(
    conn: sqlite3.Connection, schema: str, scenario: str, regions: list[str]
) -> pd.DataFrame:
    if schema == 'v4':
        df = pd.read_sql_query(
            'SELECT region, period, season, tod, input_comm, tech, vintage, '
            'output_comm, flow '
            'FROM output_flow_out WHERE scenario = ?',
            conn,
            params=(scenario,),
        )
    else:
        df = pd.read_sql_query(
            'SELECT regions AS region, t_periods AS period, t_season AS season, '
            't_day AS tod, input_comm, tech, vintage, output_comm, '
            'vflow_out AS flow '
            'FROM Output_VFlow_Out WHERE scenario = ?',
            conn,
            params=(scenario,),
        )
        strip_col(df, 'tech', regions)
    return df


def extract_objective(conn: sqlite3.Connection, schema: str, scenario: str) -> float | None:
    if schema == 'v4':
        table = 'output_objective'
        col = 'total_system_cost'
    else:
        table = 'Output_Objective'
        col = 'total_system_cost'
    try:
        cur = conn.execute(f'SELECT {col} FROM {table} WHERE scenario = ?', (scenario,))
        row = cur.fetchone()
        return float(row[0]) if row else None
    except sqlite3.OperationalError:
        return None


# ---------------------------------------------------------------------------
# Phase 3: Compute metrics
# ---------------------------------------------------------------------------


def compute_capacity_by_tech(cap_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate capacity by tech and period (sum over regions/vintages)."""
    if cap_df.empty:
        return pd.DataFrame(columns=['tech', 'period', 'capacity'])
    return (
        cap_df.groupby(['tech', 'period'])['capacity']
        .sum()
        .reset_index()
        .sort_values(['period', 'tech'])
    )


def compute_generation_by_tech(flow_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate generation by tech and period (sum over timeslices/comms)."""
    if flow_df.empty:
        return pd.DataFrame(columns=['tech', 'period', 'generation'])
    return (
        flow_df.groupby(['tech', 'period'])['flow']
        .sum()
        .rename('generation')
        .reset_index()
        .sort_values(['period', 'tech'])
    )


def compute_mix_shares(agg_df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Compute percentage share of each tech within each period."""
    if agg_df.empty:
        return agg_df
    df = agg_df.copy()
    total = df.groupby('period')[value_col].transform('sum')
    df['share_pct'] = (df[value_col] / total * 100).round(4)
    return df


def compute_implied_cf(
    cap_df: pd.DataFrame,
    gen_df: pd.DataFrame,
    c2a_df: pd.DataFrame,
    segfrac_df: pd.DataFrame,
    regions: list[str],
) -> pd.DataFrame:
    """Compute implied capacity factor = generation / (capacity × C2A × sum_segfrac).

    This metric normalizes out C2A differences.
    """
    if cap_df.empty or gen_df.empty:
        return pd.DataFrame(columns=['tech', 'period', 'implied_cf_pct'])

    cap_agg = compute_capacity_by_tech(cap_df)
    gen_agg = compute_generation_by_tech(gen_df)

    merged = pd.merge(cap_agg, gen_agg, on=['tech', 'period'], how='outer')

    # Get C2A per tech (aggregate across regions via mean — should be uniform)
    if not c2a_df.empty:
        c2a_by_tech = c2a_df.groupby('tech')['c2a'].mean().reset_index()
        merged = pd.merge(merged, c2a_by_tech, on='tech', how='left')
    else:
        merged['c2a'] = None

    # Sum of segfrac per period
    if not segfrac_df.empty:
        sf = segfrac_df.copy()
        sf['period'] = pd.to_numeric(sf['period'], errors='coerce')
        sf_sum = sf.groupby('period')['segfrac'].sum().reset_index()
        sf_sum.rename(columns={'segfrac': 'sum_segfrac'}, inplace=True)
        merged['period'] = pd.to_numeric(merged['period'], errors='coerce')
        merged = pd.merge(merged, sf_sum, on='period', how='left')
    else:
        merged['sum_segfrac'] = None

    # Implied CF = generation / (capacity * C2A * sum_segfrac)
    denom = merged['capacity'] * merged['c2a'] * merged['sum_segfrac']
    merged['implied_cf_pct'] = (merged['generation'] / denom * 100).round(4)

    return merged[
        ['tech', 'period', 'capacity', 'generation', 'c2a', 'sum_segfrac', 'implied_cf_pct']
    ].sort_values(['period', 'tech'])


# ---------------------------------------------------------------------------
# Phase 4: Comparison and reporting
# ---------------------------------------------------------------------------


def compare_inputs(
    v4_df: pd.DataFrame,
    mipdev_df: pd.DataFrame,
    key_cols: list[str],
    value_cols: list[str],
    name: str,
) -> tuple[pd.DataFrame, list[str]]:
    """Compare two input DataFrames. Returns merged DF and report lines."""
    lines = []
    if v4_df.empty and mipdev_df.empty:
        lines.append(f'  {name}: both empty')
        return pd.DataFrame(), lines

    # Normalize types for merging
    for col in key_cols:
        if col in v4_df.columns:
            v4_df[col] = v4_df[col].astype(str)
        if col in mipdev_df.columns:
            mipdev_df[col] = mipdev_df[col].astype(str)

    merged = pd.merge(
        v4_df, mipdev_df, on=key_cols, how='outer', suffixes=('_v4', '_mipdev'), indicator=True
    )

    n_both = (merged['_merge'] == 'both').sum()
    n_v4_only = (merged['_merge'] == 'left_only').sum()
    n_mipdev_only = (merged['_merge'] == 'right_only').sum()

    lines.append(f'  {name}: {n_both} matched, {n_v4_only} v4-only, {n_mipdev_only} mipdev-only')

    # Check value differences in matched rows
    both_mask = merged['_merge'] == 'both'
    for vc in value_cols:
        v4_col = f'{vc}_v4'
        md_col = f'{vc}_mipdev'
        if v4_col in merged.columns and md_col in merged.columns:
            diff_mask = both_mask & ((merged[v4_col] - merged[md_col]).abs() > 1e-6)
            n_diff = diff_mask.sum()
            if n_diff > 0:
                lines.append(f'    -> {vc}: {n_diff} rows differ')

    return merged, lines


def format_section(title: str, lines: list[str]) -> str:
    sep = '=' * 70
    return f'\n{sep}\n{title}\n{sep}\n' + '\n'.join(lines) + '\n'


def build_report(
    input_reports: dict[str, list[str]],
    obj_v4: float | None,
    obj_mipdev: float | None,
    cap_v4: pd.DataFrame,
    cap_mipdev: pd.DataFrame,
    gen_v4: pd.DataFrame,
    gen_mipdev: pd.DataFrame,
    cf_v4: pd.DataFrame,
    cf_mipdev: pd.DataFrame,
    days_per_period_v4: int | None,
    c2a_v4: pd.DataFrame,
    c2a_mipdev: pd.DataFrame,
) -> str:
    """Build the full text report."""
    sections = []

    # Header
    sections.append('TEMOA v4 vs mip-dev Diagnostic Comparison Report')
    sections.append('=' * 70)

    # --- Input diffs ---
    input_lines = []
    for name, lines in input_reports.items():
        input_lines.extend(lines)
    sections.append(format_section('1. INPUT DIFFERENCES', input_lines))

    # --- Known expected diffs ---
    known_lines = []
    known_lines.append(f'  days_per_period: v4={days_per_period_v4}, mipdev=N/A (implicitly 365)')

    if not c2a_v4.empty and not c2a_mipdev.empty:
        v4_vals = sorted(float(v) for v in c2a_v4['c2a'].unique())
        md_vals = sorted(float(v) for v in c2a_mipdev['c2a'].unique())
        known_lines.append(f'  C2A distinct values: v4={v4_vals}, mipdev={md_vals}')
        if v4_vals != md_vals:
            known_lines.append(
                '    -> EXPECTED: v4 uses 672 (28d*24h), mipdev uses 8760 (365d*24h)'
            )
    sections.append(format_section('2. KNOWN EXPECTED DIFFERENCES', known_lines))

    # --- Objective ---
    obj_lines = []
    obj_lines.append(f'  v4:     {obj_v4:>20,.2f}' if obj_v4 else '  v4:     N/A')
    obj_lines.append(f'  mipdev: {obj_mipdev:>20,.2f}' if obj_mipdev else '  mipdev: N/A')
    if obj_v4 and obj_mipdev:
        pct = (obj_v4 - obj_mipdev) / abs(obj_mipdev) * 100
        obj_lines.append(f'  diff:   {pct:+.2f}%')
    sections.append(format_section('3. OBJECTIVE', obj_lines))

    # --- Capacity comparison ---
    cap_lines = _compare_tech_metric(cap_v4, cap_mipdev, 'capacity', 'MW', threshold=1.0)
    sections.append(format_section('4. CAPACITY BY TECH (MW)', cap_lines))

    # --- Generation mix ---
    gen_lines = _compare_tech_metric(gen_v4, gen_mipdev, 'generation', 'MWh', threshold=1.0)
    sections.append(format_section('5. GENERATION BY TECH (MWh)', gen_lines))

    # --- Generation share comparison ---
    share_lines = _compare_shares(gen_v4, gen_mipdev, 'generation')
    sections.append(format_section('6. GENERATION MIX SHARES (%)', share_lines))

    # --- Implied CF ---
    cf_lines = _compare_implied_cf(cf_v4, cf_mipdev)
    sections.append(format_section('7. IMPLIED CAPACITY FACTORS (%)', cf_lines))

    # --- Dispatch status ---
    dispatch_lines = _compare_dispatch(cap_v4, cap_mipdev, gen_v4, gen_mipdev)
    sections.append(format_section('8. TECH DISPATCH STATUS', dispatch_lines))

    # --- Demand coverage ---
    coverage_lines = _demand_coverage(gen_v4, gen_mipdev, obj_v4, obj_mipdev)
    sections.append(format_section('9. DEMAND COVERAGE', coverage_lines))

    return '\n'.join(sections)


def _compare_tech_metric(
    v4_df: pd.DataFrame, mipdev_df: pd.DataFrame, value_col: str, units: str, threshold: float = 1.0
) -> list[str]:
    lines = []
    if v4_df.empty and mipdev_df.empty:
        lines.append('  No data')
        return lines

    merged = pd.merge(
        v4_df[['tech', 'period', value_col]],
        mipdev_df[['tech', 'period', value_col]],
        on=['tech', 'period'],
        how='outer',
        suffixes=('_v4', '_mipdev'),
        indicator=True,
    )

    v4_col = f'{value_col}_v4'
    md_col = f'{value_col}_mipdev'
    merged[v4_col] = merged[v4_col].fillna(0)
    merged[md_col] = merged[md_col].fillna(0)
    merged['abs_diff'] = (merged[v4_col] - merged[md_col]).abs()

    # Header
    lines.append(f'  {"Tech":<45} {"Period":<8} {"v4":>14} {"mipdev":>14} {"diff":>14} {"status"}')
    lines.append(f'  {"-" * 45} {"-" * 8} {"-" * 14} {"-" * 14} {"-" * 14} {"-" * 8}')

    for _, row in merged.sort_values(['period', 'tech']).iterrows():
        v4_val = row[v4_col]
        md_val = row[md_col]
        diff = v4_val - md_val
        status = ''
        if row['_merge'] == 'left_only':
            status = 'v4-only'
        elif row['_merge'] == 'right_only':
            status = 'md-only'
        elif abs(diff) > threshold:
            status = 'DIFF'
        else:
            status = 'OK'

        lines.append(
            f'  {row["tech"]:<45} {row["period"]:<8} '
            f'{v4_val:>14,.2f} {md_val:>14,.2f} {diff:>+14,.2f} {status}'
        )

    # Summary
    n_ok = ((merged['_merge'] == 'both') & (merged['abs_diff'] <= threshold)).sum()
    n_diff = ((merged['_merge'] == 'both') & (merged['abs_diff'] > threshold)).sum()
    n_v4 = (merged['_merge'] == 'left_only').sum()
    n_md = (merged['_merge'] == 'right_only').sum()
    lines.append(
        f'\n  Summary: {n_ok} match (within {threshold} {units}), '
        f'{n_diff} differ, {n_v4} v4-only, {n_md} mipdev-only'
    )
    return lines


def _compare_shares(v4_df: pd.DataFrame, mipdev_df: pd.DataFrame, value_col: str) -> list[str]:
    lines = []
    v4_shares = compute_mix_shares(v4_df.copy(), value_col) if not v4_df.empty else pd.DataFrame()
    md_shares = (
        compute_mix_shares(mipdev_df.copy(), value_col) if not mipdev_df.empty else pd.DataFrame()
    )

    if v4_shares.empty and md_shares.empty:
        lines.append('  No data')
        return lines

    merged = pd.merge(
        v4_shares[['tech', 'period', 'share_pct']],
        md_shares[['tech', 'period', 'share_pct']],
        on=['tech', 'period'],
        how='outer',
        suffixes=('_v4', '_mipdev'),
        indicator=True,
    )
    merged['share_pct_v4'] = merged['share_pct_v4'].fillna(0)
    merged['share_pct_mipdev'] = merged['share_pct_mipdev'].fillna(0)
    merged['diff_pp'] = merged['share_pct_v4'] - merged['share_pct_mipdev']

    lines.append(
        f'  {"Tech":<45} {"Period":<8} {"v4 %":>8} {"mipdev %":>8} {"diff pp":>8} {"flag"}'
    )
    lines.append(f'  {"-" * 45} {"-" * 8} {"-" * 8} {"-" * 8} {"-" * 8} {"-" * 6}')

    for _, row in merged.sort_values(
        ['period', 'share_pct_v4'], ascending=[True, False]
    ).iterrows():
        flag = ' ***' if abs(row['diff_pp']) > 2.0 else ''
        lines.append(
            f'  {row["tech"]:<45} {row["period"]:<8} '
            f'{row["share_pct_v4"]:>8.2f} {row["share_pct_mipdev"]:>8.2f} '
            f'{row["diff_pp"]:>+8.2f}{flag}'
        )

    n_flagged = (merged['diff_pp'].abs() > 2.0).sum()
    lines.append(f'\n  {n_flagged} techs differ by >2 percentage points')
    return lines


def _compare_implied_cf(cf_v4: pd.DataFrame, cf_mipdev: pd.DataFrame) -> list[str]:
    lines = []
    if cf_v4.empty and cf_mipdev.empty:
        lines.append('  No data')
        return lines

    cols = ['tech', 'period', 'implied_cf_pct']
    v4_sub = cf_v4[cols].copy() if not cf_v4.empty else pd.DataFrame(columns=cols)
    md_sub = cf_mipdev[cols].copy() if not cf_mipdev.empty else pd.DataFrame(columns=cols)

    merged = pd.merge(
        v4_sub,
        md_sub,
        on=['tech', 'period'],
        how='outer',
        suffixes=('_v4', '_mipdev'),
        indicator=True,
    )
    merged['implied_cf_pct_v4'] = merged['implied_cf_pct_v4'].fillna(0)
    merged['implied_cf_pct_mipdev'] = merged['implied_cf_pct_mipdev'].fillna(0)
    merged['diff_pp'] = merged['implied_cf_pct_v4'] - merged['implied_cf_pct_mipdev']

    lines.append(
        f'  {"Tech":<45} {"Period":<8} {"v4 CF%":>8} {"md CF%":>8} {"diff pp":>8} {"flag"}'
    )
    lines.append(f'  {"-" * 45} {"-" * 8} {"-" * 8} {"-" * 8} {"-" * 8} {"-" * 6}')

    for _, row in merged.sort_values(['period', 'tech']).iterrows():
        flag = ' ***' if abs(row['diff_pp']) > 5.0 else ''
        lines.append(
            f'  {row["tech"]:<45} {row["period"]:<8} '
            f'{row["implied_cf_pct_v4"]:>8.2f} {row["implied_cf_pct_mipdev"]:>8.2f} '
            f'{row["diff_pp"]:>+8.2f}{flag}'
        )

    n_flagged = (merged['diff_pp'].abs() > 5.0).sum()
    lines.append(f'\n  {n_flagged} techs differ by >5 percentage points')
    return lines


def _compare_dispatch(
    cap_v4: pd.DataFrame, cap_mipdev: pd.DataFrame, gen_v4: pd.DataFrame, gen_mipdev: pd.DataFrame
) -> list[str]:
    """Identify techs with capacity but zero generation (or vice versa)."""
    lines = []

    def dispatch_status(cap_df, gen_df, label):
        if cap_df.empty:
            return []
        cap_techs = set(zip(cap_df['tech'], cap_df['period']))
        gen_techs = set(zip(gen_df['tech'], gen_df['period'])) if not gen_df.empty else set()

        idle = cap_techs - gen_techs
        if idle:
            result = [f'  {label} — techs with capacity but zero dispatch:']
            for tech, period in sorted(idle):
                cap_val = cap_df[(cap_df['tech'] == tech) & (cap_df['period'] == period)][
                    'capacity'
                ].sum()
                result.append(f'    {tech:<45} period={period}  cap={cap_val:,.1f} MW')
            return result
        return [f'  {label} — all techs with capacity are dispatching']

    lines.extend(dispatch_status(cap_v4, gen_v4, 'v4'))
    lines.append('')
    lines.extend(dispatch_status(cap_mipdev, gen_mipdev, 'mipdev'))

    return lines


def _demand_coverage(
    gen_v4: pd.DataFrame, gen_mipdev: pd.DataFrame, obj_v4: float | None, obj_mipdev: float | None
) -> list[str]:
    """Total generation for context (not a direct demand comparison, since
    absolute values differ by C2A scaling)."""
    lines = []
    v4_total = gen_v4['generation'].sum() if not gen_v4.empty else 0
    md_total = gen_mipdev['generation'].sum() if not gen_mipdev.empty else 0

    lines.append('  Total generation:')
    lines.append(f'    v4:     {v4_total:>20,.2f} MWh')
    lines.append(f'    mipdev: {md_total:>20,.2f} MWh')
    if md_total > 0:
        ratio = v4_total / md_total
        lines.append(f'    ratio:  {ratio:.4f}  (expected ~{28 / 365:.4f} = 28/365 if C2A differs)')
    return lines


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description='Systematic v4 vs mip-dev diagnostic comparison')
    parser.add_argument('--v4-db', type=Path, required=True, help='Path to v4 output database')
    parser.add_argument('--v4-scenario', type=str, required=True, help='v4 scenario name')
    parser.add_argument(
        '--mipdev-db', type=Path, required=True, help='Path to mip-dev output database'
    )
    parser.add_argument('--mipdev-scenario', type=str, required=True, help='mip-dev scenario name')
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('diagnostics'),
        help='Output directory for CSVs and report',
    )
    args = parser.parse_args()

    for db, label in [(args.v4_db, 'v4'), (args.mipdev_db, 'mipdev')]:
        if not db.exists():
            print(f'Error: {label} database not found: {db}')
            sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    print(f'v4 DB:     {args.v4_db}')
    print(f'v4 scenario: {args.v4_scenario}')
    print(f'mipdev DB: {args.mipdev_db}')
    print(f'mipdev scenario: {args.mipdev_scenario}')
    print(f'Output:    {args.output_dir}')
    print()

    conn_v4 = sqlite3.connect(args.v4_db)
    conn_md = sqlite3.connect(args.mipdev_db)
    regions_md = get_regions(conn_md)
    print(f'mip-dev regions (for prefix stripping): {regions_md}')

    # -----------------------------------------------------------------------
    # Phase 1: Inputs
    # -----------------------------------------------------------------------
    print('\n--- Phase 1: Extracting inputs ---')
    input_reports: dict[str, list[str]] = {}

    # Demand
    dem_v4 = extract_demand(conn_v4, 'v4')
    dem_md = extract_demand(conn_md, 'mipdev')
    dem_merged, dem_lines = compare_inputs(
        dem_v4, dem_md, ['region', 'period', 'commodity'], ['demand'], 'Demand'
    )
    input_reports['Demand'] = dem_lines
    dem_merged.to_csv(args.output_dir / 'inputs_demand.csv', index=False)

    # SegFrac
    sf_v4 = extract_segfrac(conn_v4, 'v4')
    sf_md = extract_segfrac(conn_md, 'mipdev')
    sf_merged, sf_lines = compare_inputs(
        sf_v4, sf_md, ['period', 'season', 'tod'], ['segfrac'], 'SegFrac'
    )
    input_reports['SegFrac'] = sf_lines
    sf_merged.to_csv(args.output_dir / 'inputs_segfrac.csv', index=False)

    # DSD
    dsd_v4 = extract_dsd(conn_v4, 'v4')
    dsd_md = extract_dsd(conn_md, 'mipdev')
    dsd_merged, dsd_lines = compare_inputs(
        dsd_v4, dsd_md, ['region', 'period', 'season', 'tod', 'demand_name'], ['dsd'], 'DSD'
    )
    input_reports['DSD'] = dsd_lines
    dsd_merged.to_csv(args.output_dir / 'inputs_dsd.csv', index=False)

    # C2A
    c2a_v4 = extract_c2a(conn_v4, 'v4', [])
    c2a_md = extract_c2a(conn_md, 'mipdev', regions_md)
    c2a_merged, c2a_lines = compare_inputs(c2a_v4, c2a_md, ['region', 'tech'], ['c2a'], 'C2A')
    input_reports['C2A'] = c2a_lines
    c2a_merged.to_csv(args.output_dir / 'inputs_c2a.csv', index=False)

    # CapacityFactor — mip-dev has no period column, so compare without it
    cf_v4 = extract_capacity_factor(conn_v4, 'v4', [])
    cf_md = extract_capacity_factor(conn_md, 'mipdev', regions_md)
    # mip-dev CF has no period; for comparison, drop period from v4 and dedup
    cf_v4_noperiod = cf_v4.drop(columns=['period'], errors='ignore').drop_duplicates()
    cf_merged, cf_lines = compare_inputs(
        cf_v4_noperiod, cf_md, ['region', 'season', 'tod', 'tech'], ['factor'], 'CapacityFactor'
    )
    input_reports['CapacityFactor'] = cf_lines
    cf_merged.to_csv(args.output_dir / 'inputs_capacity_factor.csv', index=False)

    # Efficiency
    eff_v4 = extract_efficiency(conn_v4, 'v4', [])
    eff_md = extract_efficiency(conn_md, 'mipdev', regions_md)
    eff_merged, eff_lines = compare_inputs(
        eff_v4,
        eff_md,
        ['region', 'input_comm', 'tech', 'vintage', 'output_comm'],
        ['efficiency'],
        'Efficiency',
    )
    input_reports['Efficiency'] = eff_lines
    eff_merged.to_csv(args.output_dir / 'inputs_efficiency.csv', index=False)

    # ExistingCapacity
    ec_v4 = extract_existing_capacity(conn_v4, 'v4', [])
    ec_md = extract_existing_capacity(conn_md, 'mipdev', regions_md)
    ec_merged, ec_lines = compare_inputs(
        ec_v4, ec_md, ['region', 'tech', 'vintage'], ['capacity'], 'ExistingCapacity'
    )
    input_reports['ExistingCapacity'] = ec_lines
    ec_merged.to_csv(args.output_dir / 'inputs_existing_capacity.csv', index=False)

    # days_per_period
    dpp_v4 = extract_days_per_period(conn_v4, 'v4')
    dpp_md = extract_days_per_period(conn_md, 'mipdev')
    input_reports['days_per_period'] = [
        f'  days_per_period: v4={dpp_v4}, mipdev={dpp_md} (N/A = not present)'
    ]

    for name, lines in input_reports.items():
        for line in lines:
            print(line)

    # -----------------------------------------------------------------------
    # Phase 2: Outputs
    # -----------------------------------------------------------------------
    print('\n--- Phase 2: Extracting outputs ---')

    # Objective
    obj_v4 = extract_objective(conn_v4, 'v4', args.v4_scenario)
    obj_md = extract_objective(conn_md, 'mipdev', args.mipdev_scenario)
    obj_df = pd.DataFrame({'branch': ['v4', 'mipdev'], 'objective': [obj_v4, obj_md]})
    obj_df.to_csv(args.output_dir / 'objective.csv', index=False)
    print(f'  Objective: v4={obj_v4:,.2f}, mipdev={obj_md:,.2f}')

    # Net capacity
    netcap_v4 = extract_net_capacity(conn_v4, 'v4', args.v4_scenario, [])
    netcap_md = extract_net_capacity(conn_md, 'mipdev', args.mipdev_scenario, regions_md)
    netcap_v4.to_csv(args.output_dir / 'capacity_v4_raw.csv', index=False)
    netcap_md.to_csv(args.output_dir / 'capacity_mipdev_raw.csv', index=False)
    print(f'  Net capacity rows: v4={len(netcap_v4)}, mipdev={len(netcap_md)}')

    # New capacity
    newcap_v4 = extract_new_capacity(conn_v4, 'v4', args.v4_scenario, [])
    newcap_md = extract_new_capacity(conn_md, 'mipdev', args.mipdev_scenario, regions_md)
    newcap_v4.to_csv(args.output_dir / 'new_capacity_v4_raw.csv', index=False)
    newcap_md.to_csv(args.output_dir / 'new_capacity_mipdev_raw.csv', index=False)
    print(f'  New capacity rows: v4={len(newcap_v4)}, mipdev={len(newcap_md)}')

    # Flow out
    flow_v4 = extract_flow_out(conn_v4, 'v4', args.v4_scenario, [])
    flow_md = extract_flow_out(conn_md, 'mipdev', args.mipdev_scenario, regions_md)
    flow_v4.to_csv(args.output_dir / 'flow_out_v4_raw.csv', index=False)
    flow_md.to_csv(args.output_dir / 'flow_out_mipdev_raw.csv', index=False)
    print(f'  Flow out rows: v4={len(flow_v4)}, mipdev={len(flow_md)}')

    # -----------------------------------------------------------------------
    # Phase 3: Metrics
    # -----------------------------------------------------------------------
    print('\n--- Phase 3: Computing metrics ---')

    # Aggregated capacity
    cap_v4_agg = compute_capacity_by_tech(netcap_v4)
    cap_md_agg = compute_capacity_by_tech(netcap_md)

    # Aggregated generation
    gen_v4_agg = compute_generation_by_tech(flow_v4)
    gen_md_agg = compute_generation_by_tech(flow_md)

    # Implied CF
    icf_v4 = compute_implied_cf(netcap_v4, flow_v4, c2a_v4, sf_v4, [])
    icf_md = compute_implied_cf(netcap_md, flow_md, c2a_md, sf_md, regions_md)

    # Save metrics CSVs
    cap_merged = pd.merge(
        cap_v4_agg.rename(columns={'capacity': 'capacity_v4'}),
        cap_md_agg.rename(columns={'capacity': 'capacity_mipdev'}),
        on=['tech', 'period'],
        how='outer',
    )
    cap_merged.to_csv(args.output_dir / 'capacity_comparison.csv', index=False)

    gen_merged = pd.merge(
        gen_v4_agg.rename(columns={'generation': 'generation_v4'}),
        gen_md_agg.rename(columns={'generation': 'generation_mipdev'}),
        on=['tech', 'period'],
        how='outer',
    )
    gen_merged.to_csv(args.output_dir / 'generation_comparison.csv', index=False)

    # Shares
    gen_v4_shares = (
        compute_mix_shares(gen_v4_agg.copy(), 'generation')
        if not gen_v4_agg.empty
        else pd.DataFrame()
    )
    gen_md_shares = (
        compute_mix_shares(gen_md_agg.copy(), 'generation')
        if not gen_md_agg.empty
        else pd.DataFrame()
    )
    if not gen_v4_shares.empty or not gen_md_shares.empty:
        shares_merged = pd.merge(
            gen_v4_shares[['tech', 'period', 'share_pct']].rename(
                columns={'share_pct': 'share_pct_v4'}
            )
            if not gen_v4_shares.empty
            else pd.DataFrame(columns=['tech', 'period', 'share_pct_v4']),
            gen_md_shares[['tech', 'period', 'share_pct']].rename(
                columns={'share_pct': 'share_pct_mipdev'}
            )
            if not gen_md_shares.empty
            else pd.DataFrame(columns=['tech', 'period', 'share_pct_mipdev']),
            on=['tech', 'period'],
            how='outer',
        )
        shares_merged.to_csv(args.output_dir / 'generation_shares.csv', index=False)

    # Implied CF
    cf_merged = pd.merge(
        icf_v4[['tech', 'period', 'implied_cf_pct']].rename(
            columns={'implied_cf_pct': 'implied_cf_pct_v4'}
        )
        if not icf_v4.empty
        else pd.DataFrame(columns=['tech', 'period', 'implied_cf_pct_v4']),
        icf_md[['tech', 'period', 'implied_cf_pct']].rename(
            columns={'implied_cf_pct': 'implied_cf_pct_mipdev'}
        )
        if not icf_md.empty
        else pd.DataFrame(columns=['tech', 'period', 'implied_cf_pct_mipdev']),
        on=['tech', 'period'],
        how='outer',
    )
    cf_merged.to_csv(args.output_dir / 'implied_cf_comparison.csv', index=False)

    print(f'  Capacity: {len(cap_v4_agg)} v4 techs, {len(cap_md_agg)} mipdev techs')
    print(f'  Generation: {len(gen_v4_agg)} v4 techs, {len(gen_md_agg)} mipdev techs')
    print(f'  Implied CF: {len(icf_v4)} v4 techs, {len(icf_md)} mipdev techs')

    # -----------------------------------------------------------------------
    # Phase 4: Report
    # -----------------------------------------------------------------------
    print('\n--- Phase 4: Building report ---')

    report = build_report(
        input_reports=input_reports,
        obj_v4=obj_v4,
        obj_mipdev=obj_md,
        cap_v4=cap_v4_agg,
        cap_mipdev=cap_md_agg,
        gen_v4=gen_v4_agg,
        gen_mipdev=gen_md_agg,
        cf_v4=icf_v4,
        cf_mipdev=icf_md,
        days_per_period_v4=dpp_v4,
        c2a_v4=c2a_v4,
        c2a_mipdev=c2a_md,
    )

    report_path = args.output_dir / 'diagnostic_report.txt'
    with open(report_path, 'w') as f:
        f.write(report)

    print(f'\nReport written to: {report_path}')
    print(f'CSVs written to:   {args.output_dir}/')

    # Print report to stdout as well
    print('\n' + report)

    conn_v4.close()
    conn_md.close()


if __name__ == '__main__':
    main()
