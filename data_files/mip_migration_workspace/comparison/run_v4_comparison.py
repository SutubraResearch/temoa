#!/usr/bin/env python3
"""
Build and optionally solve a v4 Temoa model, capturing metrics to JSON.

Two modes:
  --build-only  Fast iteration: load data, build instance, save LP, capture
                var/constraint counts and timings. No solver needed.

  (default)     Full run: build + solve with Gurobi, write results to DB,
                extract objective/capacity/flow data.

Must be run from the project root (temoa-SRfork/).

Usage:
  python data_files/mip_migration_workspace/comparison/run_v4_comparison.py \\
    --config data_files/mip_migration_workspace/comparison/config_comparison_v4.toml \\
    --build-only

  python data_files/mip_migration_workspace/comparison/run_v4_comparison.py \\
    --config data_files/mip_migration_workspace/comparison/config_comparison_v4.toml
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from pathlib import Path
from time import perf_counter

# Ensure project root is on sys.path so temoa imports work
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pyomo.environ import Constraint, Var, value  # noqa: E402

from temoa._internal.run_actions import (  # noqa: E402
    build_instance,
    handle_results,
    solve_instance,
)
from temoa.core.config import TemoaConfig  # noqa: E402
from temoa.data_io.hybrid_loader import HybridLoader  # noqa: E402


def count_components(instance):
    """Count variables and constraints in a built Pyomo instance."""
    v_count = sum(len(v) for v in instance.component_objects(ctype=Var))
    c_count = sum(len(c) for c in instance.component_objects(ctype=Constraint))
    return v_count, c_count


def extract_results_from_db(db_path: Path, scenario: str) -> dict:
    """Extract objective, capacity, and flow data from v4 output tables."""
    conn = sqlite3.connect(db_path)
    results = {}

    # Objective
    cur = conn.execute(
        'SELECT total_system_cost FROM output_objective WHERE scenario = ?',
        (scenario,),
    )
    row = cur.fetchone()
    results['objective'] = row[0] if row else None

    # Capacity by tech and period
    cur = conn.execute(
        """
        SELECT period, tech, SUM(capacity) as total_cap
        FROM output_net_capacity
        WHERE scenario = ?
        GROUP BY period, tech
        ORDER BY period, tech
    """,
        (scenario,),
    )
    capacity = {}
    for period, tech, cap in cur.fetchall():
        capacity[f'{tech}_{period}'] = round(cap, 4)
    results['capacity'] = capacity

    # Flow out by tech and period (aggregated over season/tod/vintage)
    cur = conn.execute(
        """
        SELECT period, tech, SUM(flow) as total_flow
        FROM output_flow_out
        WHERE scenario = ?
        GROUP BY period, tech
        ORDER BY period, tech
    """,
        (scenario,),
    )
    flows = {}
    for period, tech, flow in cur.fetchall():
        flows[f'{tech}_{period}'] = round(flow, 4)
    results['flow_out'] = flows

    conn.close()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description='Build/solve a v4 Temoa model and capture metrics')
    parser.add_argument(
        '--config',
        type=Path,
        required=True,
        help='Path to v4 TOML config file',
    )
    parser.add_argument(
        '--build-only',
        action='store_true',
        help='Build only (skip solve). Fast iteration mode.',
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help='Output JSON file (default: v4_metrics.json next to config)',
    )
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s %(message)s',
        datefmt='%H:%M:%S',
    )
    log = logging.getLogger(__name__)

    config_path = args.config.resolve()
    output_json = args.output or config_path.parent / 'v4_metrics.json'

    # Output path for LP files and logs
    output_dir = config_path.parent / 'v4_output'
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics: dict = {
        'branch': 'v4/unstable (db-migration/mip-dev)',
        'config': str(config_path),
        'mode': 'build-only' if args.build_only else 'full',
        'timing': {},
        'model_size': {},
    }

    # =========================================================================
    # Step 1: Load config
    # =========================================================================
    log.info('Loading config: %s', config_path)
    t0 = perf_counter()
    config = TemoaConfig.build_config(config_path, output_path=output_dir, silent=True)
    metrics['timing']['config_load'] = round(perf_counter() - t0, 3)
    metrics['scenario'] = config.scenario

    # =========================================================================
    # Step 2: Load data
    # =========================================================================
    log.info('Loading data from: %s', config.input_database)
    t0 = perf_counter()
    conn = sqlite3.connect(config.input_database)
    loader = HybridLoader(conn, config)
    portal = loader.load_data_portal()
    conn.close()
    data_load_time = perf_counter() - t0
    metrics['timing']['data_load'] = round(data_load_time, 3)
    log.info('Data loaded in %.2fs', data_load_time)

    # =========================================================================
    # Step 3: Build instance
    # =========================================================================
    log.info('Building model instance...')
    t0 = perf_counter()
    instance = build_instance(
        portal,
        model_name=config.scenario,
        silent=False,
        keep_lp_file=config.save_lp_file,
        lp_path=output_dir if config.save_lp_file else None,
    )
    build_time = perf_counter() - t0
    metrics['timing']['build'] = round(build_time, 3)
    log.info('Model built in %.2fs', build_time)

    # Capture model size
    v_count, c_count = count_components(instance)
    metrics['model_size']['variables'] = v_count
    metrics['model_size']['constraints'] = c_count
    log.info('Variables: %d, Constraints: %d', v_count, c_count)

    # LP file path
    lp_path = output_dir / 'model.lp'
    if lp_path.exists():
        metrics['lp_file'] = str(lp_path)
        metrics['lp_size_mb'] = round(lp_path.stat().st_size / (1024 * 1024), 2)
        log.info('LP file: %s (%.1f MB)', lp_path, metrics['lp_size_mb'])

    if args.build_only:
        metrics['timing']['total'] = round(
            metrics['timing']['config_load']
            + metrics['timing']['data_load']
            + metrics['timing']['build'],
            3,
        )
        log.info('Build-only mode complete. Total time: %.2fs', metrics['timing']['total'])
    else:
        # =================================================================
        # Step 4: Solve
        # =================================================================
        log.info('Solving with %s...', config.solver_name)
        t0 = perf_counter()
        instance, results = solve_instance(instance, config.solver_name, silent=False)
        solve_time = perf_counter() - t0
        metrics['timing']['solve'] = round(solve_time, 3)
        log.info('Solved in %.2fs', solve_time)

        # Check solve status
        from pyomo.environ import check_optimal_termination

        if check_optimal_termination(results):
            log.info('Solver found optimal solution')
            metrics['solve_status'] = 'optimal'
        else:
            log.warning('Solver did NOT find optimal solution')
            metrics['solve_status'] = 'non-optimal'

        # Objective value
        if hasattr(instance, 'total_cost'):
            obj_val = value(instance.total_cost)
            metrics['objective'] = round(obj_val, 4)
            log.info('Objective (total_cost): %.4f', obj_val)

        # =================================================================
        # Step 5: Write results to DB
        # =================================================================
        log.info('Writing results to output DB...')
        t0 = perf_counter()
        handle_results(instance, results, config)
        results_time = perf_counter() - t0
        metrics['timing']['write_results'] = round(results_time, 3)

        # =================================================================
        # Step 6: Extract results from DB
        # =================================================================
        log.info('Extracting results from output DB...')
        db_results = extract_results_from_db(config.output_database, config.scenario)
        metrics['results'] = db_results

        metrics['timing']['total'] = round(
            metrics['timing']['config_load']
            + metrics['timing']['data_load']
            + metrics['timing']['build']
            + metrics['timing']['solve']
            + metrics['timing']['write_results'],
            3,
        )
        log.info('Full run complete. Total time: %.2fs', metrics['timing']['total'])

    # =========================================================================
    # Write metrics JSON
    # =========================================================================
    with open(output_json, 'w') as f:
        json.dump(metrics, f, indent=2)
    log.info('Metrics written to: %s', output_json)


if __name__ == '__main__':
    main()
