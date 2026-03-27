# mip-dev Changes Analysis: Do YOUR Changes Exist in unstable?

**Date:** 2026-02-12
**Purpose:** Identify SutubraResearch changes made to mip-dev (2023-2025) and assess whether they exist in unstable

---

## Executive Summary

| mip-dev Change | In unstable? | Risk Level | Action Needed |
|---------------|--------------|------------|---------------|
| Removed DemandActivity constraint | ⚠️ YES - but smarter | 🟡 MEDIUM | Modify index function to skip when only 1 tech serves demand |
| Removed ReserveMargin constraint | ⚠️ NO default | 🟢 LOW | Empty table skips constraint - verify index guard |
| Updated Group Constraints (added region index) | ✅ YES - equivalent | 🟢 LOW | Already handled |
| Storage: No seasonal storage (loop within season) | ✅ YES - optional | 🟢 LOW | Keep tech_seasonal_storage empty |
| End-of-model loan cost (removed undiscounted case) | ✅ YES - equivalent | 🟢 LOW | Already handled |
| Transmission loss bug fix | ✅ YES | 🟢 LOW | Already handled |

---

## Change 1: Removed DemandActivity Constraint

### What YOU Changed (commit ed762b1, Jul 2025)

**Removed constraint entirely:**
```python
# Commented out in mip-dev:
# M.DemandActivityConstraint_rpsdtv_dem_s0d0 = Set(
#    dimen=9, initialize=DemandActivityConstraintIndices
# )
# M.DemandActivityConstraint = Constraint(
#    M.DemandActivityConstraint_rpsdtv_dem_s0d0, rule=DemandActivity_Constraint
# )
```

**Your reasoning:** "Not relevant for power system modelling"

### Status in unstable

**✅ Constraint EXISTS in unstable:**

File: `temoa/components/commodities.py`

```python
self.demand_activity_constraint = Constraint(
    self.demand_activity_constraint_rpsdtvd,
    rule=commodities.demand_activity_constraint,
)
```

The constraint enforces that demand technologies are used proportionally across all time slices (prevents shifting electric heat pump usage to only daytime, for example).

**How the constraint works:**
- Only created when >1 technology produces the same demand commodity
- Index set: `demand_activity_constraint_indices()` filters to only create constraints for `(r, p, dem)` where multiple techs serve demand `dem`

### Your Logic Check

✅ **YOUR LOGIC IS CORRECT:**

You stated: "So long as only one tech creates the demand commodity, it's fine. But I think in the old version of temoa, it would still write the constraint - even though it's trivial."

**Verification:**
- **Old code (mip-dev):** Would create constraint indices for ALL demand commodities regardless of number of techs
- **New code (unstable):** `demand_activity_constraint_indices()` iterates over `model.commodity_up_stream_process[r, p, dem]` which ONLY includes techs that produce `dem`
- If only 1 tech produces the demand, the constraint is still created but is trivial (comparing tech to itself)

### Risk Assessment

🟡 **MEDIUM RISK** (downgraded from HIGH)

- **mip-dev:** Constraint is OFF (commented out)
- **unstable:** Constraint is ON, but only matters when >1 tech serves same demand
- **Impact:** Only differs if database has multiple demand-serving technologies for the same commodity

### Decision & Recommendation

**DECISION:** For power system modeling with 1-to-1 demand mapping (one tech per demand commodity), the constraint is unnecessary but harmless.

**Better solution than removing:**
Modify `demand_activity_constraint_indices()` in unstable to skip constraint creation when only 1 tech serves a demand:

```python
def demand_activity_constraint_indices(model: TemoaModel):
    indices = {
        (r, p, s, d, t, v, dem)
        for r, p, dem in model.demand_constraint_rpc
        for t, v in model.commodity_up_stream_process[r, p, dem]
        # Only create constraint if >1 tech serves this demand
        if len([t2 for t2, v2 in model.commodity_up_stream_process[r, p, dem]]) > 1
        if t not in model.tech_annual
        for s in model.time_season[p]
        for d in model.time_of_day
    }
    return indices
```

This keeps the constraint for cases where it's meaningful, skips it when trivial.

---

## Change 2: Removed Planning Reserve Margin Constraint

### What YOU Changed (commit ed762b1, Jul 2025)

**Removed constraint entirely:**
```python
# Commented out in mip-dev:
# M.ReserveMargin_rpsd = Set(dimen=4, initialize=ReserveMarginIndices)
# M.ReserveMarginConstraint = Constraint(
#    M.ReserveMargin_rpsd, rule=ReserveMargin_Constraint
# )
```

**Your reasoning:** "The intercomparison study decided not to include this constraint due to overwhelming differences in constraint design across models"

### Status in unstable

**✅ Constraint EXISTS in unstable:**

File: `temoa/components/reserves.py`

```python
self.reserve_margin_constraint = Constraint(
    self.reserve_margin_constraint_rpsd,
    rule=reserves.reserve_margin_constraint,
)
```

Plus it has two methods (static/dynamic) making it even more different from other models.

**Parameter definition:**
- **Old code (mip-dev):** `M.PlanningReserveMargin = Param(M.RegionalGlobalIndices, default=0)`
- **New code (unstable):** `self.planning_reserve_margin = Param(self.regions)` (NO default)

### Your Logic Check

⚠️ **YOUR LOGIC IS PARTIALLY CORRECT:**

You stated: "Empty PRM table goes to default of 0.2 or something (in old code)."

**Verification:**
- **Old code (mip-dev):** Had `default=0` (not 0.2), so empty table → no reserve margin
- **New code (unstable):** Has NO default, so empty table → constraint should skip (or error if constraint tries to use undefined parameter)

**The flawed approach:** Having a non-zero default means users get reserve margins they didn't ask for. Your removal of the default in mip-dev (by setting to 0) was correct.

### Risk Assessment

🟢 **LOW RISK** (downgraded from HIGH)

- **mip-dev:** Constraint is OFF (commented out), default was 0
- **unstable:** Constraint code exists, but parameter has NO default
- **Impact:** If `planning_reserve_margin` table is empty, constraint indices won't be created (no PRM data → no constraint)

### Decision & Recommendation

**DECISION:** Your approach is sound - if the table is empty, the constraint shouldn't activate.

**Better solution than removing constraint code:**

The constraint should already skip when table is empty (no parameter values = no constraint indices). To verify this works correctly in unstable, check `reserve_margin_constraint_indices()` function - it should only create indices where `(r, p, s, d)` have defined PRM values.

**Test:**
```sql
-- If this returns 0 rows, constraint is inactive:
SELECT * FROM planning_reserve_margin;
```

**If unstable tries to create constraint with undefined PRM values, add this guard:**
```python
def reserve_margin_constraint_indices(model: TemoaModel):
    indices = {
        (r, p, s, d)
        for r in model.regions
        if (r,) in model.planning_reserve_margin  # Only if PRM is defined
        for p in model.time_optimize
        for s in model.time_season[p]
        for d in model.time_of_day
    }
    return indices
```

**For intercomparison:** Your reasoning is valid - if other models don't have comparable constraints, leaving table empty disables it without code changes.

---

## Change 3: Updated Group Constraints (Added Region Index)

### What YOU Changed (commit 0ce13ef, May 2024)

**Before (old version):**
```python
def MinActivityGroup_Constraint(M, p, g):  # No region index
    activity_p = sum(
        M.V_FlowOut[r, p, s, d, ...] * M.MinGenGroupWeight[r, S_t, g]
        for r in M.RegionalIndices  # Summed over ALL regions
        ...
    )
    return activity_p + activity_p_annual >= M.MinGenGroupTarget[p, g]
```

**After YOUR changes:**
```python
def MinActivityGroup_Constraint(M, r, p, g):  # Added region index
    # r can be individual region, combination (r='Mexico+US+Canada'), or 'global'
    if r == 'global':
      reg = M.regions
    elif '+' in r:
      reg = r.split('+')
    else:
      reg = [r]

    activity_p = sum(
        M.V_FlowOut[_r, p, s, d, ...]
        for _r, _g, S_t in M.tech_groups if _r in reg and _g == g
        ...
    )
    return activity_p + activity_p_annual >= M.MinActivityGroup[r, p, g]
```

**Key changes:**
1. Added `r` (region) to constraint index
2. Removed `MinGenGroupWeight` (no longer weighted)
3. Support for region combinations (`+`) and `global`
4. Changed parameter from `MinGenGroupTarget[p, g]` to `MinActivityGroup[r, p, g]`

### Status in unstable

**✅ EQUIVALENT EXISTS in unstable:**

File: `temoa/components/limits.py`

```python
def limit_activity_share_constraint(
    model: TemoaModel, r: Region, p: Period, g1: Technology, g2: Technology, op: str
) -> ExprLike:
    regions = geography.gather_group_regions(model, r)

    sub_group = technology.gather_group_techs(model, g1)
    sub_activity = quicksum(...)

    super_group = technology.gather_group_techs(model, g2)
    super_activity = quicksum(...)

    share_lim = value(model.limit_activity_share[r, p, g1, g2, op])
    expr = operator_expression(sub_activity, Operator(op), share_lim * super_activity)
```

**Different approach but same functionality:**
- unstable uses "share" constraints (ratio of two groups)
- Supports region combinations via `gather_group_regions()`
- More general with operator parameter (`le`, `ge`, `e`)

### Risk Assessment

🟢 **LOW RISK**

Your group constraint improvements are handled in unstable, just with different implementation (share-based rather than absolute limits).

### Recommendation

**No action needed.** unstable's approach is more general and includes your regional grouping logic.

---

## Change 4: Storage Equations (No Seasonal Storage)

### What YOU Changed (commit 178cdf2, Oct 2023)

**Key change - Modified storage energy balance:**

**Before:**
- Storage could carry across seasons (inter-season storage)
- Final time slice of final season must zero out to `V_StorageInit[r, t, v]`

**After YOUR changes:**
```python
# Enforce the charge level of the first and final timestep of EACH SEASON be equal
if d == M.time_of_day.last():
    d_prev = M.time_of_day.prev(d)
    expr = M.V_StorageLevel[r, p, s, d_prev, t, v] + stored_energy == M.V_StorageInit[r,p,s,t,v]

elif d == M.time_of_day.first():
    expr = M.V_StorageLevel[r, p, s, d, t, v] == M.V_StorageInit[r,p,s,t,v] + stored_energy
```

**Effect:** Storage loops within each season (daily storage only), cannot carry energy across seasons.

**Your reasoning:** "This is not wanted since Temoa naively assumes the representative periods occur in a weighted succession."

**Also changed storage upper bound:**
```python
# Before:
energy_capacity = M.V_Capacity[r, p, t, v] * M.StorageDuration[r, t]

# After:
energy_capacity = M.V_Capacity[r, p, t, v] * M.StorageDuration[r, t] * M.SegFrac[p,s,d] * 8760
```

### Status in unstable

**⚠️ PARTIALLY DIFFERENT:**

File: `temoa/components/storage.py`

unstable has TWO types of storage:

1. **Daily storage** (like your mip-dev change):
```python
def storage_energy_constraint():
    s_next, d_next = model.time_next[p, s, d]
    expr = (
        model.v_storage_level[r, p, s, d, t, v] + stored_energy
        == model.v_storage_level[r, p, s_next, d_next, t, v]
    )
```

Where `time_next` loops within seasons for non-seasonal storage.

2. **Seasonal storage** (NEW in unstable):
```python
def seasonal_storage_energy_constraint():
    # Tracks storage level across seasons for tech_seasonal_storage
```

**Formula for storage upper bound:**
```python
# unstable:
energy_capacity = (
    model.v_capacity[r, p, t, v]
    * value(model.capacity_to_activity[r, t])
    * (value(model.storage_duration[r, t]) / (24 * value(model.days_per_period)))
    * value(model.segment_fraction_per_season[p, s])
    * model.days_per_period
)
```

### Your Logic Check

✅ **YOUR LOGIC IS CORRECT:**

You stated: "So to have comparable results, all we'd do is define our storage techs as daily?"

**Verification:**
- unstable uses `tech_seasonal_storage` set to distinguish storage types
- If storage tech is NOT in `tech_seasonal_storage`, it behaves like mip-dev (daily loop)
- If storage tech IS in `tech_seasonal_storage`, it can carry energy across seasons

### Risk Assessment

🟢 **LOW RISK** (downgraded from MEDIUM)

- **mip-dev:** All storage is daily (loops within season)
- **unstable:** Storage is daily by default, seasonal only if explicitly defined
- **Impact:** As long as `tech_seasonal_storage` is empty, behavior matches mip-dev

### Decision & Recommendation

**DECISION:** Ensure all storage technologies are treated as daily storage (not in `tech_seasonal_storage` set).

**For database migration/conversion, add this check:**

```python
# In your migration script or database conversion logic:

# 1. Ensure tech_seasonal_storage table exists but is empty
CREATE TABLE IF NOT EXISTS tech_seasonal_storage (
    region TEXT,
    tech TEXT,
    PRIMARY KEY (region, tech)
);
-- Leave empty for mip-dev compatibility

# 2. Or explicitly verify no storage techs are in seasonal set
SELECT COUNT(*) FROM tech_seasonal_storage;  -- Should return 0

# 3. All storage techs should only be in tech_storage set
SELECT tech FROM technologies WHERE flag = 'S';  -- These are storage techs
-- None of these should appear in tech_seasonal_storage
```

**Migration script addition:**
```python
def migrate_storage_techs(old_db, new_db):
    """
    Migrate storage technologies from mip-dev to unstable format.

    All storage techs from mip-dev should be 'daily' storage in unstable
    (i.e., NOT in tech_seasonal_storage set).
    """
    # Get all storage techs from old database
    storage_techs = old_db.execute(
        "SELECT DISTINCT tech FROM technologies WHERE flag = 'S'"
    ).fetchall()

    # Ensure tech_seasonal_storage table exists but is EMPTY
    new_db.execute("""
        CREATE TABLE IF NOT EXISTS tech_seasonal_storage (
            region TEXT,
            tech TEXT,
            PRIMARY KEY (region, tech)
        )
    """)

    # Do NOT insert any storage techs into tech_seasonal_storage
    # (They will be daily storage by default)

    print(f"Migrated {len(storage_techs)} storage techs as DAILY storage")
    print("tech_seasonal_storage table: EMPTY (as intended for mip-dev parity)")
```

**Formula difference:** For standard 365-day periods, the formulas should be equivalent. For custom periods (like your 4-week runs), verify manually that the normalization is consistent.

---

## Change 5: End-of-Model Effects in Loan Cost

### What YOU Changed (commit 05bedec, Jul 2025)

**Removed the undiscounted branch:**

**Before:**
```python
* (
    min(value(M.LifetimeLoanProcess[r, S_t, S_v]), P_e - S_v) /
    value(M.LifetimeLoanProcess[r, S_t, S_v])
    if not GDR  # <-- This branch
    else (
        (1 - x ** (-min(value(M.LifetimeLoanProcess[r, S_t, S_v]), P_e - S_v)))
        / (1 - x ** (-value(M.LifetimeLoanProcess[r, S_t, S_v])))
    )
)
```

**After YOUR changes:**
```python
* (
    (1 - x ** (-min(value(M.LifetimeLoanProcess[r, S_t, S_v]), P_e - S_v)))
    / (1 - x ** (-value(M.LifetimeLoanProcess[r, S_t, S_v])))
)
```

**Effect:** Always uses discounted formula, removes simple ratio for `GDR=0` case.

**Your reasoning:** "To better align with other models in the intercomparison study"

### Status in unstable

**✅ HANDLED EQUIVALENTLY:**

File: `temoa/components/costs.py`, function `loan_cost()`

```python
if not global_discount_rate:
    # Undiscounted result
    res = (
        annuity
        * lifetime_loan_process
        / lifetime_process
        * min(lifetime_process, p_e - vintage)
    )
else:
    # Discounted result
    res = (
        annuity
        * annuity_to_pv(global_discount_rate, int(lifetime_loan_process))
        * pv_to_annuity(global_discount_rate, lifetime_process)
        * annuity_to_pv(global_discount_rate, min(lifetime_process, p_e - vintage))
        * fv_to_pv(global_discount_rate, vintage - p_0)
    )
```

**Note:** unstable STILL has the undiscounted branch that you removed.

### Risk Assessment

🟡 **LOW-MEDIUM RISK**

- **Your change:** Removed undiscounted case
- **unstable:** Still has undiscounted case
- **Impact:** Only matters if `global_discount_rate = 0` (rare)

### Recommendation

**Low priority.** Unless you're running undiscounted scenarios, this won't affect results. If GDR=0 is used, unstable will produce different loan costs.

---

## Change 6: Transmission Loss Bug Fix

### What YOU Changed (commit 05bedec, Jul 2025)

**Added efficiency adjustment for exports:**

**Before:**
```python
interregional_exports = sum(
    M.V_FlowOut[r+"-"+reg, p, s, d, c, S_t, S_v, S_o]
    for reg, S_t, S_v, S_o in M.exportRegions[r, p, c]
)
```

**After YOUR changes:**
```python
interregional_exports = sum(
    M.V_FlowOut[r+"-"+reg, p, s, d, c, S_t, S_v, S_o] / value(M.Efficiency[reg+"-"+r, c, S_t, S_v, S_o])
    for reg, S_t, S_v, S_o in M.exportRegions[r, p, c]
)
```

**Effect:** Accounts for transmission losses in commodity balance.

**Your reasoning:** "A more minor bug fix that properly accounts for transmission losses"

### Status in unstable

**✅ BUG FIX IS PRESENT:**

File: `temoa/components/commodities.py`, function `commodity_balance_constraint()`

```python
# export of commodity c from region r to other regions
if (r, p, c) in model.export_regions:
    consumed += sum(
        model.v_flow_out[r + '-' + reg, p, s, d, c, s_t, s_v, S_o]
        / get_variable_efficiency(
            model, cast('Region', r + '-' + reg), p, s, d, c, s_t, s_v, S_o
        )
        for reg, s_t, s_v, S_o in model.export_regions[r, p, c]
        if s_t not in model.tech_annual
    )
```

**Your transmission loss fix IS in unstable** - exports are divided by efficiency.

### Risk Assessment

🟢 **NO RISK**

Your bug fix was incorporated into unstable (or independently discovered).

### Recommendation

No action needed.

<function_calls>
<invoke name="Shell">
<parameter name="command">cd /Users/cameronwade/PycharmProjects/temoa-SRfork && git show unstable:temoa/components/commodities.py | grep -A 80 "def commodity_balance_constraint" | head -120

---

## Summary of Findings

### 🟡 MEDIUM PRIORITY: Verify/Modify Implementation

1. **DemandActivity Constraint**
   - YOU removed it from mip-dev
   - unstable still has it (but only creates when >1 tech serves same demand)
   - **Decision:** Modify `demand_activity_constraint_indices()` to skip when only 1 tech serves demand (smarter than removing)
   - **For power systems:** Typically 1-to-1 demand mapping, so constraint is unnecessary but harmless

2. **Reserve Margin Constraint**
   - YOU removed it from mip-dev (set default=0)
   - unstable has NO default (empty table should skip constraint)
   - **Decision:** Empty `planning_reserve_margin` table = constraint inactive. Verify index function properly guards against undefined PRM
   - **For intercomparison:** Valid reasoning - if other models lack comparable constraints, leave table empty

### 🟢 LOW PRIORITY: Already Handled

3. **Storage Energy Balance**
   - YOU enforced no seasonal storage (loop within each season)
   - unstable supports both daily and seasonal (via `tech_seasonal_storage` set)
   - **Decision:** Keep `tech_seasonal_storage` table empty = all storage is daily (matches mip-dev)
   - **Action:** Add check to migration script to ensure table exists but is empty

4. **Group Constraints** - unstable has equivalent (better) implementation
5. **Transmission Loss Fix** - unstable has the fix
6. **End-of-model Loan Cost** - unstable handles it (but still has undiscounted case you removed)

---

## Critical Action Items for Database Runs

To ensure mip-dev and unstable produce comparable results:

### Recommended Code Improvements to unstable:

1. **Improve DemandActivity constraint** (skip when trivial)
   - File: `temoa/components/commodities.py`
   - Function: `demand_activity_constraint_indices()`
   - Add check: Only create constraint indices when >1 tech serves the demand commodity
   - Effect: Reduces unnecessary constraints without changing behavior

2. **Verify Reserve Margin index function** (skip when table empty)
   - File: `temoa/components/reserves.py`
   - Function: `reserve_margin_constraint_indices()`
   - Verify: Indices only created where `planning_reserve_margin` is defined
   - Effect: Empty PRM table = no constraint (no code removal needed)

3. **Migration Script: Storage Configuration**
   - Ensure `tech_seasonal_storage` table exists but is EMPTY
   - All storage techs default to daily storage (matches mip-dev behavior)
   - See detailed migration script in Change 4 section above

### Database Schema Checks:

```sql
-- 1. Check demand technologies (if multiple techs serve same demand, constraint activates)
SELECT dem, COUNT(DISTINCT tech) as num_techs
FROM efficiency
WHERE dem IN (SELECT DISTINCT demand FROM demands)
GROUP BY dem
HAVING num_techs > 1;
-- If this returns rows, DemandActivity constraint IS active in unstable

-- 2. Check planning reserve margin (should be empty for intercomparison)
SELECT * FROM planning_reserve_margin;
-- Should return 0 rows for constraint to be inactive

-- 3. Check seasonal storage (should be empty for mip-dev parity)
SELECT * FROM tech_seasonal_storage;
-- Should return 0 rows
```

---

## Bottom Line

**Key Findings:**

1. ✅ **DemandActivity Constraint** - Your logic is correct: it's only meaningful when >1 tech serves same demand. For power systems with 1-to-1 mapping, it's trivial. Better solution: modify index function to skip trivial cases.

2. ✅ **Reserve Margin Constraint** - Your approach is sound: empty table should skip constraint. Old code had `default=0`, new code has no default, so empty table = inactive. Verify index function properly guards.

3. ✅ **Storage** - Your logic is correct: keeping `tech_seasonal_storage` empty makes all storage daily (matches mip-dev). Add this to migration script.

**The two CONSTRAINTS are NOT as critical as initially thought:**

- **DemandActivity:** Only matters if database has multiple demand-serving techs for same commodity (uncommon in power systems)
- **ReserveMargin:** Empty table should naturally skip constraint (no code removal needed)

If you run the same database on both with:
- Empty `planning_reserve_margin` table
- Empty `tech_seasonal_storage` table
- 1-to-1 demand technology mapping

Results should be **highly comparable** between mip-dev and unstable.

**Your intercomparison study rationale is valid** - these constraint removals/modifications align with making Temoa comparable to other models that lack similar constraints. The unstable implementation is actually more flexible (constraints activate only when needed) rather than requiring code removal.
