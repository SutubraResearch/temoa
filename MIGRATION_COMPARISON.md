# Temoa mip-dev vs unstable: Detailed Optimization Differences

**Date:** 2026-02-12
**Purpose:** Document material differences in optimization logic between `mip-dev` and `unstable` branches that could affect model results.

---

## 1. Objective Function / Cost Calculation

### 1.1 High-Level Differences

**mip-dev:**
```python
period_costs = loan_costs + fixed_costs + variable_costs + variable_costs_annual
```

**unstable:**
```python
period_costs = loan_costs + fixed_costs + variable_costs + variable_costs_annual + period_emission_cost
```

### 1.2 Emission Costs in Objective (NEW in unstable)

**unstable adds `period_emission_cost` comprising:**

1. **Variable emissions** - from `v_flow_out * emission_activity * cost_emission`
2. **Annual emissions** - from `v_flow_out_annual * emission_activity * cost_emission`
3. **Embodied emissions** - from `v_new_capacity * emission_embodied * cost_emission`
4. **End-of-life emissions** - from `v_annual_retirement * emission_end_of_life * cost_emission`

**Impact:** If `cost_emission` parameter is defined in database, results will differ. mip-dev has no emission costs in objective (only emission limits as constraints).

### 1.3 Loan Cost Calculation

**mip-dev** (inline in `PeriodCost_rule`):
```python
loan_costs = sum(
    V_NewCapacity[r, S_t, S_v]
    * (
        CostInvest[r, S_t, S_v]
        * LoanAnnualize[r, S_t, S_v]
        * (
            LifetimeLoanProcess[r, S_t, S_v]  # if no discount
            if not GDR
            else (
                x ** (P_0 - S_v + 1)
                * (1 - x ** (-LifetimeLoanProcess[r, S_t, S_v]))
                / GDR
            )
        )
    )
    * (
        (1 - x ** (-min(LifetimeLoanProcess[r, S_t, S_v], P_e - S_v)))
        / (1 - x ** (-LifetimeLoanProcess[r, S_t, S_v]))
    )
    for r, S_t, S_v in M.CostInvest.sparse_iterkeys()
    if S_v == p
)
```

**unstable** (separate function `loan_cost`):
```python
# Discounted result
res = (
    annuity
    * annuity_to_pv(global_discount_rate, int(lifetime_loan_process))
    * pv_to_annuity(global_discount_rate, lifetime_process)
    * annuity_to_pv(global_discount_rate, min(lifetime_process, p_e - vintage))
    * fv_to_pv(global_discount_rate, vintage - p_0)
)
```

**Key difference:** Same mathematical result but unstable refactored into helper functions for clarity. The formulas are equivalent.

### 1.4 Survival Curve Support (NEW in unstable)

**unstable** adds `loan_cost_survival_curve` function for technologies with defined survival curves:

```python
res = (
    annuity
    * annuity_to_pv(global_discount_rate, int(lifetime_loan_process))
    / sum(
        lifetime_survival_curve[r, p, t, v]
        * fv_to_pv(global_discount_rate, p - v + 1)
        for p in survival_curve_periods[r, t, v]
        if v <= p
    )
    * sum(
        lifetime_survival_curve[r, p, t, v]
        * fv_to_pv(global_discount_rate, p - v + 1)
        for p in survival_curve_periods[r, t, v]
        if v <= p < p_e
    )
    * fv_to_pv(global_discount_rate, v - p_0)
)
```

**Impact:** Technologies with survival curves will have different loan costs. Costs are distributed according to the survival fraction in each year rather than uniformly over lifetime.

### 1.5 Fixed and Variable Cost Calculation

**mip-dev:**
```python
fixed_costs = sum(
    V_Capacity[r, p, S_t, S_v]
    * (
        CostFixed[r, p, S_t, S_v]
        * (
            MPL[r, p, S_t, S_v]  # if no discount
            if not GDR
            else (x ** (P_0 - p + 1) * (1 - x ** (-MPL[r, p, S_t, S_v])) / GDR)
        )
    )
    for r, S_p, S_t, S_v in M.CostFixed.sparse_iterkeys()
    if S_p == p
)
```

**unstable:**
```python
fixed_costs = quicksum(
    fixed_or_variable_cost(
        model.v_capacity[r, p, S_t, S_v],
        value(model.cost_fixed[r, p, S_t, S_v]),
        value(model.period_length[p]),
        global_discount_rate,
        p_0,
        p=p,
    )
    for r, S_p, S_t, S_v in model.cost_fixed.sparse_iterkeys()
    if S_p == p
)
```

Where `fixed_or_variable_cost` is:
```python
def fixed_or_variable_cost(
    cap_or_flow, cost_factor, cost_years, global_discount_rate, p_0, p
):
    if not global_discount_rate:
        res = cap_or_flow * cost_factor * cost_years
    else:
        res = (
            cap_or_flow
            * cost_factor
            * annuity_to_pv(global_discount_rate, cost_years)
            * fv_to_pv(global_discount_rate, p - p_0)
        )
    return res
```

**Key difference:** Refactored but mathematically equivalent. unstable uses `period_length[p]` instead of `ModelProcessLife[r,p,t,v]` for the cost years.

---

## 2. Retirement and Capacity Adjustment

### 2.1 Adjusted Capacity Constraint

**mip-dev** (`AdjustedCapacity_Constraint`):
```python
if t not in M.tech_retirement:
    if v in M.time_exist:
        return M.V_Capacity[r, p, t, v] == M.ExistingCapacity[r, t, v]
    else:
        return M.V_Capacity[r, p, t, v] == M.V_NewCapacity[r, t, v]
else:
    retired_cap = sum(
        M.V_RetiredCapacity[r, S_p, t, v]
        for S_p in M.time_optimize
        if S_p <= p and S_p > v
    )
    if v in M.time_exist:
        return M.V_Capacity[r, p, t, v] == M.ExistingCapacity[r, t, v] - retired_cap
    else:
        return M.V_Capacity[r, p, t, v] == M.V_NewCapacity[r, t, v] - retired_cap
```

**unstable** (`adjusted_capacity_constraint`):
```python
if v in model.time_exist:
    built_capacity = value(model.existing_capacity[r, t, v])
else:
    built_capacity = model.v_new_capacity[r, t, v]

early_retirements = 0
if t in model.tech_retirement:
    early_retirements = sum(
        model.v_retired_capacity[r, S_p, t, v]
        / value(model.lifetime_survival_curve[r, S_p, t, v])
        for S_p in model.time_optimize
        if v < S_p <= p
        and S_p < v + value(model.lifetime_process[r, t, v]) - value(model.period_length[S_p])
    )

remaining_capacity = (built_capacity - early_retirements) * value(
    model.process_life_frac[r, p, t, v]
)
return model.v_capacity[r, p, t, v] == remaining_capacity
```

**Key differences:**

1. **Survival curves integrated:** Retired capacity is divided by `lifetime_survival_curve[r, S_p, t, v]` to adjust for the survival fraction at the time of retirement
2. **Process life fraction:** Final capacity multiplied by `process_life_frac[r, p, t, v]` which handles mid-period end-of-life
3. **Always applied:** `process_life_frac` applied to all technologies, not just retirement set

**Impact:** Capacity available in each period will differ if:
- Survival curves are defined
- Technologies reach end-of-life mid-period
- Early retirement occurs

### 2.2 Retired Capacity Constraint

**mip-dev** (`RetiredCapacity_Constraint`):
```python
if p == M.time_optimize.first():
    cap_avail = M.ExistingCapacity[r, t, v]
else:
    cap_avail = M.V_Capacity[r, M.time_optimize.prev(p), t, v]
expr = M.V_RetiredCapacity[r, p, t, v] <= cap_avail
return expr
```

**unstable** has `annual_retirement_constraint` instead:
```python
# Get the capacity at the start of this period
if p == v + value(model.lifetime_process[r, t, v]):
    # Exact EOL. No v_capacity or v_retired_capacity for this period.
    if p == model.time_optimize.first():
        cap_begin = model.existing_capacity[r, t, v] * model.lifetime_survival_curve[r, p, t, v]
    else:
        p_prev = model.time_optimize.prev(p)
        cap_begin = (
            model.v_capacity[r, p_prev, t, v]
            * value(model.lifetime_survival_curve[r, p, t, v])
            / value(model.process_life_frac[r, p_prev, t, v])
        )
else:
    cap_begin = (
        model.v_capacity[r, p, t, v]
        * value(model.lifetime_survival_curve[r, p, t, v])
        / value(model.process_life_frac[r, p, t, v])
    )

# Get the capacity at the end of this period (similar logic for cap_end)
# ...

annualised_retirement = (cap_begin - cap_end) / model.period_length[p]
```

**Impact:** unstable's retirement accounting is fundamentally different - it calculates annualized retirement for EOL emissions tracking, while mip-dev only bounds retirement capacity.

---

## 3. Storage Constraints

### 3.1 Storage Energy Upper Bound

**mip-dev** (`StorageEnergyUpperBound_Constraint`):
```python
energy_capacity = (
    M.V_Capacity[r, p, t, v]
    * M.StorageDuration[r, t]
    * M.SegFrac[p, s, d]
    * 8760
)
expr = M.V_StorageLevel[r, p, s, d, t, v] <= energy_capacity
return expr
```

**unstable** (`storage_energy_upper_bound_constraint`):
```python
if model.is_seasonal_storage[t]:
    return Constraint.Skip  # redundant on SeasonalStorageEnergyUpperBound

energy_capacity = (
    model.v_capacity[r, p, t, v]
    * value(model.capacity_to_activity[r, t])
    * (value(model.storage_duration[r, t]) / (24 * value(model.days_per_period)))
    * value(model.segment_fraction_per_season[p, s])
    * model.days_per_period  # adjust for days in season
)

expr = model.v_storage_level[r, p, s, d, t, v] <= energy_capacity
return expr
```

**Key differences:**

1. **Seasonal storage separated:** unstable skips this constraint if `is_seasonal_storage[t]` is True
2. **Formula difference:**
   - mip-dev: `capacity * duration * seg_frac * 8760`
   - unstable: `capacity * c2a * (duration / (24 * days_per_period)) * seg_frac_per_season * days_per_period`

**Mathematical equivalence check:**
- If `days_per_period = 365` and `c2a = 8760`:
  - unstable: `capacity * 8760 * (duration / (24 * 365)) * seg_frac * 365`
  - Simplifies to: `capacity * 8760 * duration / 24 * seg_frac`
  - mip-dev equivalent: `capacity * duration * seg_frac * 8760` (if duration in hours)

**Impact:** Results may differ depending on how `StorageDuration` and `CapacityToActivity` are defined. unstable explicitly normalizes by `days_per_period`.

### 3.2 Seasonal Storage (NEW in unstable)

**unstable adds separate seasonal storage constraints:**

- `seasonal_storage_energy_constraint` - tracks storage level across seasons
- `seasonal_storage_energy_upper_bound_constraint` - bounds seasonal storage
- `limit_storage_fraction_constraint` - limits storage as fraction of capacity

**Impact:** Databases with seasonal storage will behave differently. mip-dev does not have explicit seasonal storage support.

---

## 4. Reserve Margin Constraint

### 4.1 Basic Structure

**mip-dev** (`ReserveMargin_Constraint`):
```python
cap_avail = sum(
    value(M.CapacityCredit[reg, p, t, v])
    * M.ProcessLifeFrac[reg, p, t, v]
    * M.V_Capacity[reg, p, t, v]
    * value(M.CapacityToActivity[reg, t])
    * value(M.SegFrac[p, s, d])
    for reg in regions
    for t in M.tech_reserve
    if (reg, p, t) in M.processVintages.keys()
    for v in M.processVintages[reg, p, t]
    if (reg, p, t, v) in M.activeCapacityAvailable_rptv
)
```

**unstable** (`reserve_margin_constraint`):
```python
match model.reserve_margin_method.first():
    case 'static':
        available = reserve_margin_static(model, r, p, s, d)
    case 'dynamic':
        available = reserve_margin_dynamic(model, r, p, s, d)
```

### 4.2 Static vs Dynamic Methods (NEW in unstable)

**Static method** (similar to mip-dev):
```python
def reserve_margin_static(model, r, p, s, d):
    available = quicksum(
        value(model.capacity_credit[_r, p, t, v])
        * value(model.process_life_frac[_r, p, t, v])
        * model.v_capacity[_r, p, t, v]
        * value(model.capacity_to_activity[_r, t])
        * value(model.segment_fraction[p, s, d])
        for _r in regions
        for (t, v) in model.process_reserve_periods[_r, p]
    )
    return available
```

**Dynamic method** (NEW):
```python
def reserve_margin_dynamic(model, r, p, s, d):
    # Uses v_flow_out instead of capacity
    available = quicksum(
        model.v_flow_out[_r, p, s, d, S_i, t, v, S_o]
        for _r in regions
        for (t, v) in model.process_reserve_periods[_r, p]
        for S_i in model.process_inputs[_r, p, t, v]
        for S_o in model.process_outputs_by_input[_r, p, t, v, S_i]
    )
    return available
```

**Impact:** With `dynamic` method, reserve is based on actual generation rather than derated capacity. Results will differ significantly.

### 4.3 Regional Exchange Handling

**unstable** has more sophisticated handling of imports/exports via exchange technologies:

```python
# Exports subtracted from generation
if r1 == r:
    total_generation -= sum(
        model.v_flow_out[r1r2, p, s, d, S_i, t, S_v, S_o]
        / get_variable_efficiency(model, r1r2, p, s, d, S_i, t, S_v, S_o)
        for (t, S_v) in model.process_reserve_periods[r1r2, p]
        for S_i in model.process_inputs[r1r2, p, t, S_v]
        for S_o in model.process_outputs_by_input[r1r2, p, t, S_v, S_i]
    )
# Imports added to generation
elif r2 == r:
    total_generation += sum(...)
```

**Impact:** Imports/exports will affect reserve margin differently between versions.

---

## 5. Constraints Present in unstable but NOT in mip-dev

| Constraint | Purpose | Impact |
|-----------|---------|--------|
| `seasonal_storage_energy_constraint` | Track storage across seasons | Seasonal storage won't work in mip-dev |
| `seasonal_storage_energy_upper_bound_constraint` | Bound seasonal storage | Seasonal storage won't work in mip-dev |
| `limit_storage_fraction_constraint` | Limit storage as % of capacity | Storage sizing may differ |
| `annual_retirement_constraint` | Track annualized retirements | Needed for EOL emissions |
| `demand_activity_constraint` | Ensure demand tech usage pattern | May affect demand technology dispatch |
| `linked_emissions_tech_constraint` | Link emissions between techs | Emission accounting may differ |
| `renewable_portfolio_standard_constraint` | RPS constraint | RPS won't work in mip-dev |
| `limit_capacity_share_constraint` | Capacity share limits with operators | Group constraints work differently |
| `limit_activity_share_constraint` | Activity share limits with operators | Group constraints work differently |
| `limit_new_capacity_share_constraint` | New capacity share limits | Group constraints work differently |

---

## 6. Constraints in mip-dev Handled Differently in unstable

| mip-dev | unstable | Difference |
|---------|----------|-----------|
| `StorageInit_Constraint` | Not present | mip-dev has explicit storage initialization |
| `RampUpPeriod_Constraint` | Not present | mip-dev has period-level ramping |
| `RampDownPeriod_Constraint` | Not present | mip-dev has period-level ramping |
| `GrowthRateConstraint` | `limit_growth_capacity_constraint` + `limit_degrowth_capacity_constraint` | Split into separate growth/degrowth |
| `MaxCapacityGroup` | `limit_capacity_share_constraint` | Unified with operator parameter |
| `MinCapacityGroup` | `limit_capacity_share_constraint` | Unified with operator parameter |
| `MaxActivityGroup` | `limit_activity_share_constraint` | Unified with operator parameter |
| `MinActivityGroup` | `limit_activity_share_constraint` | Unified with operator parameter |

---

## 7. Summary of Result-Affecting Differences

### Will ALWAYS cause different results:

1. **Emission costs in objective** - if `cost_emission` is defined
2. **Survival curves** - if `lifetime_survival_curve` is defined
3. **Process life fraction** - affects capacity in all periods
4. **Seasonal storage** - unstable has explicit support, mip-dev doesn't
5. **Storage energy bounds** - formula differences may cause different bounds
6. **Reserve margin method** - dynamic vs static produces very different results
7. **Annual retirement tracking** - different retirement accounting

### May cause different results depending on database:

1. **Storage initialization** - mip-dev has explicit constraint, unstable doesn't
2. **Period ramping** - mip-dev has it, unstable doesn't
3. **Growth rate constraints** - different formulation
4. **Group constraints** - different implementation

### Should NOT cause different results:

1. **Loan cost calculation** - mathematically equivalent
2. **Fixed/variable costs** - mathematically equivalent
3. **Basic capacity constraints** - same logic
4. **Demand constraints** - same logic

---

## 8. Recommendations

### For users migrating from mip-dev to unstable:

1. **Check emission costs:** If `cost_emission` is in your database, expect cost differences
2. **Check survival curves:** If defined, expect capacity/retirement differences
3. **Check storage:** If using storage, verify formulas match your assumptions
4. **Check reserve margin:** Verify which method (static/dynamic) matches mip-dev behavior
5. **Check period ramping:** If used in mip-dev, may need custom implementation in unstable
6. **Check storage init:** If storage initialization matters, may need custom constraint

### For developers:

1. **Document survival curve activation** - when/how does it trigger?
2. **Add migration guide** - for databases moving from mip-dev to unstable
3. **Add test cases** - comparing results between versions
4. **Consider backwards compatibility** - option to disable new features

---

## 9. Test Scenarios to Expose Differences

1. **Emission cost test:** Database with `cost_emission` defined
2. **Survival curve test:** Database with `lifetime_survival_curve` defined
3. **Storage test:** Database with storage technologies
4. **Reserve margin test:** Run with both static and dynamic methods
5. **Retirement test:** Database with endogenous retirement
6. **RPS test:** Database with renewable targets
7. **Group constraint test:** Database with capacity/activity groups
