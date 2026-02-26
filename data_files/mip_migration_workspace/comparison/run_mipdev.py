#!/usr/bin/env python3
"""
Standalone mip-dev model runner for Python 3.12+.

Patches the deprecated `imp` module before importing mip-dev code, then
runs the standard mip-dev build+solve pipeline. Captures metrics to JSON.

Must be run from the project root while on the mip-dev branch.

Usage:
  python data_files/mip_migration_workspace/comparison/run_mipdev.py \
    --config data_files/mip_migration_workspace/comparison/config_comparison_mipdev

  python data_files/mip_migration_workspace/comparison/run_mipdev.py \
    --config data_files/mip_migration_workspace/comparison/config_comparison_mipdev \
    --build-only
"""

from __future__ import annotations

# =========================================================================
# STEP 0: Patch `imp` module for Python 3.12+ (removed in 3.12)
# pyutilib requires imp.find_module and imp.load_source
# =========================================================================
import importlib
import importlib.machinery
import importlib.util
import sys
import types

if 'imp' not in sys.modules:
    imp_shim = types.ModuleType('imp')

    # Constants that pyutilib checks
    imp_shim.PY_SOURCE = 1
    imp_shim.PY_COMPILED = 2
    imp_shim.C_EXTENSION = 3
    imp_shim.PKG_DIRECTORY = 5
    imp_shim.C_BUILTIN = 6
    imp_shim.PY_FROZEN = 7

    def _find_module(name, path=None):
        """Shim for imp.find_module using importlib."""
        spec = importlib.util.find_spec(name, path)
        if spec is None:
            raise ImportError(f'No module named {name!r}')
        origin = spec.origin or ''
        fp = open(origin) if origin.endswith('.py') else None
        if origin.endswith('.py'):
            description = ('.py', 'r', imp_shim.PY_SOURCE)
        elif origin.endswith('.pyc'):
            description = ('.pyc', 'rb', imp_shim.PY_COMPILED)
        else:
            description = ('', '', imp_shim.PKG_DIRECTORY)
        return fp, origin, description

    def _load_source(name, pathname, file=None):
        """Shim for imp.load_source using importlib."""
        loader = importlib.machinery.SourceFileLoader(name, pathname)
        spec = importlib.util.spec_from_file_location(name, pathname, loader=loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    imp_shim.find_module = _find_module
    imp_shim.load_source = _load_source
    sys.modules['imp'] = imp_shim

# =========================================================================
# Now safe to import everything else
# =========================================================================
import argparse
import json
import logging
import os
import sqlite3
from pathlib import Path
from time import perf_counter

# Add temoa_model/ to path so mip-dev imports work
PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEMOA_MODEL = PROJECT_ROOT / 'temoa_model'
if str(TEMOA_MODEL) not in sys.path:
    sys.path.insert(0, str(TEMOA_MODEL))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.chdir(PROJECT_ROOT)

from pyomo.environ import (  # noqa: E402
    Constraint,
    DataPortal,
    Suffix,
    Var,
    check_optimal_termination,
    value,
)
from pyomo.opt import SolverFactory  # noqa: E402


def count_components(instance):
    v_count = sum(len(v) for v in instance.component_objects(ctype=Var))
    c_count = sum(len(c) for c in instance.component_objects(ctype=Constraint))
    return v_count, c_count


def write_results_directly(instance, db_path: Path, scenario: str, log) -> None:
    """Write results from Pyomo instance directly to mip-dev output tables.

    Bypasses pformat_results entirely. Extracts V_FlowOut, V_Capacity, and
    TotalCost from the solved instance.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Clean out old results for this scenario
    for tbl in (
        'Output_VFlow_Out',
        'Output_V_Capacity',
        'Output_Objective',
        'Output_VFlow_Out_Annual',
    ):
        try:
            cur.execute(f'DELETE FROM {tbl} WHERE scenario = ?', (scenario,))
        except sqlite3.OperationalError:
            pass  # table may not exist

    # Build sector lookup: tech -> sector
    tech_sectors = {}
    try:
        rows = cur.execute('SELECT tech, sector FROM technologies').fetchall()
        tech_sectors = {r[0]: r[1] for r in rows}
    except sqlite3.OperationalError:
        pass

    epsilon = 1e-6

    # ----- V_FlowOut: (r, p, s, d, i, t, v, o) -----
    flow_count = 0
    if hasattr(instance, 'V_FlowOut'):
        for idx in instance.V_FlowOut:
            val = value(instance.V_FlowOut[idx])
            if abs(val) < epsilon:
                continue
            r, p, s, d, i, t, v, o = idx
            sector = tech_sectors.get(t, '')
            cur.execute(
                'INSERT OR REPLACE INTO Output_VFlow_Out '
                '(regions, scenario, sector, t_periods, t_season, t_day, '
                'input_comm, tech, vintage, output_comm, vflow_out) '
                'VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                (r, scenario, sector, p, s, d, i, t, v, o, val),
            )
            flow_count += 1
    log.info('Wrote %d rows to Output_VFlow_Out', flow_count)

    # ----- V_FlowOutAnnual: (r, p, i, t, v, o) -----
    annual_count = 0
    if hasattr(instance, 'V_FlowOutAnnual'):
        try:
            cur.execute(
                'CREATE TABLE IF NOT EXISTS Output_VFlow_Out_Annual '
                '(regions text, scenario text, sector text, t_periods integer, '
                'input_comm text, tech text, vintage integer, output_comm text, '
                'vflow_out_annual real, '
                'PRIMARY KEY(regions, scenario, t_periods, input_comm, tech, vintage, output_comm))'
            )
        except sqlite3.OperationalError:
            pass
        for idx in instance.V_FlowOutAnnual:
            val = value(instance.V_FlowOutAnnual[idx])
            if abs(val) < epsilon:
                continue
            r, p, i, t, v, o = idx
            sector = tech_sectors.get(t, '')
            cur.execute(
                'INSERT OR REPLACE INTO Output_VFlow_Out_Annual '
                '(regions, scenario, sector, t_periods, '
                'input_comm, tech, vintage, output_comm, vflow_out_annual) '
                'VALUES (?,?,?,?,?,?,?,?,?)',
                (r, scenario, sector, p, i, t, v, o, val),
            )
            annual_count += 1
    log.info('Wrote %d rows to Output_VFlow_Out_Annual', annual_count)

    # ----- V_Capacity: (r, p, t, v) -----
    cap_count = 0
    if hasattr(instance, 'V_Capacity'):
        for idx in instance.V_Capacity:
            val = value(instance.V_Capacity[idx])
            if abs(val) < epsilon:
                continue
            r, p, t, v = idx
            sector = tech_sectors.get(t, '')
            cur.execute(
                'INSERT OR REPLACE INTO Output_V_Capacity '
                '(regions, scenario, sector, t_periods, tech, vintage, capacity) '
                'VALUES (?,?,?,?,?,?,?)',
                (r, scenario, sector, p, t, v, val),
            )
            cap_count += 1
    log.info('Wrote %d rows to Output_V_Capacity', cap_count)

    # ----- Objective -----
    if hasattr(instance, 'TotalCost'):
        obj_val = value(instance.TotalCost)
        cur.execute(
            'INSERT OR REPLACE INTO Output_Objective '
            '(scenario, objective_name, total_system_cost) VALUES (?,?,?)',
            (scenario, 'TotalCost', obj_val),
        )
        log.info('Wrote objective: %.4f', obj_val)

    conn.commit()
    conn.close()


def extract_results_from_db(db_path: Path, scenario: str) -> dict:
    """Extract results from mip-dev v3.1 output tables."""
    conn = sqlite3.connect(db_path)
    results = {}

    cur = conn.execute(
        'SELECT total_system_cost FROM Output_Objective WHERE scenario = ?',
        (scenario,),
    )
    row = cur.fetchone()
    results['objective'] = row[0] if row else None

    # Capacity by tech/period (strip region prefixes)
    regions = []
    try:
        cur = conn.execute('SELECT regions FROM regions ORDER BY LENGTH(regions) DESC')
        regions = [r[0] for r in cur.fetchall()]
    except sqlite3.OperationalError:
        pass

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
        stripped = strip_prefix(tech, regions)
        key = f'{stripped}_{period}'
        capacity[key] = round(capacity.get(key, 0) + cap, 4)
    results['capacity'] = capacity

    cur = conn.execute(
        """
        SELECT t_periods, tech, SUM(vflow_out) as total_flow
        FROM Output_VFlow_Out
        WHERE scenario = ?
        GROUP BY t_periods, tech
        ORDER BY t_periods, tech
    """,
        (scenario,),
    )
    flows = {}
    for period, tech, flow in cur.fetchall():
        stripped = strip_prefix(tech, regions)
        key = f'{stripped}_{period}'
        flows[key] = round(flows.get(key, 0) + flow, 4)
    results['flow_out'] = flows

    conn.close()
    return results


def strip_prefix(tech: str, regions: list[str]) -> str:
    for r in regions:
        if tech.startswith(r + '_'):
            return tech[len(r) + 1 :]
    for r in regions:
        pat = '_' + r + '_'
        if pat in tech:
            return tech.replace(pat, '_', 1)
    return tech


def main() -> None:
    parser = argparse.ArgumentParser(description='Run mip-dev model and capture metrics')
    parser.add_argument('--config', type=Path, required=True, help='mip-dev config file')
    parser.add_argument('--build-only', action='store_true', help='Build only, skip solve')
    parser.add_argument(
        '--output', type=Path, default=None, help='Output JSON (default: mipdev_metrics.json)'
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s %(message)s',
        datefmt='%H:%M:%S',
    )
    log = logging.getLogger(__name__)

    config_path = args.config.resolve()
    output_json = args.output or config_path.parent / 'mipdev_metrics.json'
    output_dir = config_path.parent / 'mipdev_output'
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics: dict = {
        'branch': 'mip-dev',
        'config': str(config_path),
        'mode': 'build-only' if args.build_only else 'full',
        'timing': {},
        'model_size': {},
    }

    # =========================================================================
    # Step 1: Parse config manually (avoid PLY lexer complexity)
    # =========================================================================
    log.info('Parsing config: %s', config_path)
    cfg = {}
    with open(config_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, val = line.split('=', 1)
                key = key.lstrip('-').strip()
                val = val.strip()
                cfg[key] = val
            elif line.startswith('--'):
                cfg[line.lstrip('-').strip()] = True

    input_db = Path(cfg['input'])
    output_db = Path(cfg.get('output', cfg['input']))
    scenario = cfg.get('scenario', 'default')
    solver_name = cfg.get('solver', 'gurobi')
    keep_lp = 'keep_pyomo_lp_file' in cfg

    metrics['scenario'] = scenario
    log.info('Input: %s', input_db)
    log.info('Scenario: %s', scenario)

    if not input_db.exists():
        log.error('Input DB not found: %s', input_db)
        sys.exit(1)

    # =========================================================================
    # Step 2: Convert SQLite to .dat (mip-dev uses db_2_dat)
    # =========================================================================
    log.info('Converting SQLite to .dat format...')
    t0 = perf_counter()

    # Import the db_2_dat converter and TemoaConfig

    # We need to build a minimal config for db_2_dat
    # The db_2_dat function needs: scenario, myopic (dict with keys)
    class MinimalConfig:
        def __init__(self, scenario_name):
            self.scenario = scenario_name
            self.myopic = {'myopic': False}
            self.mga_weight = None

    mini_cfg = MinimalConfig(scenario)

    # Import db_2_dat from temoa_config (it's defined there in mip-dev)
    from temoa_config import db_2_dat  # noqa: E402

    dat_file = str(input_db).replace('.sqlite', '.dat')
    # Suppress db_2_dat stdout
    old_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')
    try:
        db_2_dat(str(input_db), dat_file, mini_cfg)
    finally:
        sys.stdout.close()
        sys.stdout = old_stdout

    dat_time = perf_counter() - t0
    metrics['timing']['db_to_dat'] = round(dat_time, 3)
    log.info('SQLite -> .dat conversion: %.2fs', dat_time)

    # =========================================================================
    # Step 3: Load data via DataPortal
    # =========================================================================
    log.info('Loading model and data...')
    t0 = perf_counter()

    # Mock modules that mip-dev imports but we don't need for build+solve
    # The import chain: temoa_model -> temoa_run -> pformat_results -> DB_to_Excel -> pyam
    for mock_name in ['pyam', 'DB_to_Excel']:
        if mock_name not in sys.modules:
            mock_mod = types.ModuleType(mock_name)
            mock_mod.make_excel = lambda *a, **kw: None  # type: ignore[attr-defined]
            mock_mod.IamDataFrame = None  # type: ignore[attr-defined]
            sys.modules[mock_name] = mock_mod

    # Import the mip-dev model
    from temoa_model import model  # noqa: E402

    modeldata = DataPortal(model=model)
    modeldata.load(filename=dat_file)

    data_load_time = perf_counter() - t0
    metrics['timing']['data_load'] = round(data_load_time, 3)
    log.info('Data loaded in %.2fs', data_load_time)

    # =========================================================================
    # Step 4: Build instance
    # =========================================================================
    log.info('Building model instance...')
    t0 = perf_counter()

    model.dual = Suffix(direction=Suffix.IMPORT)
    instance = model.create_instance(modeldata)

    build_time = perf_counter() - t0
    metrics['timing']['build'] = round(build_time, 3)
    log.info('Model built in %.2fs', build_time)

    v_count, c_count = count_components(instance)
    metrics['model_size']['variables'] = v_count
    metrics['model_size']['constraints'] = c_count
    log.info('Variables: %d, Constraints: %d', v_count, c_count)

    # Save LP if requested
    if keep_lp:
        lp_file = output_dir / f'{scenario}.lp'
        log.info('Writing LP file...')
        instance.write(str(lp_file), format='lp', io_options={'symbolic_solver_labels': True})
        metrics['lp_file'] = str(lp_file)
        metrics['lp_size_mb'] = round(lp_file.stat().st_size / (1024 * 1024), 2)
        log.info('LP file: %s (%.1f MB)', lp_file, metrics['lp_size_mb'])

    if args.build_only:
        metrics['timing']['total'] = round(
            metrics['timing'].get('db_to_dat', 0)
            + metrics['timing']['data_load']
            + metrics['timing']['build'],
            3,
        )
        log.info('Build-only complete. Total: %.2fs', metrics['timing']['total'])
    else:
        # =================================================================
        # Step 5: Solve
        # =================================================================
        log.info('Solving with %s...', solver_name)
        optimizer = SolverFactory(solver_name)

        if solver_name == 'gurobi':
            optimizer.options['Method'] = 2
            optimizer.options['Crossover'] = 0
            optimizer.options['BarConvTol'] = 1.0e-3
            optimizer.options['FeasibilityTol'] = 1.0e-4

        t0 = perf_counter()
        if keep_lp:
            lp_for_solver = str(output_dir / scenario)
            result = optimizer.solve(
                instance, keepfiles=True, options_string=f'ResultFile={lp_for_solver}.sol'
            )
        else:
            result = optimizer.solve(instance)
        solve_time = perf_counter() - t0
        metrics['timing']['solve'] = round(solve_time, 3)
        log.info('Solved in %.2fs', solve_time)

        if check_optimal_termination(result):
            metrics['solve_status'] = 'optimal'
            log.info('Solver found optimal solution')
        else:
            metrics['solve_status'] = 'non-optimal'
            log.warning('Non-optimal termination')

        # Objective
        if hasattr(instance, 'TotalCost'):
            obj_val = value(instance.TotalCost)
            metrics['objective'] = round(obj_val, 4)
            log.info('Objective (TotalCost): %.4f', obj_val)

        # =================================================================
        # Step 6: Write results to output DB directly from instance
        # =================================================================
        log.info('Writing results to output DB...')
        t0 = perf_counter()
        write_results_directly(instance, output_db, scenario, log)

        write_time = perf_counter() - t0
        metrics['timing']['write_results'] = round(write_time, 3)

        # =================================================================
        # Step 7: Extract results from output DB
        # =================================================================
        log.info('Extracting results from output DB...')
        db_results = extract_results_from_db(output_db, scenario)
        metrics['results'] = db_results

        metrics['timing']['total'] = round(
            metrics['timing'].get('db_to_dat', 0)
            + metrics['timing']['data_load']
            + metrics['timing']['build']
            + metrics['timing']['solve']
            + metrics['timing'].get('write_results', 0),
            3,
        )
        log.info('Full run complete. Total: %.2fs', metrics['timing']['total'])

    # =========================================================================
    # Write metrics
    # =========================================================================
    with open(output_json, 'w') as f:
        json.dump(metrics, f, indent=2)
    log.info('Metrics written to: %s', output_json)

    # Cleanup .dat file
    dat_path = Path(dat_file)
    if dat_path.exists():
        dat_path.unlink()
        log.info('Cleaned up temp .dat file')


if __name__ == '__main__':
    main()
