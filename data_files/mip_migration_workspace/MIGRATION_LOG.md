# 4-Week DB Migration Log (Legacy -> Temoa v4)

## Scope
- Source DB: `data_files/mip_migration_workspace/data_files/test_TRE_TREW_4week.sqlite`
- Target DB: `data_files/mip_migration_workspace/data_files/test_TRE_TREW_4week_v4.sqlite`
- Goal: Build successfully on current Temoa (`build_only`) without modifying Temoa code.

## Artifacts Created
- Migration script: `data_files/mip_migration_workspace/migrate_to_v4.py`
- Run config: `data_files/mip_migration_workspace/config_4week_test.toml`
- Migrated DB: `data_files/mip_migration_workspace/data_files/test_TRE_TREW_4week_v4.sqlite`

## Environment Setup
- Created local Python 3.12 environment: `.venv312`
- Installed Temoa in editable mode in `.venv312`
- Installed `gurobipy` and verified license:
  - Academic license recognized
  - Gurobi version: `13.0.1`

## Core Migration Decisions

### 1) Versioning and metadata
- Wrote v4 metadata explicitly:
  - `DB_MAJOR = 4`
  - `DB_MINOR = 0`
  - `days_per_period = 28` (January 4-week test case)
- Set `metadata_real`:
  - `global_discount_rate` from legacy `GlobalDiscountRate.rate` (`0.02`)
  - `default_loan_rate = 0.05`

### 2) Time structure mapping
- `time_periods -> time_period` with generated `sequence`
- `time_of_day -> time_of_day` with generated `sequence` (natural ordering, `h1..h168`)
- `time_seasons_per_period -> time_season` with generated per-period `sequence`
- `SegFrac -> time_segment_fraction`

### 3) Commodity mapping
- `commodities -> commodity` with flag logic:
  - demand commodities remain `d`
  - inferred source commodities marked `s` (input-only in network)
  - remaining physical commodities marked `p`
- Added missing referenced commodities (not present in legacy `commodities`) by scanning:
  - `Efficiency` inputs/outputs
  - `Demand`
  - `EmissionActivity` / `EmissionLimit`
- Emission-only commodities (e.g. `CO2`) inserted with `flag='e'`

### 4) Technology mapping
- `technologies -> technology`
  - mapped `tech`, `flag`, `sector`, `category`, `description`
- Consolidated legacy feature tables into v4 boolean columns:
  - `tech_curtailment -> curtail`
  - `tech_reserve -> reserve`
  - `tech_exchange -> exchange`
  - `tech_annual -> annual`
  - `tech_flex -> flex`
  - `tech_retirement -> retire`

### 5) Capacity factor handling
- Legacy `CapacityFactorTech` lacked period index.
- Expanded into v4 `capacity_factor_tech` by duplicating over periods present in `time_seasons_per_period`.
- `CapacityFactorProcess` mapped directly (period already present).

### 6) Constraint consolidation
- Merged legacy min/max tables into v4 `limit_*` tables with explicit `operator`:
  - max -> `le`
  - min -> `ge`
- Mapped:
  - capacity, new capacity, activity, resource, emissions, annual CF
- Group constraints mapped to `limit_capacity` / `limit_activity` using group names.
- Split constraints mapped with `operator='e'`.

### 7) Other key mappings
- `LifetimeLoanTech -> loan_lifetime_process` by expanding over vintages in `CostInvest`
- `groups -> tech_group`
- `tech_groups -> tech_group_member` (`SELECT DISTINCT` after dropping region dimension)
- `LinkedTechs -> linked_tech`
- Standard cost/demand/efficiency/lifetime/ramping/storage tables mapped directly with column renames.

## Issues Encountered and Resolutions

### Issue A: `consecutive_days` sequencing failure
- Error: consecutive seasons had different implied `num_days` from segment fractions.
- Resolution: switched config to `time_sequencing = "seasonal_timeslices"` for this reduced January test DB.

### Issue B: `capacity_credit` index invalid
- Error: `capacity_credit` entries referenced techs not in model `tech_reserve` set.
- Root cause: initial migration accidentally left all technology reserve flags as 0 due attached-table existence check bug.
- Resolution:
  1. fixed flag-table loader to query attached source tables directly (try/except on query)
  2. filtered `capacity_credit` insert to techs in legacy `tech_reserve`
  3. re-migrated DB

### Issue C: FK failure on `emission_activity`
- Error: missing commodity reference for `CO2`.
- Resolution: auto-add missing referenced commodities and assign `flag='e'` where appropriate.

## Build Verification
- Command used:
  - `MPLCONFIGDIR=.mplconfig .venv312/bin/temoa run data_files/mip_migration_workspace/config_4week_test.toml --build-only --silent`
- Result: success (exit code 0)

## Final Integrity Checks
- `PRAGMA foreign_key_check;` -> no violations
- Metadata:
  - `DB_MAJOR=4`, `DB_MINOR=0`, `days_per_period=28`
- Basic row counts:
  - `technology`: 74
  - `commodity`: 13
  - `capacity_factor_tech`: 36,288
  - `demand_specific_distribution`: 2,688

## Post-Migration: Unlimited Capacity Technologies

### Background
Certain technologies should be modeled as "unlimited capacity" (`unlim_cap = 1`) in Temoa v4. These are technologies that:
- Represent external resource imports (fuel imports, etc.)
- Are pass-through/distribution technologies
- Serve as penalty/slack variables (unserved load)

### What `unlim_cap = 1` Means
- Technology has **no capacity variables** (`v_capacity`, `v_new_capacity`)
- **Cannot have** investment costs (`cost_invest`) or fixed costs (`cost_fixed`)
- **Cannot appear in** capacity-related tables:
  - `existing_capacity`
  - `limit_capacity`
  - `capacity_factor_process`
  - `construction_input`
  - `end_of_life_output`
  - `emission_embodied`
  - `emission_end_of_life`
- **CAN have** variable costs (`cost_variable`) - must cover all optimization periods if present
- **Cannot overlap** with `tech_reserve` (mutually exclusive sets)
- Activity flows are still tracked normally

### Technologies to Set as `unlim_cap`
Based on our analysis, the following technology patterns should be set to `unlim_cap = 1`:

| Pattern | Description | Notes |
|---------|-------------|-------|
| `import_%` (excluding `water_import_%`) | Fuel/resource imports | Water imports remain normal techs |
| `elec_distribution` | Pass-through for electricity demand | Must also set `reserve = 0` |
| `unserved_load` | Penalty variable for unmet demand | |
| `CO2_Offset` | Carbon offset (if present) | |
| `Dummy_Offset` | Placeholder offset (if present) | |

### Technology Flag Corrections
The following flag corrections are applied automatically during migration:

| Pattern | Flag | Set To | Reason |
|---------|------|--------|--------|
| `%biomass%` | `curtail` | 0 | Biomass is dispatchable, not a variable renewable |
| `exchange = 1` OR `%transmission%` | `reserve` | 0 | Transmission transfers power, doesn't provide reserve capacity |
| `%distributed_generation%` | `reserve` | 0 | Distributed resources are uncontrolled, can't provide reserve |

### `capacity_credit` Cleanup
When setting `reserve = 0` for technologies, their `capacity_credit` entries must also be deleted. The `capacity_credit` parameter is indexed only over technologies in `tech_reserve`. If a tech has `reserve = 0`, any existing `capacity_credit` rows will cause a `KeyError` at model build time.

### SQL Script for Application
See: `data_files/mip_migration_workspace/set_unlim_cap.sql`

### Changes Applied to 4-Week Test DB
1. Set `unlim_cap = 1` for 8 technologies
2. Set `reserve = 0` for `elec_distribution` (was `reserve = 1`, conflict with `tech_uncap`)
3. Deleted 14 rows from `existing_capacity` for these techs

### Verification
After applying changes, run `temoa run <config> --build-only` to verify the model builds without errors.

---

## Post-Migration: `capacity_to_activity` Scaling

### Issue
For reduced time-horizon databases (e.g., 4-week instead of full year), the `capacity_to_activity` values must be scaled to match the actual modeled time period.

### What Happened
- Original database had `c2a = 8760` (full year hours: 365 × 24)
- Our 4-week database only models 28 days = 672 hours
- This caused renewables to appear ~13× larger than they should be relative to demand
- Result: Unrealistic output (zero thermal generation, 100% renewables)

### Fix
Update `capacity_to_activity` values: `c2a = days_per_period × 24`
- For 4-week: `c2a = 672`
- For 52-week: `c2a = 8760`

---

## CRITICAL: Creating a Time-Subset Database (e.g., 4-week from 52-week)

When creating a subset database that models only a portion of the year (e.g., first 4 weeks from a 52-week database), **ALL of the following must be adjusted**:

### Required Adjustments Checklist

| Parameter | What to do | Formula/Notes |
|-----------|-----------|---------------|
| `days_per_period` | Set to actual days modeled | 28 for 4-week |
| `capacity_to_activity` | Scale to match hours | `days_per_period × 24` (672 for 4-week) |
| `time_segment_fraction` | **Rescale to sum to 1.0** | Divide each value by current sum, OR multiply by `(total_seasons / kept_seasons)` |
| `demand_specific_distribution` | **Rescale to sum to 1.0** | Divide each value by current sum for each (region, period, demand_name) |
| `demand` | Set to actual demand for kept time slices | `annual_demand × SUM(original_DSD for kept seasons)` |
| Delete rows | Remove data for deleted seasons | From: `time_season`, `time_segment_fraction`, `demand_specific_distribution`, `CapacityFactorTech`, `CapacityFactorProcess`, etc. |

### Why Each Matters

1. **`time_segment_fraction` must sum to 1.0** - Temoa validates this on startup. Each value represents a fraction of the modeled year.

2. **`demand_specific_distribution` must sum to 1.0** - This distributes annual demand across time slices. If it doesn't sum to 1.0, demand won't be fully served or will be over-served.

3. **`demand` must reflect actual demand for kept periods** - Don't just scale by `kept_days/365`. Calculate from the original `DemandSpecificDistribution`:
   ```sql
   new_demand = annual_demand × SUM(DSD for kept seasons)
   ```

4. **`capacity_to_activity` must match `days_per_period`** - This converts capacity (GW) to activity (GWh). Wrong values make capacity appear too large or too small relative to demand.

### Example: 4-week subset from 52-week database

```python
# After deleting seasons p5-p52:

# 1. Rescale time_segment_fraction to sum to 1.0
conn.execute('''
    UPDATE time_segment_fraction
    SET segment_fraction = segment_fraction * 13.0
''')  -- 52/4 = 13

# 2. Rescale demand_specific_distribution to sum to 1.0 per (region, period, demand)
# First get current sums, then divide each row by its group's sum
for (region, period, demand_name), current_sum in group_sums.items():
    conn.execute('''
        UPDATE demand_specific_distribution
        SET dsd = dsd / ?
        WHERE region = ? AND period = ? AND demand_name = ?
    ''', (current_sum, region, period, demand_name))

# 3. Set demand to actual first-4-weeks demand
# Calculate from original: demand = annual_demand × SUM(original DSD for p1-p4)
conn.execute('''
    UPDATE demand SET demand = ?
    WHERE region = ? AND period = ? AND commodity = ?
''', (annual_demand * dsd_fraction_for_kept_seasons, ...))

# 4. Set c2a = 672 (28 days × 24 hours)
conn.execute('UPDATE capacity_to_activity SET c2a = 672.0')

# 5. Set days_per_period = 28
conn.execute("UPDATE metadata SET value = 28 WHERE element = 'days_per_period'")
```

### Verification Before Running Temoa

```sql
-- All must pass:
SELECT period, SUM(segment_fraction) FROM time_segment_fraction GROUP BY period;
-- Expected: 1.0 for each period

SELECT region, period, demand_name, SUM(dsd) FROM demand_specific_distribution
GROUP BY region, period, demand_name;
-- Expected: 1.0 for each combination

SELECT value FROM metadata WHERE element = 'days_per_period';
-- Expected: 28 (for 4-week)

SELECT DISTINCT c2a FROM capacity_to_activity;
-- Expected: 672.0 (for 4-week)

PRAGMA foreign_key_check;
-- Expected: no results (no FK violations)
```

---

## Post-Migration: Strip Region Prefixes from Tech Names

### Background
The legacy database uses region-prefixed technology names (e.g., `TRE_onshore_wind_turbine_1`). This is redundant because all data tables use `(region, tech)` composite keys.

### Benefits of Stripping Prefixes
1. **Cleaner tech names**: `onshore_wind_turbine_1` instead of `TRE_onshore_wind_turbine_1`
2. **Simpler tech groups**: One `ONSHORE_WIND` group works for all regions
3. **Multi-region constraints work**: `TRE+TREW` constraints can reference techs that exist in both regions
4. **Reduced tech count**: 74 region-prefixed techs → 47 base techs (in TRE/TREW subset)

### Script
Use `strip_region_prefixes.py` to strip prefixes:
```bash
python strip_region_prefixes.py input.sqlite output.sqlite
```

### Verification
- Confirmed zero flag conflicts across all 26 regions in full database
- Confirmed zero PK violations after stripping
- Test 06 (stripped baseline): Matches original baseline cost ($27.34B)
- Test 07 (stripped + multi-region constraints): Successfully applied `TRE+TREW` capacity group constraint

---

## Temoa v4 Bug Identified

### Bug: `limit_capacity_constraint` Missing Index Check

**Location**: `temoa/components/limits.py`, line 1386

**Problem**: When using tech groups with multi-region constraints (e.g., `TRE+TREW`), the constraint tries to access capacity variables for technologies that don't exist in all regions, causing `KeyError`.

**Fix**: Add `if (_r, p, _t) in model.process_vintages` check (same pattern used in `limit_capacity_share_constraint`).

**Workaround**: Strip region prefixes from tech names so techs exist in all regions.

**See**: `TEMOA_BUG_AND_NAMING_ANALYSIS.md` for full analysis and bug report draft.

---

## Notes for Reuse on Other DBs
- Keep the migration script explicit and table-by-table.
- Always validate:
  1. commodity flags (`s/d/p/e`)
  2. technology feature flags (`reserve`, `curtail`, etc.)
  3. period-index completeness for `capacity_factor_tech`
  4. `limit_*` operator direction (`le` vs `ge`)
  5. time sequencing compatibility with segment fractions
  6. **`unlim_cap` settings** - apply using `set_unlim_cap.sql` after migration
  7. **`capacity_to_activity`** - scale to match `days_per_period`
  8. **Strip region prefixes** - use `strip_region_prefixes.py` for cleaner tech names
  9. **Time subsetting** - if creating a subset (e.g., 4-week from 52-week), see "CRITICAL: Creating a Time-Subset Database" section above. Must adjust: `days_per_period`, `c2a`, `time_segment_fraction`, `demand_specific_distribution`, and `demand`.

## Script Compatibility

**Order of operations:** After running `migrate_to_v4.py`, the post-processing scripts
can be run in either order:

| Script | Input | Works with prefixed techs? | Works with non-prefixed techs? |
|--------|-------|---------------------------|-------------------------------|
| `set_unlim_cap.sql` | v4 database | ✅ Yes (uses `%` wildcards) | ✅ Yes |
| `strip_region_prefixes.py` | v4 database | ✅ Yes (strips them) | ✅ Yes (no-op) |

The `set_unlim_cap.sql` script was updated to use `%` wildcard patterns that match both:
- Region-prefixed: `TRE_import_coal`, `TREW_elec_distribution`
- Non-prefixed: `import_coal`, `elec_distribution`

---

## Final Test Results

| Test | Description | Result | Cost |
|------|-------------|--------|------|
| Baseline | Original v4 migration | ✅ Pass | $27.34B |
| Test 01 | Baseline (no new constraints) | ✅ Pass | $27.34B |
| Test 02 | Capacity group (single-region) | ✅ Pass | - |
| Test 03 | Activity share (RPS) | ✅ Pass | $33.73B |
| Test 04 | Emission limit (CO2 cap) | ✅ Pass | $27.34B |
| Test 05 | Multi-region (pre-strip) | ❌ Fail | KeyError |
| Test 06 | Stripped prefixes baseline | ✅ Pass | $27.34B |
| Test 07 | Stripped + multi-region | ✅ Pass | $38.82B |

All constraint types from the original database are now validated.

---

## Full 26-Region 52-Week Conversion (2026-02-12)

**Source:** `server_current_policies_noIRA_52_week_retire_HighGasCapex.sqlite`
**Run folder:** `data_files/mip_migration_workspace/runs/full_db_20260212_142635/`**Commands:**
```bash
python3 migrate_to_v4.py --source "<full_source_path>" --out "<run_dir>/full_all_regions_v4.sqlite" --days-per-period 364
echo y | temoa run <run_dir>/config_full.toml --build-only
```**Results:** Migration completed; constraint parity verified; build-only run manually (full model is large). See `MIGRATION_REPORT.md` and `CONSTRAINT_PARITY_REPORT.md` in run folder. Prefix stripping skipped on full DB (timeout/FK issues); use prefixed artifact for build.
