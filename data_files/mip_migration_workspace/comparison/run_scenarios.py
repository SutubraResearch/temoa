#!/usr/bin/env python3
"""
Scenario Comparison Test Suite: v4 vs mip-dev

Prepares 5 policy scenario DBs (x2 versions), generates configs, and compares results.
DB preparation is pure SQLite — no branch dependency.

Usage:
    python run_scenarios.py prepare   # Create all 10 scenario DBs + configs
    python run_scenarios.py compare   # Extract results and produce comparison table
    python run_scenarios.py compare --scenario s3_emission  # Compare one scenario
"""

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import textwrap
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / 'data_files'
SCENARIO_DB_DIR = SCRIPT_DIR / 'scenario_dbs'
SCENARIO_CFG_DIR = SCRIPT_DIR / 'scenario_configs'

# Relative paths from repo root (for config files)
# SCRIPT_DIR is .../temoa-SRfork/data_files/mip_migration_workspace/comparison
REPO_ROOT = SCRIPT_DIR.parents[2]  # .../temoa-SRfork

BASE_V4_DB = DATA_DIR / 'jan_TRE_TREW_4week_v4_stripped.sqlite'
# IMPORTANT: Use the top-level corrected DB (C2A=672, scaled demands), NOT the
# workspace copy which may have stale C2A=8760 and full-year demands.
BASE_V3_DB = REPO_ROOT / 'data_files' / 'jan_TRE_TREW_4week.sqlite'

# ---------------------------------------------------------------------------
# Tech classification
# ---------------------------------------------------------------------------
RENEWABLE_PATTERNS = [
    'landbasedwind',
    'offshorewind',
    'onshore_wind',
    'utilitypv',
    'solar_photovoltaic',
    'biomass',
    'conventional_hydroelectric',
    'small_hydroelectric',
]

EXCLUDE_FROM_GEN = [
    'batter',
    'transmission',
    'elec_distribution',
    'import_',
    'water_import',
    'unserved_load',
]

TECH_CATEGORIES = {
    'wind': ['landbasedwind', 'offshorewind', 'onshore_wind'],
    'solar': ['utilitypv', 'solar_photovoltaic'],
    'gas': ['natural_gas', 'naturalgas'],
    'coal': ['conventional_steam_coal'],
    'nuclear': ['nuclear'],
    'hydro': ['conventional_hydroelectric', 'small_hydroelectric'],
    'biomass': ['biomass'],
    'distributed_gen': ['distributed_generation'],
    'hydrogen': ['hydrogen'],
    'petroleum': ['petroleum'],
}


def classify_tech(tech_name):
    """Classify a tech name (v4 stripped or v3 with region prefix stripped) into a category."""
    t = tech_name.lower()
    for cat, patterns in TECH_CATEGORIES.items():
        for pat in patterns:
            if pat in t:
                return cat
    return 'other'


def is_renewable(tech_name):
    t = tech_name.lower()
    return any(pat in t for pat in RENEWABLE_PATTERNS)


def is_excluded_from_gen(tech_name):
    t = tech_name.lower()
    return any(pat in t for pat in EXCLUDE_FROM_GEN)


def strip_region_prefix(tech_name):
    """Remove TRE_ or TREW_ prefix from a v3 tech name."""
    for prefix in ('TREW_', 'TRE_'):
        if tech_name.startswith(prefix):
            return tech_name[len(prefix) :]
    return tech_name


# ---------------------------------------------------------------------------
# v4 output table names
# ---------------------------------------------------------------------------
V4_OUTPUT_TABLES = [
    'output_built_capacity',
    'output_cost',
    'output_emission',
    'output_flow_in',
    'output_flow_out',
    'output_flow_out_summary',
    'output_net_capacity',
    'output_objective',
    'output_storage_level',
]

# v3 output table names
V3_OUTPUT_TABLES = [
    'Output_V_Capacity',
    'Output_VFlow_Out',
    'Output_VFlow_Out_Annual',
    'Output_Objective',
    'Output_Costs',
    'Output_Emissions',
    'Output_CapacityByPeriodAndTech',
]


def clear_output_tables(db_path, version):
    """Clear all output tables so scenario solves start clean."""
    tables = V4_OUTPUT_TABLES if version == 'v4' else V3_OUTPUT_TABLES
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for table in tables:
        try:
            cur.execute(f'DELETE FROM "{table}"')
        except sqlite3.OperationalError:
            pass  # table may not exist
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------


def get_elec_gen_techs_v4(db_path):
    """Get all electricity-generating techs from v4 DB, excluding batteries/transmission/etc."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT tech FROM efficiency WHERE output_comm = 'electricity'")
    all_techs = [row[0] for row in cur.fetchall()]
    conn.close()
    return [t for t in all_techs if not is_excluded_from_gen(t)]


def get_elec_gen_techs_v3(db_path):
    """Get all electricity-generating techs from v3 DB (region-prefixed), excluding exclusions."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # v3 electricity commodity names vary; check what's there
    cur.execute("SELECT DISTINCT output_comm FROM Efficiency WHERE output_comm LIKE '%ELC%'")
    elc_comms = [row[0] for row in cur.fetchall()]
    if not elc_comms:
        # Try 'electricity'
        cur.execute("SELECT DISTINCT output_comm FROM Efficiency WHERE output_comm = 'electricity'")
        elc_comms = [row[0] for row in cur.fetchall()]
    # Also check lowercase
    cur.execute(
        'SELECT DISTINCT output_comm FROM Efficiency '
        "WHERE output_comm IN ('electricity', 'DEMAND_ELC', 'ELC', 'ELC_s')"
    )
    elc_comms_extra = [row[0] for row in cur.fetchall()]
    elc_comms = list(set(elc_comms + elc_comms_extra))

    if not elc_comms:
        print(f'  WARNING: No electricity commodity found in {db_path}')
        conn.close()
        return []

    placeholders = ','.join('?' * len(elc_comms))
    cur.execute(
        f'SELECT DISTINCT regions, tech FROM Efficiency WHERE output_comm IN ({placeholders})',
        elc_comms,
    )
    rows = cur.fetchall()
    conn.close()

    result = []
    for region, tech in rows:
        if not is_excluded_from_gen(tech):
            result.append((region, tech))
    return result


def get_offshore_wind_techs_v4(db_path):
    """Get all offshore wind tech names from v4 DB."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT tech FROM efficiency WHERE tech LIKE 'offshorewind%'")
    techs = [row[0] for row in cur.fetchall()]
    conn.close()
    return techs


def get_offshore_wind_techs_v3(db_path):
    """Get all offshore wind tech names from v3 DB (region-prefixed)."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT regions, tech FROM Efficiency WHERE tech LIKE '%offshorewind%'")
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# Scenario preparation functions
# ---------------------------------------------------------------------------


def prepare_s1_discount(v4_db, v3_db):
    """S1: Lower discount rates 7.5% → 2%."""
    print('  S1: Updating discount rates to 2%...')

    # v4: loan_rate table
    conn = sqlite3.connect(v4_db)
    conn.execute('UPDATE loan_rate SET rate = 0.02')
    conn.commit()
    conn.close()

    # v3: DiscountRate table
    conn = sqlite3.connect(v3_db)
    conn.execute('UPDATE DiscountRate SET tech_rate = 0.02')
    conn.commit()
    conn.close()


def prepare_s2_demand(v4_db, v3_db):
    """S2: Raise electricity demands +20%."""
    print('  S2: Raising demand by 20%...')

    # v4
    conn = sqlite3.connect(v4_db)
    conn.execute('UPDATE demand SET demand = demand * 1.2')
    conn.commit()
    conn.close()

    # v3
    conn = sqlite3.connect(v3_db)
    conn.execute('UPDATE Demand SET demand = demand * 1.2')
    conn.commit()
    conn.close()


def fix_hydrogen_capex(v4_db, v3_db):
    """Set hydrogen capex = gas capex (source DB used highGasCapex scenario).

    The base DB was built from a highGasCapex scenario that inflated gas capital costs
    above hydrogen. This made hydrogen CTs ~$350k/MW cheaper than gas CTs, causing the
    optimizer to build massive hydrogen peaker capacity purely for the capex advantage.
    Fix: set hydrogen CT/CC capex equal to the corresponding gas CT/CC capex.
    """
    # v4: cost_invest table
    conn = sqlite3.connect(v4_db)
    conn.execute("""
        UPDATE cost_invest SET cost = (
            SELECT g.cost FROM cost_invest g
            WHERE g.tech = 'naturalgas_fframe_ct_moderate_0'
            AND g.vintage = cost_invest.vintage AND g.region = cost_invest.region
        ) WHERE tech = 'hydrogen_fframe_ct_moderate_0'
    """)
    conn.execute("""
        UPDATE cost_invest SET cost = (
            SELECT g.cost FROM cost_invest g
            WHERE g.tech = 'naturalgas_hframe_cc_moderate_0'
            AND g.vintage = cost_invest.vintage AND g.region = cost_invest.region
        ) WHERE tech = 'hydrogen_hframe_cc_moderate_0'
    """)
    conn.commit()
    conn.close()

    # v3: CostInvest table (different column/table names)
    conn = sqlite3.connect(v3_db)
    conn.execute("""
        UPDATE CostInvest SET cost_invest = (
            SELECT g.cost_invest FROM CostInvest g
            WHERE g.tech = replace(CostInvest.tech, 'hydrogen_fframe_ct', 'naturalgas_fframe_ct')
            AND g.vintage = CostInvest.vintage AND g.regions = CostInvest.regions
        ) WHERE tech LIKE '%hydrogen_fframe_ct%'
    """)
    conn.execute("""
        UPDATE CostInvest SET cost_invest = (
            SELECT g.cost_invest FROM CostInvest g
            WHERE g.tech = replace(CostInvest.tech, 'hydrogen_hframe_cc', 'naturalgas_hframe_cc')
            AND g.vintage = CostInvest.vintage AND g.regions = CostInvest.regions
        ) WHERE tech LIKE '%hydrogen_hframe_cc%'
    """)
    conn.commit()
    conn.close()


def prepare_s6_greenfield(v4_db, v3_db):
    """S6: Raise electricity demands 10x (greenfield-like scenario).

    Also scales elec_distribution and fuel import existing capacities to match,
    since these are fixed-capacity passthrough techs with no investment option.
    """
    MULT = 10
    print(f'  S6: Raising demand by {MULT}x (greenfield)...')

    # v4
    conn = sqlite3.connect(v4_db)
    conn.execute(f'UPDATE demand SET demand = demand * {MULT}')
    conn.execute(
        f'UPDATE existing_capacity SET capacity = capacity * {MULT} '
        f"WHERE tech IN ('elec_distribution', "
        f"'import_west_south_central_reference_distillate', "
        f"'import_west_south_central_reference_coal', "
        f"'import_west_south_central_reference_naturalgas', "
        f"'import_west_south_central_reference_naturalgas_ccs95', "
        f"'import_hydrogen', 'import_waste_biomass')"
    )
    conn.commit()
    conn.close()

    # v3
    conn = sqlite3.connect(v3_db)
    conn.execute(f'UPDATE Demand SET demand = demand * {MULT}')
    conn.execute(
        f'UPDATE ExistingCapacity SET exist_cap = exist_cap * {MULT} '
        f"WHERE tech IN ('elec_distribution', "
        f"'import_west_south_central_reference_distillate', "
        f"'import_west_south_central_reference_coal', "
        f"'import_west_south_central_reference_naturalgas', "
        f"'import_west_south_central_reference_naturalgas_ccs95', "
        f"'import_hydrogen', 'import_waste_biomass')"
    )
    conn.commit()
    conn.close()


def prepare_s3_emission(v4_db, v3_db):
    """S3: Emission limit at 50% of baseline CO2."""
    print('  S3: Adding emission limits (50% of baseline)...')

    # Baseline emissions (from solved v4 output):
    # TRE 2027: 9,405,269 | TRE 2030: 16,495,782
    # TREW 2027: 797,370 | TREW 2030: 849,847
    # Combined: 2027: 10,202,639 | 2030: 17,345,629
    limit_2027 = 10_202_639 * 0.5  # 5,101,320
    limit_2030 = 17_345_629 * 0.5  # 8,672,815

    # v4: limit_emission table
    conn = sqlite3.connect(v4_db)
    conn.execute(
        'INSERT INTO limit_emission (region, period, emis_comm, operator, value, units, notes) '
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        ('TRE+TREW', 2027, 'CO2', 'le', limit_2027, 'tonnes', '50% of baseline'),
    )
    conn.execute(
        'INSERT INTO limit_emission (region, period, emis_comm, operator, value, units, notes) '
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        ('TRE+TREW', 2030, 'CO2', 'le', limit_2030, 'tonnes', '50% of baseline'),
    )
    conn.commit()
    conn.close()

    # v3: EmissionLimit table
    conn = sqlite3.connect(v3_db)
    # Ensure TRE+TREW exists in region_combinations (required by RegionalGlobalIndices)
    conn.execute(
        'INSERT OR IGNORE INTO region_combinations (regions, region_note) VALUES (?, ?)',
        ('TRE+TREW', 'Combined TRE and TREW'),
    )
    conn.execute(
        'INSERT INTO EmissionLimit '
        '(regions, periods, emis_comm, emis_limit, emis_limit_units, emis_limit_notes) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        ('TRE+TREW', 2027, 'CO2', limit_2027, 'tonnes', '50% of baseline'),
    )
    conn.execute(
        'INSERT INTO EmissionLimit '
        '(regions, periods, emis_comm, emis_limit, emis_limit_units, emis_limit_notes) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        ('TRE+TREW', 2030, 'CO2', limit_2030, 'tonnes', '50% of baseline'),
    )
    conn.commit()
    conn.close()


def prepare_s4_rps(v4_db, v3_db):
    """S4: Renewable Portfolio Standard (50% in 2027, 80% in 2030)."""
    print('  S4: Adding RPS constraints...')

    # --- v4 ---
    gen_techs_v4 = get_elec_gen_techs_v4(v4_db)
    renewable_techs_v4 = [t for t in gen_techs_v4 if is_renewable(t)]

    conn = sqlite3.connect(v4_db)
    cur = conn.cursor()

    # Create tech groups
    cur.execute(
        'INSERT INTO tech_group (group_name, notes) VALUES (?, ?)',
        ('RENEWABLES', 'Wind+Solar+Hydro+Biomass'),
    )
    cur.execute(
        'INSERT INTO tech_group (group_name, notes) VALUES (?, ?)',
        ('ALL_ELEC_GEN', 'All electricity generators'),
    )

    # Populate members
    for tech in renewable_techs_v4:
        cur.execute(
            'INSERT INTO tech_group_member (group_name, tech) VALUES (?, ?)',
            ('RENEWABLES', tech),
        )
    for tech in gen_techs_v4:
        cur.execute(
            'INSERT INTO tech_group_member (group_name, tech) VALUES (?, ?)',
            ('ALL_ELEC_GEN', tech),
        )

    # Activity share constraint
    cur.execute(
        'INSERT INTO limit_activity_share '
        '(region, period, sub_group, super_group, operator, share, notes) '
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        ('TRE+TREW', 2027, 'RENEWABLES', 'ALL_ELEC_GEN', 'ge', 0.50, 'RPS 50%'),
    )
    cur.execute(
        'INSERT INTO limit_activity_share '
        '(region, period, sub_group, super_group, operator, share, notes) '
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        ('TRE+TREW', 2030, 'RENEWABLES', 'ALL_ELEC_GEN', 'ge', 0.80, 'RPS 80%'),
    )

    conn.commit()

    print(f'    v4: {len(renewable_techs_v4)} renewable techs, {len(gen_techs_v4)} total gen techs')
    conn.close()

    # --- v3 ---
    # v3 uses absolute MWh targets (MinActivityGroup)
    # Baseline total gen: 2027 ~39.5M MWh, 2030 ~46.7M MWh
    baseline_total_2027 = 39_536_489.0
    baseline_total_2030 = 46_676_896.0
    target_2027 = baseline_total_2027 * 0.50
    target_2030 = baseline_total_2030 * 0.80

    v3_elec_techs = get_elec_gen_techs_v3(v3_db)
    v3_renewable_techs = [(r, t) for r, t in v3_elec_techs if is_renewable(t)]

    conn = sqlite3.connect(v3_db)
    cur = conn.cursor()

    # Create group
    cur.execute(
        'INSERT INTO groups (group_name, notes) VALUES (?, ?)',
        ('RENEWABLES', 'Wind+Solar+Hydro+Biomass'),
    )

    # Populate tech_groups (region, group_name, tech)
    for region, tech in v3_renewable_techs:
        cur.execute(
            'INSERT INTO tech_groups (region, group_name, tech, notes) VALUES (?, ?, ?, ?)',
            (region, 'RENEWABLES', tech, ''),
        )

    # Create MinGenGroupTarget/Weight tables if they don't exist (needed by db_2_dat)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS "MinGenGroupTarget" (
            "regions" text, "periods" integer, "group_name" text,
            "min_act_g" real, "notes" text,
            PRIMARY KEY("periods","group_name","regions")
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS "MinGenGroupWeight" (
            "regions" text, "tech" text, "group_name" text,
            "act_fraction" REAL, "tech_desc" text,
            PRIMARY KEY("tech","group_name","regions")
        )
    """)

    # Ensure TRE+TREW exists in region_combinations
    cur.execute(
        'INSERT OR IGNORE INTO region_combinations (regions, region_note) VALUES (?, ?)',
        ('TRE+TREW', 'Combined TRE and TREW'),
    )

    # MinActivityGroup constraint
    cur.execute(
        'INSERT INTO MinActivityGroup (regions, periods, group_name, min_act_g, notes) '
        'VALUES (?, ?, ?, ?, ?)',
        ('TRE+TREW', 2027, 'RENEWABLES', target_2027, 'RPS ~50% of total gen'),
    )
    cur.execute(
        'INSERT INTO MinActivityGroup (regions, periods, group_name, min_act_g, notes) '
        'VALUES (?, ?, ?, ?, ?)',
        ('TRE+TREW', 2030, 'RENEWABLES', target_2030, 'RPS ~80% of total gen'),
    )

    conn.commit()

    print(f'    v3: {len(v3_renewable_techs)} renewable techs (region-prefixed)')
    print(f'    v3 targets: 2027={target_2027:,.0f} MWh, 2030={target_2030:,.0f} MWh')
    conn.close()


def prepare_s5_windcap(v4_db, v3_db):
    """S5: Offshore wind minimum capacity (5 GW in 2030)."""
    print('  S5: Adding offshore wind capacity constraint...')

    # --- v4 ---
    offshore_techs_v4 = get_offshore_wind_techs_v4(v4_db)

    conn = sqlite3.connect(v4_db)
    cur = conn.cursor()

    # Create tech group
    cur.execute(
        'INSERT INTO tech_group (group_name, notes) VALUES (?, ?)',
        ('OFFSHORE_WIND', 'Offshore wind techs'),
    )

    for tech in offshore_techs_v4:
        cur.execute(
            'INSERT INTO tech_group_member (group_name, tech) VALUES (?, ?)',
            ('OFFSHORE_WIND', tech),
        )

    # Capacity constraint (TRE only — TREW has no offshore wind)
    cur.execute(
        'INSERT INTO limit_capacity (region, period, tech_or_group, operator, capacity, units, notes) '
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        ('TRE', 2030, 'OFFSHORE_WIND', 'ge', 5000.0, 'MW', 'Min 5 GW offshore wind'),
    )

    conn.commit()
    print(f'    v4: {len(offshore_techs_v4)} offshore wind techs in group')
    conn.close()

    # --- v3 ---
    offshore_techs_v3 = get_offshore_wind_techs_v3(v3_db)

    conn = sqlite3.connect(v3_db)
    cur = conn.cursor()

    # Create group
    cur.execute(
        'INSERT INTO groups (group_name, notes) VALUES (?, ?)',
        ('OFFSHORE_WIND', 'Offshore wind techs'),
    )

    for region, tech in offshore_techs_v3:
        cur.execute(
            'INSERT INTO tech_groups (region, group_name, tech, notes) VALUES (?, ?, ?, ?)',
            (region, 'OFFSHORE_WIND', tech, ''),
        )

    # MinCapacityGroup
    cur.execute(
        'INSERT INTO MinCapacityGroup (regions, periods, group_name, min_cap_g, notes) '
        'VALUES (?, ?, ?, ?, ?)',
        ('TRE', 2030, 'OFFSHORE_WIND', 5000.0, 'Min 5 GW offshore wind'),
    )

    conn.commit()
    print(f'    v3: {len(offshore_techs_v3)} offshore wind techs in group')
    conn.close()


# ---------------------------------------------------------------------------
# Scenario registry
# ---------------------------------------------------------------------------
SCENARIOS = {
    's1_discount': {
        'name': 'Lower Discount Rates (7.5% → 2%)',
        'prepare': prepare_s1_discount,
    },
    's2_demand': {
        'name': 'Raise Electricity Demand +20%',
        'prepare': prepare_s2_demand,
    },
    's3_emission': {
        'name': 'Emission Limit (50% of baseline CO2)',
        'prepare': prepare_s3_emission,
    },
    's4_rps': {
        'name': 'Renewable Portfolio Standard (50%/80%)',
        'prepare': prepare_s4_rps,
    },
    's5_windcap': {
        'name': 'Offshore Wind Min Capacity (5 GW in 2030)',
        'prepare': prepare_s5_windcap,
    },
    's6_greenfield': {
        'name': 'Demand 10x (Greenfield)',
        'prepare': prepare_s6_greenfield,
    },
}


# ---------------------------------------------------------------------------
# Config generation
# ---------------------------------------------------------------------------


def generate_v4_config(scenario_key, db_path):
    """Generate a v4 TOML config file."""
    # Use path relative to repo root
    rel_db = os.path.relpath(db_path, REPO_ROOT)
    content = textwrap.dedent(f"""\
        scenario = "{scenario_key}_v4"
        scenario_mode = "perfect_foresight"
        input_database = "{rel_db}"
        output_database = "{rel_db}"
        solver_name = "gurobi"
        save_lp_file = false
        save_duals = false
        save_excel = false
        neos = false
        time_sequencing = "seasonal_timeslices"
        reserve_margin = "static"
    """)
    cfg_path = SCENARIO_CFG_DIR / f'{scenario_key}_v4.toml'
    cfg_path.write_text(content)
    return cfg_path


def generate_v3_config(scenario_key, db_path):
    """Generate a v3 mip-dev config file."""
    rel_db = os.path.relpath(db_path, REPO_ROOT)
    content = textwrap.dedent(f"""\
        --input={rel_db}
        --output={rel_db}
        --scenario={scenario_key}_mipdev
        --solver=gurobi
        --keep_pyomo_lp_file
    """)
    cfg_path = SCENARIO_CFG_DIR / f'{scenario_key}_v3'
    cfg_path.write_text(content)
    return cfg_path


# ---------------------------------------------------------------------------
# prepare command
# ---------------------------------------------------------------------------


def cmd_prepare(args):
    """Prepare all scenario DBs and configs."""
    print('=' * 70)
    print('Scenario Comparison: Preparing DBs and configs')
    print('=' * 70)

    # Verify baselines exist and are consistent
    for label, path in [('v4 baseline', BASE_V4_DB), ('v3 baseline', BASE_V3_DB)]:
        if not path.exists():
            print(f'ERROR: {label} not found: {path}')
            sys.exit(1)
        print(f'  {label}: {path} ({path.stat().st_size / 1e6:.1f} MB)')

    # CRITICAL: Validate C2A and demand match between v4 and v3 base DBs.
    # The v3 base MUST have C2A=672 for a 4-week subset (not 8760).
    # A mismatch here silently produces garbage results.
    v4_conn = sqlite3.connect(str(BASE_V4_DB))
    v3_conn = sqlite3.connect(str(BASE_V3_DB))
    v4_c2a = v4_conn.execute('SELECT c2a FROM capacity_to_activity LIMIT 1').fetchone()[0]
    v3_c2a = v3_conn.execute('SELECT c2a FROM CapacityToActivity LIMIT 1').fetchone()[0]
    if abs(v4_c2a - v3_c2a) > 0.1:
        print(f'FATAL: C2A mismatch! v4={v4_c2a}, v3={v3_c2a}')
        print('The v3 base DB has wrong C2A. Use the corrected DB with C2A=672.')
        sys.exit(1)
    print(f'  C2A check: v4={v4_c2a}, v3={v3_c2a} ✓')

    v4_demand = v4_conn.execute(
        'SELECT SUM(demand) FROM demand WHERE period = (SELECT MIN(period) FROM demand)'
    ).fetchone()[0]
    v3_demand = v3_conn.execute(
        'SELECT SUM(demand) FROM Demand WHERE periods = (SELECT MIN(periods) FROM Demand)'
    ).fetchone()[0]
    demand_ratio = v4_demand / v3_demand if v3_demand else float('inf')
    if abs(demand_ratio - 1.0) > 0.01:
        print(
            f'FATAL: Demand mismatch! v4={v4_demand:.0f}, v3={v3_demand:.0f} (ratio={demand_ratio:.3f})'
        )
        print('The v3 base DB has wrong demand values.')
        sys.exit(1)
    print(f'  Demand check: v4={v4_demand:.0f}, v3={v3_demand:.0f} (ratio={demand_ratio:.4f}) ✓')
    v4_conn.close()
    v3_conn.close()

    # Create dirs
    SCENARIO_DB_DIR.mkdir(parents=True, exist_ok=True)
    SCENARIO_CFG_DIR.mkdir(parents=True, exist_ok=True)

    # Filter to single scenario if --scenario given
    if getattr(args, 'scenario', None):
        if args.scenario not in SCENARIOS:
            print(f'ERROR: Unknown scenario {args.scenario!r}. Available: {", ".join(SCENARIOS)}')
            sys.exit(1)
        selected = {args.scenario: SCENARIOS[args.scenario]}
    else:
        selected = SCENARIOS

    for key, scenario in selected.items():
        print(f'\n--- {key}: {scenario["name"]} ---')

        # Copy baseline DBs
        v4_db = SCENARIO_DB_DIR / f'{key}_v4.sqlite'
        v3_db = SCENARIO_DB_DIR / f'{key}_v3.sqlite'

        print('  Copying baselines...')
        shutil.copy2(BASE_V4_DB, v4_db)
        shutil.copy2(BASE_V3_DB, v3_db)

        # Clear output tables
        clear_output_tables(v4_db, 'v4')
        clear_output_tables(v3_db, 'v3')

        # Fix hydrogen capex in all scenarios (source DB used highGasCapex)
        fix_hydrogen_capex(v4_db, v3_db)

        # Apply scenario modifications
        scenario['prepare'](v4_db, v3_db)

        # Generate configs
        v4_cfg = generate_v4_config(key, v4_db)
        v3_cfg = generate_v3_config(key, v3_db)
        print(f'  v4 config: {v4_cfg.name}')
        print(f'  v3 config: {v3_cfg.name}')

    print('\n' + '=' * 70)
    print('Preparation complete. Next steps:')
    print()
    print('Step 1: Solve v4 (on db-migration/mip-dev with .venv):')
    print('  source .venv/bin/activate')
    for key in selected:
        rel_cfg = os.path.relpath(SCENARIO_CFG_DIR / f'{key}_v4.toml', REPO_ROOT)
        print(f'  echo "y" | temoa run {rel_cfg}')
    print()
    print('Step 2: Solve v3 (on mip-dev-52 with .venv312):')
    print('  git stash && git checkout mip-dev-52 && git stash pop')
    print('  source .venv312/bin/activate')
    for key in selected:
        rel_cfg = os.path.relpath(SCENARIO_CFG_DIR / f'{key}_v3', REPO_ROOT)
        print(
            f'  .venv312/bin/python '
            f'data_files/mip_migration_workspace/comparison/run_mipdev.py '
            f'--config {rel_cfg}'
        )
    print()
    print('Step 3: Compare results:')
    print('  python run_scenarios.py compare')
    print('=' * 70)


# ---------------------------------------------------------------------------
# Metrics extraction from temoa log output
# ---------------------------------------------------------------------------

METRICS_DIR = SCRIPT_DIR / 'scenario_metrics'


def parse_temoa_output(output_text):
    """Parse temoa run output for timing, model size, and objective."""
    metrics = {}

    # Build time: "Finished: Creating model instance (Time taken: 5.43s)"
    m = re.search(r'Creating model instance \(Time taken: ([\d.]+)s\)', output_text)
    if m:
        metrics['build_time_s'] = float(m.group(1))

    # Solve time: "Finished: Solving model unknown (Time taken: 17.51s)"
    m = re.search(r'Solving model \w+ \(Time taken: ([\d.]+)s\)', output_text)
    if m:
        metrics['solve_time_s'] = float(m.group(1))

    # Results time: "Finished: Processing results (Time taken: 2.13s)"
    m = re.search(r'Processing results \(Time taken: ([\d.]+)s\)', output_text)
    if m:
        metrics['results_time_s'] = float(m.group(1))

    # Model size: "Model built... Variables: 535830, Constraints: 448764"
    m = re.search(r'Variables:\s*([\d,]+),\s*Constraints:\s*([\d,]+)', output_text)
    if m:
        metrics['variables'] = int(m.group(1).replace(',', ''))
        metrics['constraints'] = int(m.group(2).replace(',', ''))

    # Objective: "Total Cost value: 27425068891.68"
    m = re.search(r'Total Cost value:\s*([\d.]+)', output_text)
    if m:
        metrics['objective'] = float(m.group(1))

    # Solver status: "Solver termination condition: optimal (optimal: True)"
    m = re.search(r'Solver termination condition:\s*(\w+)', output_text)
    if m:
        metrics['solver_status'] = m.group(1)

    return metrics


def save_metrics(scenario_key, version, metrics):
    """Save metrics to JSON file."""
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    path = METRICS_DIR / f'{scenario_key}_{version}.json'
    path.write_text(json.dumps(metrics, indent=2) + '\n')
    return path


def load_metrics(scenario_key, version):
    """Load metrics from JSON file, or return empty dict."""
    path = METRICS_DIR / f'{scenario_key}_{version}.json'
    if path.exists():
        return json.loads(path.read_text())
    return {}


# ---------------------------------------------------------------------------
# solve command (v4)
# ---------------------------------------------------------------------------


def cmd_solve_v4(args):
    """Solve all v4 scenarios, capturing timing metrics."""
    print('=' * 70)
    print('Solving v4 scenarios')
    print('=' * 70)

    scenario_filter = args.scenario if hasattr(args, 'scenario') else None

    for key in SCENARIOS:
        if scenario_filter and key != scenario_filter:
            continue

        cfg = SCENARIO_CFG_DIR / f'{key}_v4.toml'
        if not cfg.exists():
            print(f'\n  SKIP {key}: config not found ({cfg})')
            continue

        print(f'\n--- Solving {key} (v4) ---')
        wall_start = time.time()

        result = subprocess.run(
            ['temoa', 'run', str(cfg)],
            input='y\n',
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )

        wall_time = time.time() - wall_start
        output = result.stdout + result.stderr

        if result.returncode != 0:
            print(f'  ERROR: temoa exited with code {result.returncode}')
            print(output[-500:] if len(output) > 500 else output)
            # Save error metrics
            save_metrics(
                key,
                'v4',
                {
                    'status': 'error',
                    'exit_code': result.returncode,
                    'wall_time_s': wall_time,
                    'output_tail': output[-500:],
                },
            )
            continue

        metrics = parse_temoa_output(output)
        metrics['wall_time_s'] = round(wall_time, 2)
        metrics['version'] = 'v4'
        metrics['scenario'] = key

        mpath = save_metrics(key, 'v4', metrics)

        status = metrics.get('solver_status', '?')
        build = metrics.get('build_time_s', '?')
        solve = metrics.get('solve_time_s', '?')
        nvars = metrics.get('variables', '?')
        ncons = metrics.get('constraints', '?')
        obj = metrics.get('objective', '?')

        print(f'  Status: {status}')
        print(f'  Build: {build}s | Solve: {solve}s | Wall: {wall_time:.1f}s')
        print(
            f'  Variables: {nvars:,} | Constraints: {ncons:,}'
            if isinstance(nvars, int)
            else f'  Variables: {nvars} | Constraints: {ncons}'
        )
        print(f'  Objective: ${obj:,.2f}' if isinstance(obj, float) else f'  Objective: {obj}')
        print(f'  Metrics saved: {mpath.name}')

    print('\n' + '=' * 70)
    print('v4 solves complete.')
    print('=' * 70)


# ---------------------------------------------------------------------------
# Results extraction
# ---------------------------------------------------------------------------


def extract_v4_results(db_path, scenario_name):
    """Extract generation shares, new capacity, and emissions from a solved v4 DB."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    results = {'gen_by_cat': {}, 'new_cap': {}, 'emissions': {}, 'total_gen': {}}

    # Check if results exist
    cur.execute('SELECT COUNT(*) FROM output_flow_out WHERE scenario = ?', (scenario_name,))
    if cur.fetchone()[0] == 0:
        print(f'    WARNING: No output_flow_out rows for scenario={scenario_name}')
        conn.close()
        return None

    # Generation by category and period
    cur.execute(
        'SELECT period, tech, SUM(flow) FROM output_flow_out '
        "WHERE scenario = ? AND output_comm = 'electricity' "
        'GROUP BY period, tech',
        (scenario_name,),
    )
    gen_data = {}
    for period, tech, flow in cur.fetchall():
        if is_excluded_from_gen(tech):
            continue
        cat = classify_tech(tech)
        gen_data.setdefault(period, {}).setdefault(cat, 0.0)
        gen_data[period][cat] += flow

    # Compute shares
    for period, cats in gen_data.items():
        total = sum(cats.values())
        results['total_gen'][period] = total
        results['gen_by_cat'][period] = {}
        for cat, val in sorted(cats.items()):
            results['gen_by_cat'][period][cat] = {
                'mwh': val,
                'share': val / total * 100 if total > 0 else 0.0,
            }

    # New capacity (built capacity)
    cur.execute(
        'SELECT tech, vintage, SUM(capacity) FROM output_built_capacity '
        'WHERE scenario = ? AND capacity > 0.1 '
        'GROUP BY tech, vintage',
        (scenario_name,),
    )
    for tech, vintage, cap in cur.fetchall():
        cat = classify_tech(tech)
        results['new_cap'].setdefault(vintage, []).append(
            {
                'tech': tech,
                'category': cat,
                'capacity_mw': cap,
            }
        )

    # Emissions
    cur.execute(
        'SELECT region, period, emis_comm, SUM(emission) FROM output_emission '
        'WHERE scenario = ? GROUP BY region, period, emis_comm',
        (scenario_name,),
    )
    for region, period, emis_comm, amount in cur.fetchall():
        results['emissions'].setdefault(period, {}).setdefault(emis_comm, {})
        results['emissions'][period][emis_comm][region] = amount

    # Net capacity (for offshore wind check)
    cur.execute(
        'SELECT region, period, tech, SUM(capacity) FROM output_net_capacity '
        'WHERE scenario = ? GROUP BY region, period, tech',
        (scenario_name,),
    )
    results['net_cap'] = {}
    for region, period, tech, cap in cur.fetchall():
        results['net_cap'].setdefault(period, {}).setdefault(tech, {})
        results['net_cap'][period][tech][region] = cap

    conn.close()
    return results


def extract_v3_results(db_path, scenario_name):
    """Extract generation shares, new capacity, and emissions from a solved v3 DB."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    results = {'gen_by_cat': {}, 'new_cap': {}, 'emissions': {}, 'total_gen': {}}

    # Check if results exist
    cur.execute('SELECT COUNT(*) FROM Output_VFlow_Out WHERE scenario = ?', (scenario_name,))
    if cur.fetchone()[0] == 0:
        print(f'    WARNING: No Output_VFlow_Out rows for scenario={scenario_name}')
        conn.close()
        return None

    # v3 electricity commodity — check what's available
    cur.execute(
        'SELECT DISTINCT output_comm FROM Output_VFlow_Out '
        "WHERE scenario = ? AND (output_comm LIKE '%ELC%' OR output_comm = 'electricity')",
        (scenario_name,),
    )
    elc_comms = [row[0] for row in cur.fetchall()]
    if not elc_comms:
        print('    WARNING: No electricity commodity found in Output_VFlow_Out')
        conn.close()
        return None

    placeholders = ','.join('?' * len(elc_comms))
    cur.execute(
        f'SELECT t_periods, tech, SUM(vflow_out) FROM Output_VFlow_Out '
        f'WHERE scenario = ? AND output_comm IN ({placeholders}) '
        f'GROUP BY t_periods, tech',
        (scenario_name, *elc_comms),
    )
    gen_data = {}
    for period, tech, flow in cur.fetchall():
        # Strip region prefix for classification
        stripped = strip_region_prefix(tech)
        if is_excluded_from_gen(stripped):
            continue
        cat = classify_tech(stripped)
        gen_data.setdefault(period, {}).setdefault(cat, 0.0)
        gen_data[period][cat] += flow

    for period, cats in gen_data.items():
        total = sum(cats.values())
        results['total_gen'][period] = total
        results['gen_by_cat'][period] = {}
        for cat, val in sorted(cats.items()):
            results['gen_by_cat'][period][cat] = {
                'mwh': val,
                'share': val / total * 100 if total > 0 else 0.0,
            }

    # New capacity: vintage == t_periods means new build
    cur.execute(
        'SELECT tech, vintage, SUM(capacity) FROM Output_V_Capacity '
        'WHERE scenario = ? AND vintage = t_periods AND capacity > 0.1 '
        'GROUP BY tech, vintage',
        (scenario_name,),
    )
    for tech, vintage, cap in cur.fetchall():
        stripped = strip_region_prefix(tech)
        cat = classify_tech(stripped)
        results['new_cap'].setdefault(vintage, []).append(
            {
                'tech': tech,
                'category': cat,
                'capacity_mw': cap,
            }
        )

    # Emissions
    cur.execute(
        'SELECT regions, t_periods, emissions_comm, SUM(emissions) FROM Output_Emissions '
        'WHERE scenario = ? GROUP BY regions, t_periods, emissions_comm',
        (scenario_name,),
    )
    for region, period, emis_comm, amount in cur.fetchall():
        results['emissions'].setdefault(period, {}).setdefault(emis_comm, {})
        results['emissions'][period][emis_comm][region] = amount

    # Net capacity for offshore wind check
    cur.execute(
        'SELECT regions, t_periods, tech, SUM(capacity) FROM Output_V_Capacity '
        'WHERE scenario = ? GROUP BY regions, t_periods, tech',
        (scenario_name,),
    )
    results['net_cap'] = {}
    for region, period, tech, cap in cur.fetchall():
        stripped = strip_region_prefix(tech)
        results['net_cap'].setdefault(period, {}).setdefault(stripped, {})
        # Aggregate across region-prefixed variants
        results['net_cap'][period][stripped][region] = (
            results['net_cap'][period][stripped].get(region, 0.0) + cap
        )

    conn.close()
    return results


# ---------------------------------------------------------------------------
# Comparison and reporting
# ---------------------------------------------------------------------------

# Baseline reference data
BASELINE = {
    'total_gen': {2027: 39_536_489.0, 2030: 46_676_896.0},
    'emissions': {
        2027: {'CO2': {'TRE': 9_405_269.0, 'TREW': 797_370.0, 'total': 10_202_639.0}},
        2030: {'CO2': {'TRE': 16_495_782.0, 'TREW': 849_847.0, 'total': 17_345_629.0}},
    },
    'gen_shares': {
        2027: {
            'gas': 49.9,
            'wind': 26.4,
            'solar': 8.9,
            'coal': 5.1,
            'nuclear': 8.7,
            'distributed_gen': 1.0,
        },
        2030: {
            'gas': 42.3,
            'wind': 22.4,
            'solar': 7.5,
            'coal': 18.7,
            'nuclear': 7.4,
            'distributed_gen': 1.7,
        },
    },
}


def print_gen_shares(results, label, period):
    """Print generation shares for a single version/period."""
    if results is None or period not in results['gen_by_cat']:
        print(f'    {label}: NO DATA')
        return
    cats = results['gen_by_cat'][period]
    total = results['total_gen'].get(period, 0)
    parts = []
    for cat in [
        'wind',
        'solar',
        'gas',
        'coal',
        'nuclear',
        'hydro',
        'biomass',
        'distributed_gen',
        'hydrogen',
        'petroleum',
        'other',
    ]:
        if cat in cats:
            parts.append(f'{cat}={cats[cat]["share"]:.1f}%')
    print(f'    {label} ({total / 1e6:.1f}M MWh): {", ".join(parts)}')


def print_new_capacity(results, label, period):
    """Print new capacity builds aggregated by category, with top individual techs."""
    if results is None or period not in results.get('new_cap', {}):
        print(f'    {label}: none')
        return
    builds = results['new_cap'][period]
    if not builds:
        print(f'    {label}: none')
        return

    # Aggregate by category
    by_cat = {}
    for b in builds:
        cat = b['category']
        by_cat.setdefault(cat, 0.0)
        by_cat[cat] += b['capacity_mw']

    # Print category totals
    cat_parts = []
    for cat, total in sorted(by_cat.items(), key=lambda x: -x[1]):
        if total >= 1.0:
            cat_parts.append(f'{cat}={total:,.0f} MW')
    print(f'    {label}: {", ".join(cat_parts)}')

    # Print individual techs > 100 MW
    significant = [b for b in builds if b['capacity_mw'] >= 100]
    for b in sorted(significant, key=lambda x: -x['capacity_mw']):
        print(f'      {b["tech"]}: {b["capacity_mw"]:,.0f} MW')


def get_total_emissions(results, period, emis_comm='CO2'):
    """Sum emissions across all regions for a period."""
    if results is None or period not in results.get('emissions', {}):
        return None
    emis = results['emissions'].get(period, {}).get(emis_comm, {})
    return sum(emis.values())


def get_offshore_wind_capacity(results, period):
    """Sum offshore wind net capacity across all techs for a period."""
    if results is None or period not in results.get('net_cap', {}):
        return 0.0
    total = 0.0
    for tech, regions in results['net_cap'][period].items():
        if 'offshorewind' in tech.lower():
            total += sum(regions.values())
    return total


def compare_shares(v4_results, v3_results, period, threshold=2.0):
    """Compare generation shares between v4 and v3 for a period. Returns list of mismatches."""
    mismatches = []
    if v4_results is None or v3_results is None:
        return mismatches

    v4_cats = v4_results.get('gen_by_cat', {}).get(period, {})
    v3_cats = v3_results.get('gen_by_cat', {}).get(period, {})
    all_cats = set(v4_cats.keys()) | set(v3_cats.keys())

    for cat in sorted(all_cats):
        v4_share = v4_cats.get(cat, {}).get('share', 0.0)
        v3_share = v3_cats.get(cat, {}).get('share', 0.0)
        diff = abs(v4_share - v3_share)
        if diff > threshold:
            mismatches.append((cat, v4_share, v3_share, diff))
    return mismatches


def run_sniff_tests(scenario_key, v4_results, v3_results):
    """Run scenario-specific sniff tests. Returns (pass_count, fail_count, messages)."""
    passes = 0
    fails = 0
    msgs = []

    def check(condition, msg):
        nonlocal passes, fails
        if condition:
            passes += 1
            msgs.append(f'  PASS: {msg}')
        else:
            fails += 1
            msgs.append(f'  FAIL: {msg}')

    # Cross-version match (2pp threshold)
    for period in [2027, 2030]:
        mismatches = compare_shares(v4_results, v3_results, period)
        if mismatches:
            detail = '; '.join(
                f'{cat}: v4={v4s:.1f}% v3={v3s:.1f}% (diff={d:.1f}pp)'
                for cat, v4s, v3s, d in mismatches
            )
            check(False, f'Period {period} cross-version match (2pp): {detail}')
        else:
            check(True, f'Period {period} cross-version match within 2pp')

    # Scenario-specific tests
    if scenario_key == 's1_discount':
        # Lower discount rates favor capital-intensive techs. Check that the model solved
        # and generation shares shifted (or at least didn't break). New renewable builds
        # are not guaranteed in a 4-week January model with sufficient existing capacity.
        for version, results, label in [('v4', v4_results, 'v4'), ('v3', v3_results, 'v3')]:
            if results is None:
                continue
            has_gen = bool(results.get('total_gen', {}))
            check(has_gen, f'{label}: Model solved with generation output')
            # Objective should be lower or similar to baseline ($27.4B baseline)
            obj = load_metrics(scenario_key, version.replace('v4', 'v4').replace('v3', 'v3')).get(
                'objective'
            )
            if obj is not None:
                check(
                    obj < 30e9,  # Generous bound — lower discount = lower cost
                    f'{label}: Objective ${obj / 1e9:.1f}B (should be <= baseline ~$27B)',
                )

    elif scenario_key == 's2_demand':
        # Total gen should be ~1.2x baseline
        for version, results, label in [('v4', v4_results, 'v4'), ('v3', v3_results, 'v3')]:
            if results is None:
                continue
            for period in [2027, 2030]:
                total = results.get('total_gen', {}).get(period, 0)
                baseline = BASELINE['total_gen'].get(period, 1)
                ratio = total / baseline if baseline else 0
                check(
                    1.15 <= ratio <= 1.25,
                    f'{label} {period}: Total gen ratio = {ratio:.3f}x baseline '
                    f'({total / 1e6:.1f}M vs {baseline / 1e6:.1f}M MWh)',
                )

    elif scenario_key == 's3_emission':
        limits = {2027: 10_202_639 * 0.5, 2030: 17_345_629 * 0.5}
        for version, results, label in [('v4', v4_results, 'v4'), ('v3', v3_results, 'v3')]:
            if results is None:
                continue
            for period in [2027, 2030]:
                total_co2 = get_total_emissions(results, period, 'CO2')
                if total_co2 is not None:
                    limit = limits[period]
                    # Allow 1% tolerance
                    check(
                        total_co2 <= limit * 1.01,
                        f'{label} {period}: CO2 = {total_co2:,.0f} <= limit {limit:,.0f} '
                        f'({total_co2 / limit * 100:.1f}%)',
                    )
                else:
                    check(False, f'{label} {period}: No emission data')

        # Coal should drop vs baseline
        for version, results, label in [('v4', v4_results, 'v4'), ('v3', v3_results, 'v3')]:
            if results is None:
                continue
            for period in [2027, 2030]:
                coal_share = (
                    results.get('gen_by_cat', {}).get(period, {}).get('coal', {}).get('share', 0.0)
                )
                baseline_coal = BASELINE['gen_shares'].get(period, {}).get('coal', 0.0)
                check(
                    coal_share < baseline_coal,
                    f'{label} {period}: Coal share {coal_share:.1f}% < baseline {baseline_coal:.1f}%',
                )

    elif scenario_key == 's4_rps':
        targets = {2027: 50.0, 2030: 80.0}
        for version, results, label in [('v4', v4_results, 'v4'), ('v3', v3_results, 'v3')]:
            if results is None:
                continue
            for period in [2027, 2030]:
                cats = results.get('gen_by_cat', {}).get(period, {})
                renewable_share = sum(
                    cats.get(c, {}).get('share', 0.0) for c in ['wind', 'solar', 'hydro', 'biomass']
                )
                target = targets[period]
                check(
                    renewable_share >= target - 1.0,  # 1pp tolerance
                    f'{label} {period}: Renewable share {renewable_share:.1f}% >= {target}% target',
                )

        # Should have new renewable capacity
        for version, results, label in [('v4', v4_results, 'v4'), ('v3', v3_results, 'v3')]:
            if results is None:
                continue
            new_renewable = 0.0
            for period, builds in results.get('new_cap', {}).items():
                for b in builds:
                    if b['category'] in ('wind', 'solar', 'hydro', 'biomass'):
                        new_renewable += b['capacity_mw']
            check(
                new_renewable > 1000,
                f'{label}: New renewable capacity = {new_renewable:,.0f} MW (need significant builds)',
            )

    elif scenario_key == 's5_windcap':
        for version, results, label in [('v4', v4_results, 'v4'), ('v3', v3_results, 'v3')]:
            if results is None:
                continue
            offshore_cap = get_offshore_wind_capacity(results, 2030)
            check(
                offshore_cap >= 4900,  # 100 MW tolerance
                f'{label} 2030: Offshore wind capacity = {offshore_cap:,.0f} MW >= 5000 MW',
            )

    elif scenario_key == 's6_greenfield':
        # Total gen should be ~10x baseline
        for version, results, label in [('v4', v4_results, 'v4'), ('v3', v3_results, 'v3')]:
            if results is None:
                continue
            for period in [2027, 2030]:
                total = results.get('total_gen', {}).get(period, 0)
                baseline = BASELINE['total_gen'].get(period, 1)
                ratio = total / baseline if baseline else 0
                check(
                    8.0 <= ratio <= 12.0,
                    f'{label} {period}: Total gen ratio = {ratio:.1f}x baseline '
                    f'({total / 1e6:.1f}M vs {baseline / 1e6:.1f}M MWh)',
                )
        # Should have massive new capacity builds
        for version, results, label in [('v4', v4_results, 'v4'), ('v3', v3_results, 'v3')]:
            if results is None:
                continue
            total_new = 0.0
            for period, builds in results.get('new_cap', {}).items():
                for b in builds:
                    total_new += b['capacity_mw']
            check(
                total_new > 50_000,
                f'{label}: Total new capacity = {total_new:,.0f} MW (expect massive builds)',
            )

    return passes, fails, msgs


def print_metrics_table(v4_metrics, v3_metrics):
    """Print a side-by-side metrics comparison table."""
    print('\n  --- Build / Solve Metrics ---')
    header = f'    {"Metric":<25} {"v4":>12} {"v3":>12} {"ratio":>8}'
    print(header)
    print(f'    {"-" * 57}')

    rows = [
        ('Variables', 'variables', '{:,}'),
        ('Constraints', 'constraints', '{:,}'),
        ('Build time (s)', 'build_time_s', '{:.2f}'),
        ('Solve time (s)', 'solve_time_s', '{:.2f}'),
        ('Results time (s)', 'results_time_s', '{:.2f}'),
        ('Wall time (s)', 'wall_time_s', '{:.1f}'),
        ('Objective ($)', 'objective', '{:,.0f}'),
    ]

    for label, key, fmt in rows:
        v4_val = v4_metrics.get(key)
        v3_val = v3_metrics.get(key)
        v4_str = fmt.format(v4_val) if v4_val is not None else 'N/A'
        v3_str = fmt.format(v3_val) if v3_val is not None else 'N/A'
        if v4_val and v3_val and isinstance(v4_val, (int, float)) and v3_val != 0:
            ratio = f'{v4_val / v3_val:.2f}x'
        else:
            ratio = ''
        print(f'    {label:<25} {v4_str:>12} {v3_str:>12} {ratio:>8}')


def cmd_compare(args):
    """Compare results from solved scenario DBs."""
    print('=' * 70)
    print('Scenario Comparison: Results')
    print('=' * 70)

    scenario_filter = args.scenario if hasattr(args, 'scenario') else None
    total_passes = 0
    total_fails = 0

    for key, scenario in SCENARIOS.items():
        if scenario_filter and key != scenario_filter:
            continue

        print(f'\n{"=" * 70}')
        print(f'{key}: {scenario["name"]}')
        print(f'{"=" * 70}')

        v4_db = SCENARIO_DB_DIR / f'{key}_v4.sqlite'
        v3_db = SCENARIO_DB_DIR / f'{key}_v3.sqlite'

        if not v4_db.exists():
            print(f'  v4 DB not found: {v4_db}')
            continue
        if not v3_db.exists():
            print(f'  v3 DB not found: {v3_db}')
            continue

        v4_scenario = f'{key}_v4'
        v3_scenario = f'{key}_mipdev'

        # Load and display metrics
        v4_metrics = load_metrics(key, 'v4')
        v3_metrics = load_metrics(key, 'v3')
        if v4_metrics or v3_metrics:
            print_metrics_table(v4_metrics, v3_metrics)

        print(f'\n  Extracting v4 results (scenario={v4_scenario})...')
        v4_results = extract_v4_results(v4_db, v4_scenario)
        print(f'  Extracting v3 results (scenario={v3_scenario})...')
        v3_results = extract_v3_results(v3_db, v3_scenario)

        # Print generation shares
        for period in [2027, 2030]:
            print(f'\n  --- Period {period} Generation Shares ---')
            print_gen_shares(v4_results, 'v4', period)
            print_gen_shares(v3_results, 'v3', period)
            baseline = BASELINE['gen_shares'].get(period, {})
            bl_parts = [f'{k}={v:.1f}%' for k, v in sorted(baseline.items())]
            print(f'    baseline: {", ".join(bl_parts)}')

        # Print new capacity
        for period in [2027, 2030]:
            print(f'\n  --- Period {period} New Capacity ---')
            print_new_capacity(v4_results, 'v4', period)
            print_new_capacity(v3_results, 'v3', period)

        # Print emissions (for S3 especially)
        if key == 's3_emission':
            print('\n  --- CO2 Emissions ---')
            for period in [2027, 2030]:
                v4_co2 = get_total_emissions(v4_results, period, 'CO2')
                v3_co2 = get_total_emissions(v3_results, period, 'CO2')
                limit = {2027: 10_202_639 * 0.5, 2030: 17_345_629 * 0.5}[period]
                v4_str = f'{v4_co2:,.0f}' if v4_co2 is not None else 'N/A'
                v3_str = f'{v3_co2:,.0f}' if v3_co2 is not None else 'N/A'
                print(f'    {period}: v4={v4_str}, v3={v3_str}, limit={limit:,.0f}')

        # Print offshore wind capacity (for S5)
        if key == 's5_windcap':
            print('\n  --- Offshore Wind Net Capacity ---')
            for period in [2027, 2030]:
                v4_ow = get_offshore_wind_capacity(v4_results, period)
                v3_ow = get_offshore_wind_capacity(v3_results, period)
                print(f'    {period}: v4={v4_ow:,.0f} MW, v3={v3_ow:,.0f} MW')

        # Run sniff tests
        print('\n  --- Sniff Tests ---')
        passes, fails, msgs = run_sniff_tests(key, v4_results, v3_results)
        for msg in msgs:
            print(msg)
        total_passes += passes
        total_fails += fails

    # Metrics summary table across all scenarios
    print(f'\n{"=" * 70}')
    print('METRICS SUMMARY')
    print(f'{"=" * 70}')
    print(
        f'  {"Scenario":<15} {"v4 build":>10} {"v4 solve":>10} {"v4 vars":>10} '
        f'{"v4 cons":>10} {"v3 build":>10} {"v3 solve":>10} {"v3 vars":>10} {"v3 cons":>10}'
    )
    print(f'  {"-" * 95}')
    for key in SCENARIOS:
        if scenario_filter and key != scenario_filter:
            continue
        v4m = load_metrics(key, 'v4')
        v3m = load_metrics(key, 'v3')

        def fmt(d, k, f='{:.1f}'):
            v = d.get(k)
            return f.format(v) if v is not None else 'N/A'

        def fmti(d, k):
            v = d.get(k)
            return f'{v:,}' if v is not None else 'N/A'

        print(
            f'  {key:<15} {fmt(v4m, "build_time_s"):>10} {fmt(v4m, "solve_time_s"):>10} '
            f'{fmti(v4m, "variables"):>10} {fmti(v4m, "constraints"):>10} '
            f'{fmt(v3m, "build_time_s"):>10} {fmt(v3m, "solve_time_s"):>10} '
            f'{fmti(v3m, "variables"):>10} {fmti(v3m, "constraints"):>10}'
        )

    print(f'\n{"=" * 70}')
    print(f'SNIFF TEST SUMMARY: {total_passes} passed, {total_fails} failed')
    print('=' * 70)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description='Scenario comparison test suite: v4 vs mip-dev')
    subparsers = parser.add_subparsers(dest='command')

    # prepare
    prep_parser = subparsers.add_parser('prepare', help='Create scenario DBs and configs')
    prep_parser.add_argument(
        '--scenario', '-s', help='Prepare only this scenario (e.g., s6_greenfield)'
    )

    # solve-v4
    solve_parser = subparsers.add_parser('solve-v4', help='Solve all v4 scenarios with metrics')
    solve_parser.add_argument(
        '--scenario', '-s', help='Solve only this scenario (e.g., s3_emission)'
    )

    # compare
    cmp_parser = subparsers.add_parser('compare', help='Compare solved results')
    cmp_parser.add_argument(
        '--scenario', '-s', help='Compare only this scenario (e.g., s3_emission)'
    )

    args = parser.parse_args()

    if args.command == 'prepare':
        cmd_prepare(args)
    elif args.command == 'solve-v4':
        cmd_solve_v4(args)
    elif args.command == 'compare':
        cmd_compare(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
