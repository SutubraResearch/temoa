#!/usr/bin/env python3
"""
Custom migration for the reduced 4-week legacy DB -> Temoa v4 DB.

This script is intentionally explicit (not generic) so mappings are auditable.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path


def fetch_scalar(conn: sqlite3.Connection, query: str, default: float | int | None = None):
    row = conn.execute(query).fetchone()
    return row[0] if row and row[0] is not None else default


def parse_sort_key(label: str) -> tuple[int, str]:
    # Natural-ish ordering for labels like h1, h2, ..., p1, p2, ...
    prefix = ''.join(ch for ch in label if not ch.isdigit())
    digits = ''.join(ch for ch in label if ch.isdigit())
    if digits:
        return (int(digits), prefix)
    return (10**9, label)


def migrate(source: Path, schema: Path, target: Path, days_per_period: int | None = None) -> None:
    if not source.exists():
        raise FileNotFoundError(f'Source DB does not exist: {source}')
    if not schema.exists():
        raise FileNotFoundError(f'Schema file does not exist: {schema}')

    if target.exists():
        target.unlink()

    conn = sqlite3.connect(target)
    conn.execute('PRAGMA foreign_keys = OFF;')
    with open(schema, encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.execute('ATTACH DATABASE ? AS src', (str(source),))

    # ---------------------------------------------------------------------
    # Core metadata and lookup tables
    # ---------------------------------------------------------------------
    global_discount_rate = fetch_scalar(
        conn, 'SELECT rate FROM src.GlobalDiscountRate LIMIT 1', 0.05
    )

    # Auto-detect days_per_period from season count if not specified
    if days_per_period is None:
        season_count = fetch_scalar(conn, 'SELECT COUNT(DISTINCT t_season) FROM src.time_season', 4)
        days_per_period = season_count * 7  # Assume each season is 1 week
        print(f'Auto-detected {season_count} seasons -> days_per_period = {days_per_period}')

    conn.execute('DELETE FROM metadata')
    conn.executemany(
        'INSERT INTO metadata (element, value, notes) VALUES (?, ?, ?)',
        [
            ('DB_MAJOR', 4, 'DB major version number'),
            ('DB_MINOR', 0, 'DB minor version number'),
            ('days_per_period', days_per_period, 'count of days in each period'),
        ],
    )

    conn.execute('DELETE FROM metadata_real')
    conn.executemany(
        'INSERT INTO metadata_real (element, value, notes) VALUES (?, ?, ?)',
        [
            ('global_discount_rate', float(global_discount_rate), 'Discount Rate for future costs'),
            ('default_loan_rate', 0.05, 'Default Loan Rate if not specified in LoanRate table'),
        ],
    )

    conn.execute(
        'INSERT OR REPLACE INTO region (region, notes) SELECT regions, region_note FROM src.regions'
    )

    seasons = [
        r[0] for r in conn.execute('SELECT DISTINCT t_season FROM src.time_season').fetchall()
    ]
    conn.executemany(
        'INSERT OR REPLACE INTO season_label (season, notes) VALUES (?, NULL)',
        [(s,) for s in sorted(seasons, key=parse_sort_key)],
    )

    sectors = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT sector FROM src.technologies WHERE sector IS NOT NULL AND TRIM(sector) <> ''"
        ).fetchall()
    ]
    conn.executemany(
        'INSERT OR REPLACE INTO sector_label (sector, notes) VALUES (?, NULL)',
        [(s,) for s in sorted(sectors)],
    )

    # Commodity flags: infer source/emission flags from network structure + emission tables
    input_comms = {
        r[0] for r in conn.execute('SELECT DISTINCT input_comm FROM src.Efficiency').fetchall()
    }
    output_comms = {
        r[0] for r in conn.execute('SELECT DISTINCT output_comm FROM src.Efficiency').fetchall()
    }
    source_comms = input_comms - output_comms
    emission_comms = {
        r[0] for r in conn.execute('SELECT DISTINCT emis_comm FROM src.EmissionActivity').fetchall()
    }
    emission_limit_comms = {
        r[0] for r in conn.execute('SELECT DISTINCT emis_comm FROM src.EmissionLimit').fetchall()
    }
    emission_comms.update(emission_limit_comms)
    demand_comms = {
        r[0] for r in conn.execute('SELECT DISTINCT demand_comm FROM src.Demand').fetchall()
    }

    if 'ethos' in {r[0] for r in conn.execute('SELECT comm_name FROM src.commodities').fetchall()}:
        source_comms.add('ethos')

    commodity_rows = conn.execute(
        'SELECT comm_name, flag, comm_desc FROM src.commodities ORDER BY comm_name'
    ).fetchall()
    for comm_name, old_flag, comm_desc in commodity_rows:
        if old_flag == 'd':
            new_flag = 'd'
        elif comm_name in emission_comms:
            new_flag = 'e'
        elif comm_name in source_comms:
            new_flag = 's'
        else:
            new_flag = 'p'
        conn.execute(
            'INSERT OR REPLACE INTO commodity (name, flag, description, units) VALUES (?, ?, ?, NULL)',
            (comm_name, new_flag, comm_desc),
        )

    # Add commodity rows that are referenced by other tables but absent from old commodities table.
    known_comms = {r[0] for r in conn.execute('SELECT name FROM commodity').fetchall()}
    referenced_comms = (
        set(input_comms) | set(output_comms) | set(demand_comms) | set(emission_comms)
    )
    missing_comms = sorted(referenced_comms - known_comms)
    for comm_name in missing_comms:
        if comm_name in emission_comms:
            new_flag = 'e'
        elif comm_name in demand_comms:
            new_flag = 'd'
        elif comm_name in source_comms:
            new_flag = 's'
        else:
            new_flag = 'p'
        conn.execute(
            'INSERT OR REPLACE INTO commodity (name, flag, description, units) VALUES (?, ?, ?, NULL)',
            (comm_name, new_flag, f'Added during migration ({new_flag})'),
        )

    # ---------------------------------------------------------------------
    # Time tables
    # ---------------------------------------------------------------------
    old_periods = conn.execute(
        'SELECT t_periods, flag FROM src.time_periods ORDER BY t_periods'
    ).fetchall()
    for idx, (period, flag) in enumerate(old_periods, start=1):
        conn.execute(
            'INSERT OR REPLACE INTO time_period (sequence, period, flag) VALUES (?, ?, ?)',
            (idx, period, flag),
        )

    tods = [r[0] for r in conn.execute('SELECT t_day FROM src.time_of_day').fetchall()]
    for idx, tod in enumerate(sorted(tods, key=parse_sort_key), start=1):
        conn.execute(
            'INSERT OR REPLACE INTO time_of_day (sequence, tod) VALUES (?, ?)',
            (idx, tod),
        )

    tspp = conn.execute(
        'SELECT periods, season_name FROM src.time_seasons_per_period ORDER BY periods, season_name'
    ).fetchall()
    seasons_by_period: dict[int, list[str]] = {}
    for period, season in tspp:
        seasons_by_period.setdefault(period, []).append(season)
    for period, period_seasons in seasons_by_period.items():
        ordered = sorted(set(period_seasons), key=parse_sort_key)
        for idx, season in enumerate(ordered, start=1):
            conn.execute(
                'INSERT OR REPLACE INTO time_season (period, sequence, season, notes) VALUES (?, ?, ?, NULL)',
                (period, idx, season),
            )

    conn.execute(
        """
        INSERT OR REPLACE INTO time_segment_fraction (period, season, tod, segment_fraction, notes)
        SELECT periods, season_name, time_of_day_name, segfrac, segfrac_notes
        FROM src.SegFrac
        """
    )

    # ---------------------------------------------------------------------
    # Technology table + attribute flags
    # ---------------------------------------------------------------------
    def load_tech_set(table: str) -> set[str]:
        try:
            rows = conn.execute(f'SELECT tech FROM src.{table}').fetchall()
            return {r[0] for r in rows}
        except sqlite3.OperationalError:
            return set()

    tech_curtail = load_tech_set('tech_curtailment')
    tech_exchange = load_tech_set('tech_exchange')
    tech_reserve = load_tech_set('tech_reserve')
    tech_annual = load_tech_set('tech_annual')
    tech_flex = load_tech_set('tech_flex')
    tech_retire = load_tech_set('tech_retirement')

    tech_rows = conn.execute(
        """
        SELECT tech, flag, sector, tech_desc, tech_category
        FROM src.technologies
        ORDER BY tech
        """
    ).fetchall()

    for tech, flag, sector, tech_desc, tech_category in tech_rows:
        conn.execute(
            """
            INSERT OR REPLACE INTO technology
            (tech, flag, sector, category, sub_category, unlim_cap, annual, reserve, curtail, retire,
             flex, exchange, seas_stor, description)
            VALUES (?, ?, ?, ?, NULL, 0, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                tech,
                flag,
                sector,
                tech_category,
                1 if tech in tech_annual else 0,
                1 if tech in tech_reserve else 0,
                1 if tech in tech_curtail else 0,
                1 if tech in tech_retire else 0,
                1 if tech in tech_flex else 0,
                1 if tech in tech_exchange else 0,
                tech_desc,
            ),
        )

    # ---------------------------------------------------------------------
    # Direct table mappings
    # ---------------------------------------------------------------------
    conn.execute(
        """
        INSERT OR REPLACE INTO existing_capacity (region, tech, vintage, capacity, units, notes)
        SELECT regions, tech, vintage, exist_cap, exist_cap_units, exist_cap_notes
        FROM src.ExistingCapacity
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO efficiency (region, input_comm, tech, vintage, output_comm, efficiency, units, notes)
        SELECT regions, input_comm, tech, vintage, output_comm, efficiency, NULL, eff_notes
        FROM src.Efficiency
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO cost_invest (region, tech, vintage, cost, units, notes)
        SELECT regions, tech, vintage, cost_invest, cost_invest_units, cost_invest_notes
        FROM src.CostInvest
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO cost_fixed (region, period, tech, vintage, cost, units, notes)
        SELECT regions, periods, tech, vintage, cost_fixed, cost_fixed_units, cost_fixed_notes
        FROM src.CostFixed
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO cost_variable (region, period, tech, vintage, cost, units, notes)
        SELECT regions, periods, tech, vintage, cost_variable, cost_variable_units, cost_variable_notes
        FROM src.CostVariable
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO demand (region, period, commodity, demand, units, notes)
        SELECT regions, periods, demand_comm, demand, demand_units, demand_notes
        FROM src.Demand
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO demand_specific_distribution
        (region, period, season, tod, demand_name, dsd, notes)
        SELECT regions, periods, season_name, time_of_day_name, demand_name, dds, dds_notes
        FROM src.DemandSpecificDistribution
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO capacity_to_activity (region, tech, c2a, units, notes)
        SELECT regions, tech, c2a, NULL, c2a_notes
        FROM src.CapacityToActivity
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO capacity_credit (region, period, tech, vintage, credit, notes)
        SELECT regions, periods, tech, vintage, cf_tech, cf_tech_notes
        FROM src.CapacityCredit
        WHERE tech IN (SELECT tech FROM src.tech_reserve)
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO lifetime_tech (region, tech, lifetime, units, notes)
        SELECT regions, tech, life, NULL, life_notes
        FROM src.LifetimeTech
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO lifetime_process (region, tech, vintage, lifetime, units, notes)
        SELECT regions, tech, vintage, life_process, NULL, life_process_notes
        FROM src.LifetimeProcess
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO loan_rate (region, tech, vintage, rate, notes)
        SELECT regions, tech, vintage, tech_rate, tech_rate_notes
        FROM src.DiscountRate
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO emission_activity
        (region, emis_comm, input_comm, tech, vintage, output_comm, activity, units, notes)
        SELECT regions, emis_comm, input_comm, tech, vintage, output_comm, emis_act, emis_act_units, emis_act_notes
        FROM src.EmissionActivity
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO storage_duration (region, tech, duration, notes)
        SELECT regions, tech, duration, duration_notes
        FROM src.StorageDuration
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO ramp_up_hourly (region, tech, rate, notes)
        SELECT regions, tech, ramp_up, NULL
        FROM src.RampUp
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO ramp_down_hourly (region, tech, rate, notes)
        SELECT regions, tech, ramp_down, NULL
        FROM src.RampDown
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO planning_reserve_margin (region, margin, notes)
        SELECT regions, reserve_margin, NULL
        FROM src.PlanningReserveMargin
        """
    )

    # capacity_factor_tech requires a period in v4; expand by periods with seasons.
    conn.execute(
        """
        INSERT OR REPLACE INTO capacity_factor_tech (region, period, season, tod, tech, factor, notes)
        SELECT c.regions, p.periods, c.season_name, c.time_of_day_name, c.tech, c.cf_tech, c.cf_tech_notes
        FROM src.CapacityFactorTech c
        JOIN (SELECT DISTINCT periods, season_name FROM src.time_seasons_per_period) p
          ON p.season_name = c.season_name
        """
    )
    # Process-level CF table already has period.
    conn.execute(
        """
        INSERT OR REPLACE INTO capacity_factor_process
        (region, period, season, tod, tech, vintage, factor, notes)
        SELECT regions, periods, season_name, time_of_day_name, tech, vintage, cf_process, cf_process_notes
        FROM src.CapacityFactorProcess
        """
    )

    # LifetimeLoanTech in legacy has no vintage; expand across cost_invest vintages.
    conn.execute(
        """
        INSERT OR REPLACE INTO loan_lifetime_process (region, tech, vintage, lifetime, units, notes)
        SELECT ll.regions, ll.tech, ci.vintage, ll.loan, NULL, ll.loan_notes
        FROM src.LifetimeLoanTech ll
        JOIN (SELECT DISTINCT regions, tech, vintage FROM src.CostInvest) ci
          ON ci.regions = ll.regions
         AND ci.tech = ll.tech
        """
    )

    # Groups and membership
    conn.execute(
        """
        INSERT OR REPLACE INTO tech_group (group_name, notes)
        SELECT group_name, notes FROM src.groups
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO tech_group_member (group_name, tech)
        SELECT DISTINCT group_name, tech
        FROM src.tech_groups
        """
    )

    # Linked techs
    conn.execute(
        """
        INSERT OR REPLACE INTO linked_tech (primary_region, primary_tech, emis_comm, driven_tech, notes)
        SELECT primary_region, primary_tech, emis_comm, linked_tech, tech_linked_notes
        FROM src.LinkedTechs
        """
    )

    # ---------------------------------------------------------------------
    # Legacy constraint tables -> v4 limit_* with operators
    # ---------------------------------------------------------------------
    conn.execute(
        """
        INSERT OR REPLACE INTO limit_capacity (region, period, tech_or_group, operator, capacity, units, notes)
        SELECT regions, periods, tech, 'le', maxcap, maxcap_units, maxcap_notes
        FROM src.MaxCapacity
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO limit_capacity (region, period, tech_or_group, operator, capacity, units, notes)
        SELECT regions, periods, tech, 'ge', mincap, mincap_units, mincap_notes
        FROM src.MinCapacity
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO limit_new_capacity (region, period, tech_or_group, operator, new_cap, units, notes)
        SELECT regions, periods, tech, 'le', maxnewcap, maxnewcap_units, maxnewcap_notes
        FROM src.MaxNewCapacity
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO limit_new_capacity (region, period, tech_or_group, operator, new_cap, units, notes)
        SELECT regions, periods, tech, 'ge', minnewcap, minnewcap_units, minnewcap_notes
        FROM src.MinNewCapacity
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO limit_activity (region, period, tech_or_group, operator, activity, units, notes)
        SELECT regions, periods, tech, 'le', maxact, maxact_units, maxact_notes
        FROM src.MaxActivity
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO limit_activity (region, period, tech_or_group, operator, activity, units, notes)
        SELECT regions, periods, tech, 'ge', minact, minact_units, minact_notes
        FROM src.MinActivity
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO limit_resource (region, tech_or_group, operator, cum_act, units, notes)
        SELECT regions, tech, 'le', maxres, maxres_units, maxres_notes
        FROM src.MaxResource
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO limit_emission (region, period, emis_comm, operator, value, units, notes)
        SELECT regions, periods, emis_comm, 'le', emis_limit, emis_limit_units, emis_limit_notes
        FROM src.EmissionLimit
        """
    )

    # Group constraints (empty in this reduced DB, but include mapping)
    conn.execute(
        """
        INSERT OR REPLACE INTO limit_capacity (region, period, tech_or_group, operator, capacity, units, notes)
        SELECT regions, periods, group_name, 'le', max_cap_g, NULL, notes FROM src.MaxCapacityGroup
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO limit_capacity (region, period, tech_or_group, operator, capacity, units, notes)
        SELECT regions, periods, group_name, 'ge', min_cap_g, NULL, notes FROM src.MinCapacityGroup
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO limit_activity (region, period, tech_or_group, operator, activity, units, notes)
        SELECT regions, periods, group_name, 'le', max_act_g, NULL, notes FROM src.MaxActivityGroup
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO limit_activity (region, period, tech_or_group, operator, activity, units, notes)
        SELECT regions, periods, group_name, 'ge', min_act_g, NULL, notes FROM src.MinActivityGroup
        """
    )

    # Annual CF limits; infer output commodities from efficiency map
    conn.execute(
        """
        INSERT OR REPLACE INTO limit_annual_capacity_factor
        (region, period, tech, output_comm, operator, factor, notes)
        SELECT m.regions, m.periods, m.tech, eo.output_comm, 'ge', m.mincf, m.mincf_notes
        FROM src.MinAnnualCapacityFactor m
        JOIN (
            SELECT DISTINCT regions, tech, output_comm
            FROM src.Efficiency
        ) eo
          ON eo.regions = m.regions AND eo.tech = m.tech
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO limit_annual_capacity_factor
        (region, period, tech, output_comm, operator, factor, notes)
        SELECT m.regions, m.periods, m.tech, eo.output_comm, 'le', m.maxcf, m.maxcf_notes
        FROM src.MaxAnnualCapacityFactor m
        JOIN (
            SELECT DISTINCT regions, tech, output_comm
            FROM src.Efficiency
        ) eo
          ON eo.regions = m.regions AND eo.tech = m.tech
        """
    )

    # Growth-rate constraints
    conn.execute(
        """
        INSERT OR REPLACE INTO limit_growth_capacity
        (region, tech_or_group, operator, rate, seed, seed_units, notes)
        SELECT gm.regions,
               gm.tech,
               'le',
               gm.growthrate_max,
               COALESCE(gs.growthrate_seed, 0),
               gs.growthrate_seed_units,
               COALESCE(gm.growthrate_max_notes, gs.growthrate_seed_notes)
        FROM src.GrowthRateMax gm
        LEFT JOIN src.GrowthRateSeed gs
          ON gs.regions = gm.regions
         AND gs.tech = gm.tech
        """
    )

    # Split constraints (old split tables had no operator; use equality)
    conn.execute(
        """
        INSERT OR REPLACE INTO limit_tech_input_split
        (region, period, input_comm, tech, operator, proportion, notes)
        SELECT regions, periods, input_comm, tech, 'e', ti_split, ti_split_notes
        FROM src.TechInputSplit
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO limit_tech_input_split_annual
        (region, period, input_comm, tech, operator, proportion, notes)
        SELECT regions, periods, input_comm, tech, 'e', ti_split, ti_split_notes
        FROM src.TechInputSplitAverage
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO limit_tech_output_split
        (region, period, tech, output_comm, operator, proportion, notes)
        SELECT regions, periods, tech, output_comm, 'e', to_split, to_split_notes
        FROM src.TechOutputSplit
        """
    )

    # =========================================================================
    # UNLIMITED CAPACITY TECHNOLOGIES
    # =========================================================================
    # Certain technologies should be modeled as "unlimited capacity":
    #   - Import technologies (excluding water imports)
    #   - elec_distribution (pass-through)
    #   - unserved_load (penalty variable)
    #   - CO2_Offset, Dummy_Offset (if present)
    #
    # These techs:
    #   - Cannot have existing_capacity, cost_invest, cost_fixed, limit_capacity
    #   - Cannot overlap with tech_reserve
    #   - CAN have cost_variable
    #
    # NOTE: Patterns handle both prefixed (TRE_import_coal) and non-prefixed
    #       (import_coal) tech names using wildcards.
    # =========================================================================

    print('Setting unlimited capacity flags...')

    # Set unlim_cap = 1 for target technologies
    # Patterns use wildcards to match both:
    #   - Non-prefixed: "import_naturalgas", "elec_distribution"
    #   - Region-prefixed: "TRE_import_naturalgas", "TRE_elec_distribution"
    conn.execute(
        """
        UPDATE technology
        SET unlim_cap = 1
        WHERE (
            -- import_* or <REGION>_import_* (but NOT water_import_*)
            (tech LIKE 'import_%' OR tech LIKE '%_import_%')
            -- elec_distribution or <REGION>_elec_distribution
            OR tech LIKE '%elec_distribution'
            -- unserved_load or <REGION>_unserved_load
            OR tech LIKE '%unserved_load'
            -- CO2_Offset or <REGION>_CO2_Offset
            OR tech LIKE '%CO2_Offset'
            -- Dummy_Offset or <REGION>_Dummy_Offset
            OR tech LIKE '%Dummy_Offset'
        )
        AND tech NOT LIKE 'water_import_%'
        AND tech NOT LIKE '%_water_import_%'
        """
    )

    # tech_uncap and tech_reserve cannot overlap - fix any conflicts
    conn.execute(
        """
        UPDATE technology
        SET reserve = 0
        WHERE unlim_cap = 1 AND reserve = 1
        """
    )

    # Keep existing_capacity for tech_uncap techs.  The adjusted_capacity_constraint
    # now indexes ALL active_activity_rptv (including tech_uncap), creating equality
    # constraints that pin v_capacity = existing_capacity * PLF.  These equalities
    # act as separator nodes in the constraint graph, improving Cholesky fill-in
    # during barrier factorization (matching mip-dev's structure).

    # Report what was set
    unlim_techs = conn.execute(
        'SELECT tech FROM technology WHERE unlim_cap = 1 ORDER BY tech'
    ).fetchall()
    print(f'  Set unlim_cap = 1 for {len(unlim_techs)} technologies:')
    for (tech,) in unlim_techs:
        print(f'    - {tech}')

    # =========================================================================
    # TECHNOLOGY FLAG CORRECTIONS
    # =========================================================================
    # Fix incorrect flag assignments that were in the legacy database
    # =========================================================================

    print('Correcting technology flags...')

    # Biomass should NOT be curtailable (it's dispatchable, not variable renewable)
    conn.execute(
        """
        UPDATE technology SET curtail = 0 WHERE tech LIKE '%biomass%'
        """
    )
    biomass_fixed = conn.execute(
        "SELECT tech FROM technology WHERE tech LIKE '%biomass%'"
    ).fetchall()
    if biomass_fixed:
        print(f'  Set curtail = 0 for biomass techs: {[t[0] for t in biomass_fixed]}')

    # Transmission/exchange should NOT be in reserve (they transfer power, not provide reserve)
    conn.execute(
        """
        UPDATE technology SET reserve = 0
        WHERE exchange = 1 OR tech LIKE '%transmission%'
        """
    )
    transmission_fixed = conn.execute(
        "SELECT tech FROM technology WHERE exchange = 1 OR tech LIKE '%transmission%'"
    ).fetchall()
    if transmission_fixed:
        print(f'  Set reserve = 0 for transmission techs: {[t[0] for t in transmission_fixed]}')

    # Distributed generation should NOT be in reserve (uncontrolled, distributed resources)
    conn.execute(
        """
        UPDATE technology SET reserve = 0 WHERE tech LIKE '%distributed_generation%'
        """
    )
    dg_fixed = conn.execute(
        "SELECT tech FROM technology WHERE tech LIKE '%distributed_generation%'"
    ).fetchall()
    if dg_fixed:
        print(f'  Set reserve = 0 for distributed gen techs: {[t[0] for t in dg_fixed]}')

    # =========================================================================
    # POST-MIGRATION CLEANUP (for region-extracted source DBs)
    # =========================================================================
    # The source DB can contain orphan commodities/technologies after row-level
    # region filtering. Clean these so Temoa validation/build succeeds.
    # =========================================================================
    print('Running post-migration cleanup...')

    # capacity_credit is valid only for reserve techs.
    cc_to_delete = conn.execute(
        """
        SELECT COUNT(*) FROM capacity_credit
        WHERE tech IN (SELECT tech FROM technology WHERE reserve = 0)
        """
    ).fetchone()[0]
    if cc_to_delete:
        conn.execute(
            """
            DELETE FROM capacity_credit
            WHERE tech IN (SELECT tech FROM technology WHERE reserve = 0)
            """
        )
    print(f'  Deleted {cc_to_delete} capacity_credit rows for non-reserve techs')

    # unlim_cap techs cannot have investment/fixed costs.
    ci_to_delete = conn.execute(
        """
        SELECT COUNT(*) FROM cost_invest
        WHERE tech IN (SELECT tech FROM technology WHERE unlim_cap = 1)
        """
    ).fetchone()[0]
    if ci_to_delete:
        conn.execute(
            """
            DELETE FROM cost_invest
            WHERE tech IN (SELECT tech FROM technology WHERE unlim_cap = 1)
            """
        )
    print(f'  Deleted {ci_to_delete} cost_invest rows for unlim_cap techs')

    cf_to_delete = conn.execute(
        """
        SELECT COUNT(*) FROM cost_fixed
        WHERE tech IN (SELECT tech FROM technology WHERE unlim_cap = 1)
        """
    ).fetchone()[0]
    if cf_to_delete:
        conn.execute(
            """
            DELETE FROM cost_fixed
            WHERE tech IN (SELECT tech FROM technology WHERE unlim_cap = 1)
            """
        )
    print(f'  Deleted {cf_to_delete} cost_fixed rows for unlim_cap techs')

    # Remove orphan commodities (unused physical carriers).
    orphan_comm_query = """
        SELECT name FROM commodity
        WHERE name NOT IN (
            SELECT DISTINCT input_comm FROM efficiency
            UNION SELECT DISTINCT output_comm FROM efficiency
            UNION SELECT DISTINCT commodity FROM demand
            UNION SELECT DISTINCT emis_comm FROM emission_activity
            UNION SELECT DISTINCT demand_name FROM demand_specific_distribution
        )
    """
    orphan_comms = conn.execute(orphan_comm_query).fetchall()
    if orphan_comms:
        conn.execute(
            f'DELETE FROM commodity WHERE name IN ({",".join(["?"] * len(orphan_comms))})',
            [r[0] for r in orphan_comms],
        )
    print(f'  Deleted {len(orphan_comms)} orphan commodities')

    # Remove orphan technologies (not used in efficiency).
    orphan_tech_count = conn.execute(
        """
        SELECT COUNT(*) FROM technology
        WHERE tech NOT IN (SELECT DISTINCT tech FROM efficiency)
        """
    ).fetchone()[0]
    conn.execute('DROP TABLE IF EXISTS orphan_tech')
    conn.execute('CREATE TEMP TABLE orphan_tech (tech TEXT PRIMARY KEY)')
    conn.execute(
        """
        INSERT INTO orphan_tech (tech)
        SELECT tech FROM technology
        WHERE tech NOT IN (SELECT DISTINCT tech FROM efficiency)
        """
    )

    if orphan_tech_count:
        # Delete dependencies first so tech deletion is safe even if FK enforcement is on.
        tech_tables = [
            ('existing_capacity', 'tech'),
            ('cost_invest', 'tech'),
            ('cost_fixed', 'tech'),
            ('cost_variable', 'tech'),
            ('capacity_to_activity', 'tech'),
            ('capacity_credit', 'tech'),
            ('lifetime_tech', 'tech'),
            ('lifetime_process', 'tech'),
            ('loan_rate', 'tech'),
            ('loan_lifetime_process', 'tech'),
            ('emission_activity', 'tech'),
            ('storage_duration', 'tech'),
            ('ramp_up_hourly', 'tech'),
            ('ramp_down_hourly', 'tech'),
            ('capacity_factor_tech', 'tech'),
            ('capacity_factor_process', 'tech'),
            ('limit_annual_capacity_factor', 'tech'),
            ('limit_growth_capacity', 'tech_or_group'),
            ('limit_tech_input_split', 'tech'),
            ('limit_tech_input_split_annual', 'tech'),
            ('limit_tech_output_split', 'tech'),
            ('linked_tech', 'primary_tech'),
            ('linked_tech', 'driven_tech'),
            ('tech_group_member', 'tech'),
            ('rps_requirement', 'tech_group'),
        ]
        for table_name, column_name in tech_tables:
            conn.execute(
                f"""
                DELETE FROM [{table_name}]
                WHERE [{column_name}] IN (SELECT tech FROM orphan_tech)
                """
            )

        conn.execute('DELETE FROM technology WHERE tech IN (SELECT tech FROM orphan_tech)')
    print(f'  Deleted {orphan_tech_count} orphan technologies')
    conn.execute('DROP TABLE IF EXISTS orphan_tech')

    # Cleanup for objects tied to technologies/groups.
    tgm_to_delete = conn.execute(
        """
        SELECT COUNT(*) FROM tech_group_member
        WHERE tech NOT IN (SELECT tech FROM technology)
        """
    ).fetchone()[0]
    if tgm_to_delete:
        conn.execute(
            """
            DELETE FROM tech_group_member
            WHERE tech NOT IN (SELECT tech FROM technology)
            """
        )
    print(f'  Deleted {tgm_to_delete} orphan tech_group_member rows')

    tg_to_delete = conn.execute(
        """
        SELECT COUNT(*) FROM tech_group
        WHERE group_name NOT IN (SELECT DISTINCT group_name FROM tech_group_member)
        """
    ).fetchone()[0]
    if tg_to_delete:
        conn.execute(
            """
            DELETE FROM tech_group
            WHERE group_name NOT IN (SELECT DISTINCT group_name FROM tech_group_member)
            """
        )
    print(f'  Deleted {tg_to_delete} empty tech_group rows')

    linked_to_delete = conn.execute(
        """
        SELECT COUNT(*) FROM linked_tech
        WHERE primary_tech NOT IN (SELECT tech FROM technology)
           OR driven_tech NOT IN (SELECT tech FROM technology)
        """
    ).fetchone()[0]
    if linked_to_delete:
        conn.execute(
            """
            DELETE FROM linked_tech
            WHERE primary_tech NOT IN (SELECT tech FROM technology)
               OR driven_tech NOT IN (SELECT tech FROM technology)
            """
        )
    print(f'  Deleted {linked_to_delete} linked_tech rows with missing technologies')

    for table_name in ['limit_capacity', 'limit_new_capacity', 'limit_activity', 'limit_resource']:
        rows_to_delete = conn.execute(
            f"""
            SELECT COUNT(*) FROM [{table_name}]
            WHERE tech_or_group NOT IN (
                SELECT tech FROM technology
                UNION
                SELECT group_name FROM tech_group
            )
            """
        ).fetchone()[0]
        if rows_to_delete:
            conn.execute(
                f"""
                DELETE FROM [{table_name}]
                WHERE tech_or_group NOT IN (
                    SELECT tech FROM technology
                    UNION
                    SELECT group_name FROM tech_group
                )
                """
            )
        print(f'  Deleted {rows_to_delete} dangling rows from {table_name}')

    conn.commit()
    conn.execute('PRAGMA foreign_keys = ON;')
    fk_issues = conn.execute('PRAGMA foreign_key_check;').fetchall()
    if fk_issues:
        print('WARNING: foreign_key_check found issues:')
        for row in fk_issues[:20]:
            print('  ', row)
        if len(fk_issues) > 20:
            print(f'  ... {len(fk_issues) - 20} more')
    conn.execute('DETACH DATABASE src')
    conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Migrate legacy DB to Temoa v4 schema.')
    parser.add_argument(
        '--source',
        default='data_files/mip_migration_workspace/data_files/test_TRE_TREW_4week.sqlite',
        help='Path to source legacy sqlite DB',
    )
    parser.add_argument(
        '--schema',
        default='temoa/db_schema/temoa_schema_v4.sql',
        help='Path to v4 schema SQL file',
    )
    parser.add_argument(
        '--out',
        default='data_files/mip_migration_workspace/data_files/test_TRE_TREW_4week_v4.sqlite',
        help='Path to output migrated sqlite DB',
    )
    parser.add_argument(
        '--days-per-period',
        type=int,
        default=None,
        help='Days per period (e.g., 28 for 4-week, 364 for 52-week). Auto-detected if not specified.',
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = Path(args.source).resolve()
    schema = Path(args.schema).resolve()
    target = Path(args.out).resolve()

    target.parent.mkdir(parents=True, exist_ok=True)
    migrate(source=source, schema=schema, target=target, days_per_period=args.days_per_period)
    print(f'Migrated database written to: {target}')
    print(f'Size: {os.path.getsize(target)} bytes')


if __name__ == '__main__':
    main()
