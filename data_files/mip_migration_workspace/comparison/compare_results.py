#!/usr/bin/env python3
"""
Compare two JSON metric files (v4 vs mip-dev) and produce a formatted report.

Shows differences in:
  - Timing (data load, build, solve, total)
  - Model size (variables, constraints)
  - Objective value
  - Capacity by tech/period
  - Flow by tech/period
  - LP file size

Usage:
  python compare_results.py v4_metrics.json mipdev_metrics.json

  # Custom thresholds
  python compare_results.py v4_metrics.json mipdev_metrics.json \\
    --obj-threshold 0.001 --cap-threshold 1.0 --flow-threshold 1.0
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def pct_diff(a: float, b: float) -> float | None:
    """Percentage difference: (a - b) / b * 100. Returns None if b is zero."""
    if b == 0:
        return None
    return (a - b) / abs(b) * 100


def format_pct(val: float | None) -> str:
    if val is None:
        return 'N/A'
    return f'{val:+.2f}%'


def format_num(val: float | None, decimals: int = 2) -> str:
    if val is None:
        return 'N/A'
    if abs(val) >= 1e6:
        return f'{val:,.{decimals}f}'
    return f'{val:.{decimals}f}'


def compare_timing(v4: dict, mipdev: dict) -> list[str]:
    """Compare timing metrics."""
    lines = []
    lines.append('TIMING')
    lines.append('-' * 70)

    v4_t = v4.get('timing', {})
    md_t = mipdev.get('timing', {})

    fields = [
        ('config_load', 'Config load'),
        ('data_load', 'Data load'),
        ('build', 'Build'),
        ('solve', 'Solve'),
        ('write_results', 'Write results'),
        ('total', 'Total'),
    ]

    lines.append(f'  {"Phase":<20s} {"v4 (s)":>10s} {"mip-dev (s)":>12s} {"Ratio":>8s}')
    lines.append(f'  {"-----":<20s} {"------":>10s} {"-----------":>12s} {"-----":>8s}')

    for key, label in fields:
        v4_val = v4_t.get(key)
        md_val = md_t.get(key)

        v4_str = f'{v4_val:.2f}' if v4_val is not None else '-'
        md_str = f'{md_val:.2f}' if md_val is not None else '-'

        if v4_val is not None and md_val is not None and md_val > 0:
            ratio = f'{v4_val / md_val:.1f}x'
        else:
            ratio = '-'

        lines.append(f'  {label:<20s} {v4_str:>10s} {md_str:>12s} {ratio:>8s}')

    return lines


def compare_model_size(v4: dict, mipdev: dict) -> list[str]:
    """Compare model size (variables and constraints)."""
    lines = []
    lines.append('')
    lines.append('MODEL SIZE')
    lines.append('-' * 70)

    v4_ms = v4.get('model_size', {})
    md_ms = mipdev.get('model_size', {})

    fields = [('variables', 'Variables'), ('constraints', 'Constraints')]

    lines.append(f'  {"Metric":<20s} {"v4":>12s} {"mip-dev":>12s} {"Diff":>10s} {"% Diff":>10s}')
    lines.append(f'  {"------":<20s} {"--":>12s} {"-------":>12s} {"----":>10s} {"------":>10s}')

    for key, label in fields:
        v4_val = v4_ms.get(key)
        md_val = md_ms.get(key)

        v4_str = f'{v4_val:,}' if v4_val is not None else '-'
        md_str = f'{md_val:,}' if md_val is not None else '-'

        if v4_val is not None and md_val is not None:
            diff = v4_val - md_val
            pct = pct_diff(v4_val, md_val)
            diff_str = f'{diff:+,}'
            pct_str = format_pct(pct)
        else:
            diff_str = '-'
            pct_str = '-'

        lines.append(f'  {label:<20s} {v4_str:>12s} {md_str:>12s} {diff_str:>10s} {pct_str:>10s}')

    return lines


def compare_objective(v4: dict, mipdev: dict, threshold: float) -> list[str]:
    """Compare objective values."""
    lines = []
    lines.append('')
    lines.append('OBJECTIVE')
    lines.append('-' * 70)

    v4_r = v4.get('results', {})
    md_r = mipdev.get('results', {})

    # v4 may have objective at top level or in results
    v4_obj = v4.get('objective') or v4_r.get('objective')
    md_obj = md_r.get('objective')

    lines.append(f'  v4:      {format_num(v4_obj, 4)}')
    lines.append(f'  mip-dev: {format_num(md_obj, 4)}')

    if v4_obj is not None and md_obj is not None:
        diff = v4_obj - md_obj
        pct = pct_diff(v4_obj, md_obj)
        lines.append(f'  Diff:    {format_num(diff, 4)} ({format_pct(pct)})')

        if pct is not None and abs(pct) < threshold * 100:
            lines.append(f'  Status:  PASS (within {threshold * 100:.1f}% threshold)')
        else:
            lines.append(f'  Status:  FAIL (exceeds {threshold * 100:.1f}% threshold)')
    else:
        lines.append('  Status:  INCOMPLETE (missing data)')

    return lines


def compare_dict_values(
    v4_dict: dict,
    md_dict: dict,
    label: str,
    abs_threshold: float,
    pct_threshold: float,
) -> list[str]:
    """Compare two dictionaries of numeric values (capacity or flow)."""
    lines = []
    lines.append('')
    lines.append(f'{label.upper()}')
    lines.append('-' * 70)

    all_keys = sorted(set(v4_dict.keys()) | set(md_dict.keys()))

    if not all_keys:
        lines.append('  No data available')
        return lines

    # Find differences
    diffs = []
    for key in all_keys:
        v4_val = v4_dict.get(key, 0.0)
        md_val = md_dict.get(key, 0.0)
        abs_diff = v4_val - md_val
        pct = pct_diff(v4_val, md_val) if md_val != 0 else None

        flagged = abs(abs_diff) > abs_threshold or (pct is not None and abs(pct) > pct_threshold)

        diffs.append((key, v4_val, md_val, abs_diff, pct, flagged))

    n_total = len(diffs)
    n_flagged = sum(1 for d in diffs if d[5])
    n_v4_only = sum(1 for k in all_keys if k not in md_dict)
    n_md_only = sum(1 for k in all_keys if k not in v4_dict)

    lines.append(f'  Total entries: {n_total}')
    lines.append(f'  Flagged (>{abs_threshold} abs or >{pct_threshold}%): {n_flagged}')
    if n_v4_only:
        lines.append(f'  v4 only: {n_v4_only}')
    if n_md_only:
        lines.append(f'  mip-dev only: {n_md_only}')

    if n_flagged > 0:
        lines.append('')
        lines.append(f'  {"Key":<40s} {"v4":>12s} {"mip-dev":>12s} {"Diff":>12s} {"% Diff":>8s}')
        lines.append(f'  {"---":<40s} {"--":>12s} {"-------":>12s} {"----":>12s} {"------":>8s}')

        flagged_items = [d for d in diffs if d[5]]
        # Sort by absolute difference descending
        flagged_items.sort(key=lambda x: abs(x[3]), reverse=True)

        for key, v4_val, md_val, abs_diff, pct, _ in flagged_items[:30]:
            lines.append(
                f'  {key:<40s} {format_num(v4_val, 2):>12s}'
                f' {format_num(md_val, 2):>12s}'
                f' {format_num(abs_diff, 2):>12s} {format_pct(pct):>8s}'
            )

        if len(flagged_items) > 30:
            lines.append(f'  ... and {len(flagged_items) - 30} more')

    return lines


def compare_lp(v4: dict, mipdev: dict) -> list[str]:
    """Compare LP file information."""
    lines = []

    v4_lp_size = v4.get('lp_size_mb')
    md_lp_size = mipdev.get('lp_size_mb')

    if v4_lp_size is not None or md_lp_size is not None:
        lines.append('')
        lines.append('LP FILE')
        lines.append('-' * 70)
        if v4_lp_size is not None:
            lines.append(f'  v4 LP size: {v4_lp_size:.1f} MB')
        if md_lp_size is not None:
            lines.append(f'  mip-dev LP size: {md_lp_size:.1f} MB')

    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description='Compare v4 and mip-dev metrics')
    parser.add_argument('v4_json', type=Path, help='v4 metrics JSON file')
    parser.add_argument('mipdev_json', type=Path, help='mip-dev metrics JSON file')
    parser.add_argument(
        '--obj-threshold',
        type=float,
        default=0.001,
        help='Objective relative diff threshold for PASS/FAIL (default: 0.001 = 0.1%%)',
    )
    parser.add_argument(
        '--cap-threshold',
        type=float,
        default=1.0,
        help='Capacity absolute threshold in MW (default: 1.0)',
    )
    parser.add_argument(
        '--flow-threshold',
        type=float,
        default=1.0,
        help='Flow absolute threshold in MWh (default: 1.0)',
    )
    parser.add_argument(
        '--pct-threshold',
        type=float,
        default=1.0,
        help='Percentage threshold for capacity/flow flagging (default: 1.0%%)',
    )
    parser.add_argument(
        '--flow-scale',
        type=float,
        default=1.0,
        help='Scale factor for mip-dev flows before comparison. Use 672/8760=0.07671 '
        'when mip-dev uses C2A=8760 and v4 uses C2A=672 (default: 1.0)',
    )
    args = parser.parse_args()

    for p in [args.v4_json, args.mipdev_json]:
        if not p.exists():
            print(f'Error: file not found: {p}')
            sys.exit(1)

    with open(args.v4_json) as f:
        v4 = json.load(f)
    with open(args.mipdev_json) as f:
        mipdev = json.load(f)

    # Header
    report = []
    report.append('=' * 70)
    report.append('  TEMOA v4 vs mip-dev COMPARISON REPORT')
    report.append('=' * 70)
    report.append(f'  v4 source:      {v4.get("config", v4.get("database", "?"))}')
    report.append(f'  mip-dev source:  {mipdev.get("database", "?")}')
    report.append(f'  v4 scenario:     {v4.get("scenario", "?")}')
    report.append(f'  mip-dev scenario: {mipdev.get("scenario", "?")}')
    report.append(f'  v4 mode:         {v4.get("mode", "?")}')
    report.append('')

    # Timing
    report.extend(compare_timing(v4, mipdev))

    # Model size
    report.extend(compare_model_size(v4, mipdev))

    # LP
    report.extend(compare_lp(v4, mipdev))

    # Objective
    v4_r = v4.get('results', {})
    md_r = mipdev.get('results', {})

    if v4_r.get('objective') is not None or md_r.get('objective') is not None:
        report.extend(compare_objective(v4, mipdev, args.obj_threshold))

    # Capacity
    v4_cap = v4_r.get('capacity', {})
    md_cap = md_r.get('capacity', {})
    if v4_cap or md_cap:
        report.extend(
            compare_dict_values(
                v4_cap, md_cap, 'Capacity (MW)', args.cap_threshold, args.pct_threshold
            )
        )

    # Flow (apply scaling if mip-dev uses different C2A)
    v4_flow = v4_r.get('flow_out', {})
    md_flow = md_r.get('flow_out', {})
    if args.flow_scale != 1.0:
        md_flow = {k: v * args.flow_scale for k, v in md_flow.items()}
        flow_label = f'Flow Out (MWh, mip-dev scaled by {args.flow_scale:.4f})'
    else:
        flow_label = 'Flow Out (MWh)'
    if v4_flow or md_flow:
        report.extend(
            compare_dict_values(
                v4_flow, md_flow, flow_label, args.flow_threshold, args.pct_threshold
            )
        )

    report.append('')
    report.append('=' * 70)

    output = '\n'.join(report)
    print(output)

    # Also write to file
    report_path = args.v4_json.parent / 'comparison_report.txt'
    with open(report_path, 'w') as f:
        f.write(output)
    print(f'\nReport saved to: {report_path}')


if __name__ == '__main__':
    main()
