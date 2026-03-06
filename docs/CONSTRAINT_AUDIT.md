# Constraint Audit: mip-dev vs v4 — Complete Mapping

**Date:** 2026-03-03
**Branch:** `feat/solver-tuning-experiments` (off `db-migration/mip-dev`)
**Verified against:** `reference/mip-dev/temoa_rules.py` and `temoa/components/*.py`

## Context

This document provides a complete, verified mapping of every constraint from mip-dev
(`reference/mip-dev/temoa_rules.py`) to v4 (`temoa/components/*.py`). It catalogs:
1. Which constraints map correctly (same math)
2. Which have known, intentional differences
3. Which have real mathematical differences that could affect results
4. What v4 features are unconditionally active and how they affect the LP
5. How the migration pipeline transforms mip-dev DB data

## Current Branch State

Key modifications on `feat/solver-tuning-experiments` that are NOT on `db-migration/mip-dev`:

| Change | Commit | Files | On db-migration/mip-dev? |
|---|---|---|---|
| `v_storage_init` chain anchor | `c9bbfd4` | `storage.py`, `model.py` | **NO** |
| Solver tuning env vars | earlier commits | `run_actions.py` | **NO** |

The `v_storage_init` change mirrors mip-dev's `V_StorageInit` — breaking closed storage
cycles into open chains. DIFF-5 (StorageInitConstraint) is partially addressed: the variable
exists and chain topology matches mip-dev, but the `StorageInitFrac`-based fixing constraint
is still missing (irrelevant — see DB query results below).

---

## Category 1: MATHEMATICALLY EQUIVALENT (33 constraints)

These produce identical LP rows/columns when survival curve and other v4-only tables are empty.

| # | mip-dev Constraint | v4 Location | Notes |
|---|---|---|---|
| 1 | `AdjustedCapacity_Constraint` | `capacity.py:adjusted_capacity_constraint` | mip-dev: `CAP = ECAP - retired`. v4: `CAP = PLF * (ECAP - retired/LSC)`. PLF absorbed into CAP, compensated by removing PLF from capacity_constraint. Net: same combined constraint. Survival curve benign when table empty. |
| 2 | `Capacity_Constraint` (timeslice) | `capacity.py:capacity_constraint` | mip-dev: `CFP * C2A * SEG * PLF * CAP >= activity`. v4: `CFP * C2A * SEG * CAP >= activity` (PLF in adjusted_capacity). Same combined result. |
| 3 | `CapacityAnnual_Constraint` | `capacity.py:capacity_annual_constraint` | mip-dev: `CF(=1) * C2A * PLF * CAP >= FOA`. v4: `C2A * CAP >= FOA` (PLF in CAP). Equivalent. |
| 4 | `CapacityAvailableByPeriodAndTech` | `capacity.py:capacity_available_by_period_and_tech_constraint` | mip-dev: `CAPAVL = sum(PLF * CAP)`. v4: `CAPAVL = sum(CAP)` (PLF already in CAP). Equivalent. |
| 5 | `RegionalExchangeCapacity` | `geography.py:regional_exchange_capacity_constraint` | Both: `CAP[r_e-r_i] == CAP[r_i-r_e]`. Identical. |
| 6 | `DemandConstraint` | `commodities.py:demand_constraint` | Both: `supply + supply_annual * SEG == Demand * DSD`. Math identical. |
| 7 | `CommodityBalance_Constraint` | `commodities.py:commodity_balance_constraint` | Core logic identical. v4 adds construction_input/end_of_life_output (zero when empty). v4 `commodity_waste` `>=` vs `==` benign when set empty. |
| 8 | `CommodityBalanceAnnual` | `commodities.py:annual_commodity_balance_constraint` | Same as #7 — core logic identical. |
| 9 | `BaseloadDiurnal_Constraint` | `operations.py:baseload_diurnal_constraint` | Both: `act_d * SEG[d_0] == act_d0 * SEG[d]`. Identical. |
| 10 | `StorageEnergy_Constraint` | `storage.py:storage_energy_constraint` | Both use V_StorageInit as chain anchor. First/last TOD: chain from/to SI. Middle: chain from SL[prev]. Identical for non-seasonal storage. |
| 11 | `StorageChargeRate` | `storage.py:storage_charge_rate_constraint` | PLF absorbed in v4. Equivalent. |
| 12 | `StorageDischargeRate` | `storage.py:storage_discharge_rate_constraint` | PLF absorbed. Equivalent. |
| 13 | `StorageThroughput` | `storage.py:storage_throughput_constraint` | PLF absorbed. Equivalent. |
| 14 | `LinkedEmissionsTech` | `emissions.py:linked_emissions_tech_constraint` | Both: `-sum(FO * EAC) == sum(FO_linked)`. v4 extends to handle tech_annual (superset). |
| 15 | `TechInputSplit_Constraint` | `limits.py:limit_tech_input_split_constraint` | Both: `inp >= split * total_inp`. Equivalent. |
| 16 | `TechInputSplitAnnual` | `limits.py:limit_tech_input_split_annual_constraint` | Equivalent. |
| 17 | `TechInputSplitAverage` | `limits.py:limit_tech_input_split_average_constraint` | Equivalent. |
| 18 | `TechOutputSplit_Constraint` | `limits.py:limit_tech_output_split_constraint` | Both: `out >= split * total_out`. Equivalent. |
| 19 | `TechOutputSplitAnnual` | `limits.py:limit_tech_output_split_annual_constraint` | Equivalent. |
| 20 | `MaxActivity_Constraint` | `limits.py:limit_activity_constraint` | Equivalent. |
| 21 | `MinActivity_Constraint` | `limits.py:limit_activity_constraint` | Equivalent. |
| 22 | `MaxCapacity_Constraint` | `limits.py:limit_capacity_constraint` | Equivalent. |
| 23 | `MinCapacity_Constraint` | `limits.py:limit_capacity_constraint` | Equivalent. |
| 24 | `MaxNewCapacity_Constraint` | `limits.py:limit_new_capacity_constraint` | Equivalent. |
| 25 | `MinNewCapacity_Constraint` | `limits.py:limit_new_capacity_constraint` | Equivalent. |
| 26 | `MaxResource_Constraint` | `limits.py:limit_resource_constraint` | Equivalent. |
| 27 | `MaxCapacityGroup` | `limits.py:limit_capacity_constraint` (group) | Equivalent. |
| 28 | `MinCapacityGroup` | `limits.py:limit_capacity_constraint` (group) | Equivalent. |
| 29 | `MaxActivityGroup` | `limits.py:limit_activity_constraint` (group) | Equivalent. |
| 30 | `MinActivityGroup` | `limits.py:limit_activity_constraint` (group) | **See DIFF-6** — v4 omits `MinGenGroupWeight`. **INACTIVE in national DB** (table doesn't exist). |
| 31 | `GrowthRateConstraint` | `limits.py:limit_growth_capacity_constraint_rule` | Equivalent. |
| 32 | `MinAnnualCapacityFactor` | `limits.py:limit_annual_capacity_factor_constraint` | Equivalent. |
| 33 | `MaxAnnualCapacityFactor` | `limits.py:limit_annual_capacity_factor_constraint` | Equivalent. |

---

## RPS/CES (Energy Standard Requirements) — Detailed Mapping

The RPS/CES is implemented identically in both codebases, but through differently-named tables:

| Aspect | mip-dev (v3) | v4 |
|---|---|---|
| Constraint function | `MinActivityGroup_Constraint` | `limit_activity_constraint` |
| Data table | `MinActivityGroup` (23 rows, 13 ESR groups) | `limit_activity` with `operator='ge'` and `notes='RPS'` |
| Group membership | `tech_groups` (region, group_name, tech) | `tech_group_member` (group_name, tech) — no region column |
| Group resolution | Filters by region in constraint loop | `gather_group_techs()` returns all techs; constraint iterates over region group |
| Migration | N/A | `migrate_to_v4.py:511-512` copies MinActivityGroup → limit_activity |

**Verification:** Programmatic check confirmed zero overcounting and zero undercounting across
all 16 ESR groups. Despite v4's region-agnostic group membership, techs only exist in regions
where they have Efficiency data, so `process_vintages` returns empty for non-existent
region+tech pairs. Net result: identical constraint sums.

**ESR groups in national DB:** ESR_1 through ESR_16 (13 have MinActivityGroup targets, 3 are
defined but unused). Cover regional renewable portfolio standards with absolute GWh targets.
None cover TRE/TREW (which is why the 4-week Texas comparison doesn't exercise RPS).

v4 also has a deprecated `rps_requirement` table (for percentage-based RPS via
`renewable_portfolio_standard_constraint`), but this is empty and unused in migrated DBs.

---

## Category 2: INTENTIONAL / KNOWN DIFFERENCES (validated)

| # | Difference | mip-dev | v4 | Impact | Status |
|---|---|---|---|---|---|
| A | Demand tech flow variables | `V_FlowOutAnnual` for demand techs | `v_flow_out` only (timeslice) | Prevents dense columns / 300x barrier slowdown | **VALIDATED** |
| B | DemandActivity constraint | COMMENTED OUT | REMOVED ENTIRELY | Both disabled | **EQUIVALENT** |
| C | ReserveMargin constraint | COMMENTED OUT | Present, gated on empty table | Disabled via empty `planning_reserve_margin` | **EQUIVALENT** |
| D | v_storage_init variable | Present (`V_StorageInit`) | Present (`v_storage_init`) | Same chain topology | **EQUIVALENT** |
| E | Survival curves | Not present | `lifetime_survival_curve` param | Disabled when table empty | **BENIGN** |
| F | Seasonal storage | Not present | Full constraint set | Never activates without data | **BENIGN** |
| G | Construction/EOL flows | Not present | In commodity balance | Zero when tables empty | **BENIGN** |

---

## Category 3: REAL MATHEMATICAL DIFFERENCES

### DIFF-1: StorageEnergyUpperBound formula

**Files:** `storage.py:270-324` vs `temoa_rules.py:975-1018`

**mip-dev:** Bound VARIES by time-of-day:
```
SL[r,p,s,d,t,v] <= CAP * StorageDuration * SegFrac[p,s,d] * 8760
```

**v4:** Bound is UNIFORM across TODs within a season:
```
SL[r,p,s,d,t,v] <= CAP * C2A * SD/24 * SegFracPerSeason[p,s]
```

**Implication:** Storage energy capacity shouldn't physically depend on time-of-day. v4 is
arguably more correct. The upper bound is rarely binding (charge/discharge rates dominate).

**Risk:** LOW — storage is a small fraction of total capacity.

---

### DIFF-2: Emission limit — Flex/Curtailment accounting

**Files:** `limits.py:796-897` vs `temoa_rules.py:1530-1639`

mip-dev adds `V_Flex * EAC` and `V_Curtailment * EAC` terms. v4 omits them, noting flex
is already accounted in FlowOut and curtailed flows are just accounting.

**DB check:** No curtailment techs have EmissionActivity entries in the national DB.

**Risk:** NONE with our data. **INACTIVE.**

---

### DIFF-3: Ramping formulation differs — **ACTIVE**

**Files:** `operations.py:239-593` vs `temoa_rules.py:1172-1457`

**mip-dev (day ramp):**
```
(act_d / SegFrac_d - act_prev / SegFrac_prev) / C2A <= RampUp * CAP
```
- Normalizes by SegFrac and C2A
- Season ramping: COMMENTED OUT
- Period ramping: Returns Constraint.Skip

**v4 (day ramp):**
```
(act_next / hours_next - act_d / hours_d) <= ramp_fraction * CAP * C2A
where hours = SegFrac * DPP * 24
ramp_fraction = hours_elapsed * ramp_up_hourly
hours_elapsed = 12 * (SegFrac_d/SFPS_s + SegFrac_next/SFPS_s_next)
```
- Physically motivated elapsed-time calculation
- Season ramping: ACTIVE (when `time_sequencing != 'consecutive_days'`)
- Skips when `ramp_fraction >= 1` (non-binding)

**DB check (national):** 229 rows in RampUp/RampDown. 16 techs in TRE/TREW alone:
- Coal (0.57 ramp rate): `conventional_steam_coal_1`, `conventional_steam_coal_2`
- Gas CC/CT (0.64): 8 techs including hydrogen and CCS variants
- Nuclear (0.25): `nuclear_1`, `nuclear_nuclear_moderate_0`

**Additional v4 difference:** Season ramp constraints are ACTIVE in v4 (all our configs use
`time_sequencing = 'seasonal_timeslices'`). mip-dev has them commented out. This means v4
enforces ramp limits at season boundaries that mip-dev does not.

**Impact assessment:** The within-day formulation differs in normalization math but produces
similar constraint tightness. The season-boundary ramp is strictly additional in v4. Given
the validated 4-week Texas comparison showed <0.06pp generation differences, the practical
impact is small, but this is the ONLY structurally active difference between the codebases.

**Risk:** MEDIUM — the only real active difference. Worth monitoring but validated results
show negligible impact.

---

### DIFF-4: RetiredCapacity per-period bound missing in v4

mip-dev explicitly bounds per-period retirement to available capacity:
```
V_RetiredCapacity[r,p,t,v] <= V_Capacity[r,p-1,t,v]
```

v4 relies on cumulative nonnegativity. The solver would never choose to over-retire.

**Risk:** VERY LOW.

---

### DIFF-5: StorageInitFrac fixing constraint missing in v4

mip-dev has `StorageInit_Constraint` gated on `StorageInitFrac` parameter.

**DB check:** `StorageInitFrac` table does NOT EXIST in the national DB.

**Risk:** NONE — **INACTIVE.**

---

### DIFF-6: MinActivityGroup missing MinGenGroupWeight

mip-dev multiplies annual tech flows by `MinGenGroupWeight[r, t, g]` in the min activity
group constraint. v4 sums annual flows without weighting.

**DB check:** `MinGenGroupWeight` table does NOT EXIST in the national DB.

**Risk:** NONE — **INACTIVE.**

---

## Category 4: DISABLED IN BOTH

| Constraint | mip-dev | v4 |
|---|---|---|
| `DemandActivityConstraint` | Commented out | Removed |
| `ReserveMarginConstraint` | Commented out | Gated on empty table |
| `RampUpConstraintSeason` | Commented out | **Active in v4** (see DIFF-3) |
| `RampDownConstraintSeason` | Commented out | **Active in v4** (see DIFF-3) |
| `RampUpConstraintPeriod` | Returns Constraint.Skip | Not present |
| `RampDownConstraintPeriod` | Returns Constraint.Skip | Not present |

---

## Category 5: V4-ONLY CONSTRAINTS (data-gated, benign)

These only activate when corresponding database tables are populated:

| Constraint | Trigger |
|---|---|
| `annual_retirement_constraint` | Retirement periods exist |
| `seasonal_storage_energy_constraint` + upper bound | `tech_seasonal_storage` |
| `limit_storage_fraction_constraint` | `limit_storage_fraction` |
| `limit_activity_share_constraint` | `limit_activity_share` |
| `limit_capacity_share_constraint` | `limit_capacity_share` |
| `limit_new_capacity_share_constraint` | `limit_new_capacity_share` |
| `limit_seasonal_capacity_factor_constraint` | `limit_seasonal_capacity_factor` |
| `limit_growth_new_capacity_delta` (both) | `limit_growth_new_capacity_delta` |
| `limit_degrowth_capacity_constraint` | degrowth rate |
| `limit_tech_output_split_average_constraint` | `output_split_annual_vintages` |
| `renewable_portfolio_standard_constraint` | RPS table |

---

## FORCED V4 FEATURES & MIGRATION PIPELINE

### FORCED-1: tech_uncap (Unlimited Capacity Techs)

Migration script (`migrate_to_v4.py:607-641`) auto-flags techs by name pattern and deletes
their existing_capacity rows.

**National DB verification (49 techs flagged):**

| Category | Count | Examples |
|---|---|---|
| `import_*` | 44 | Regional fuel imports |
| `elec_distribution` | 1 | |
| `unserved_load` | 1 | |
| `CO2_Offset` | 1 | |
| `Dummy_Offset` | 1 | |

No unexpected techs flagged. `water_import_conventional_hydroelectric_1` correctly excluded.
`distributed_generation_1` correctly has `unlim_cap = 0`.

**Impact:** Functionally equivalent to mip-dev's 999,999 MW caps. Slightly better LP
conditioning (removes large coefficients).

### FORCED-2: process_life_frac

PLF absorbed into `adjusted_capacity_constraint` instead of `capacity_constraint`.
Net combined effect identical. **No LP impact.**

### FORCED-3: Migration Re-infers Commodity and Tech Flags

**National DB verification:**
- `ethos` correctly flagged `s` (source) — only true source commodity
- Reference fuels correctly flagged `p` (physical/intermediate)
- `CO2` correctly flagged `e` (emission)
- 4 demand commodities: `DEMAND_ELC`, `DEMAND_CRYPTO`, `DEMAND_SERVERS`, `Dummy_CO2_Offset_Demand`
- No flag discrepancies from mip-dev categorization

**Additional migration actions verified:**
- Biomass techs: `curtail` forced to 0
- Transmission/exchange and distributed gen: `reserve` forced to 0
- `capacity_credit`: all 4,698 rows belong to reserve-flagged techs (212 techs). Zero rows dropped.
- Zero `cost_invest`/`cost_fixed` rows remain for `unlim_cap` techs

### FORCED-4: commodity_waste

v4 introduces `>=` for waste commodities. **No waste commodities in our migrated DB.
Zero impact.**

---

## OBJECTIVE FUNCTION

Cost formulation differs substantially (survival curves, emission costs, embodied/EOL,
discounting). Produces documented ~2% objective difference — **expected and acceptable**
per user directive.

---

## SUMMARY

### Active Differences with National DB

| DIFF | Description | Status | Risk |
|---|---|---|---|
| DIFF-1 | StorageEnergyUpperBound: TOD-varying vs uniform | Active (storage data exists) | LOW |
| DIFF-2 | Emission flex/curtailment accounting | **INACTIVE** (no curtailment + emissions) | NONE |
| DIFF-3 | **Ramping formulation + season ramp** | **ACTIVE** (229 rows, 16 TRE/TREW techs) | MEDIUM |
| DIFF-4 | RetiredCapacity per-period bound | Active (theoretical only) | VERY LOW |
| DIFF-5 | StorageInitFrac fixing constraint | **INACTIVE** (no table) | NONE |
| DIFF-6 | MinGenGroupWeight multiplier | **INACTIVE** (no table) | NONE |

**Bottom line:** DIFF-3 (ramping) is the ONLY structurally meaningful active difference.
The within-day formulation math differs, and v4 adds season-boundary ramp constraints that
mip-dev doesn't have. Despite this, validated 4-week Texas comparisons show <0.06pp
generation share differences, indicating the practical impact is negligible.

### Forced V4 Features

| Feature | Impact | Verified |
|---|---|---|
| tech_uncap (49 techs) | Functionally equivalent, better conditioning | Yes — all expected |
| process_life_frac | No LP impact | N/A |
| Commodity/tech flag re-inference | Correct assignment | Yes — matches mip-dev |
| commodity_waste | Not populated | N/A |

### Recommended Cherry-picks to energysystem

**Ready:**
- Demand formulation fix (commit `39b2b2e` on `db-migration/mip-dev`)
- BarOrder=0 (commit `b50c73b` on `db-migration/mip-dev`)
- v_storage_init (commit `c9bbfd4` on `feat/solver-tuning-experiments`)

**No action needed:**
- DIFF-3 (ramping): Different but results validate. v4's formulation is physically better.
- DIFF-6 (MinGenGroupWeight): Table doesn't exist in national DB.
