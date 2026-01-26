# Data Requirements and Gaps

**Purpose**: Catalog the data needed for the hydrocarbon module, identify potential sources, and flag gaps requiring attention.

---

## Overview

The hydrocarbon module requires data in five categories:

1. **Regional Supply Curves** — Production costs and capacity by fuel and region
2. **Inter-Regional Trade** — Pipeline/transport capacities and costs
3. **International Trade** — Import/export capacities, prices, and demand curve parameters
4. **Product Interrelationships** — Refinery yields, associated gas ratios
5. **Validation Data** — Historical prices, flows, production for calibration

---

## 1. Regional Supply Curves

### What's Needed

For each fuel `f`, region `r`, block `b`, and period `p`:

| Parameter | Description | Units |
|-----------|-------------|-------|
| λ_{f,r,b,p} | Marginal cost of block | $/unit |
| s̄_{f,r,b,p} | Maximum production from block | units/year |

### Potential Sources

#### NEMS (National Energy Modeling System)

The EIA's NEMS includes detailed supply modules:

- **Oil and Gas Supply Module (OGSM)**: Regional oil and gas production projections, cost curves
- **Petroleum Market Module (PMM)**: Refinery operations, product supply
- **Natural Gas Transmission and Distribution Module**: Pipeline flows, regional prices

**Accessibility**: 
- NEMS documentation is public (EIA website)
- NEMS source code is restricted, but model structure is documented
- AEO (Annual Energy Outlook) publications include regional projections
- Some NEMS data tables may be extractable from AEO data files

**Question for ex-EIA member**: What NEMS data is realistically accessible? Can we get supply curve parameters directly?

#### EIA Publications

- **Annual Energy Outlook (AEO)**: Regional production projections, price trajectories
- **Petroleum Supply Annual**: Refinery production, regional data
- **Natural Gas Annual**: Production, consumption, prices by state/region
- **Drilling Productivity Report**: Well-level production data

**Limitation**: Publications provide projections, not explicit supply curves. Would need to infer curves from production-price relationships.

#### Academic Literature

- Oil and gas supply curve studies (many exist for shale plays)
- USGS resource assessments
- Academic energy models (may publish calibrated curves)

#### Expert Elicitation

- Construct curves from cost estimates + resource assessments
- Leverage working group expertise

### Data Structure (Example)

```
Table: supply_curve_block
---------------------------------------------------------------
fuel     region  block  period  marginal_cost  max_quantity  notes
---------------------------------------------------------------
natgas   R1      1      2025    2.50           1000          Conventional
natgas   R1      2      2025    3.25           2000          Shale - Tier 1
natgas   R1      3      2025    4.00           1500          Shale - Tier 2
natgas   R1      4      2025    5.50           500           Shale - Tier 3
gasoline R1      1      2025    2.10           500           Gulf Coast supply
...
```

### Gaps and Challenges

| Gap | Severity | Mitigation |
|-----|----------|------------|
| Explicit supply curves not published | High | Infer from production-price data or expert judgment |
| Regional disaggregation | Medium | May need to aggregate/disaggregate from state-level data |
| Future projections | Medium | Use AEO trajectories or scenario assumptions |
| Consistency across fuels | Medium | Different sources for different fuels may not align |

---

## 2. Inter-Regional Trade

### What's Needed

For each fuel `f`, region pair `(r, r')`, and period `p`:

| Parameter | Description | Units |
|-----------|-------------|-------|
| T̄_{f,r->r',p} | Bilateral trade capacity | units/year |
| τ_{f,r->r'} | Transport cost | $/unit |
| ε_{f,r->r'} | Transport loss factor | fraction |

### Potential Sources

#### Natural Gas Pipelines

- **EIA Natural Gas Pipeline Projects**: Capacity data, planned expansions
- **FERC filings**: Pipeline capacity, utilization
- **EIA Natural Gas Pipeline Network Map**: Geographic structure
- **State of the Market reports**: Flow data

**Quality**: Good data availability for major pipelines. Challenge is aggregating to 9-region structure.

#### Petroleum Pipelines

- **EIA Petroleum Pipeline Capacity and Utilization**: Major liquid pipelines
- **PHMSA (Pipeline and Hazardous Materials Safety Administration)**: Pipeline data
- **Trade publications**: Oil & Gas Journal, Pipeline & Gas Journal

**Quality**: Less comprehensive than gas. May need to supplement with rail/barge data.

#### Other Transport Modes

- Rail: Association of American Railroads data, EIA petroleum movements
- Barge/tanker: US Army Corps of Engineers waterway data
- Truck: Limited data, typically short-haul

### Data Structure (Example)

```
Table: trade_capacity
-------------------------------------------------------------------
fuel      from_region  to_region  period  capacity  cost    loss
-------------------------------------------------------------------
natgas    R1           R2         2025    5000      0.25    0.02
natgas    R2           R1         2025    3000      0.25    0.02
gasoline  R1           R2         2025    2000      0.05    0.001
diesel    R1           R2         2025    1500      0.05    0.001
...
```

### Gaps and Challenges

| Gap | Severity | Mitigation |
|-----|----------|------------|
| Aggregation to 9 regions | Medium | Define mapping from pipeline-level to regional |
| Petroleum transport modes | Medium | Aggregate pipeline + rail + barge |
| Transport costs | Medium | Estimate from tariffs or literature |
| Future capacity | Low | Use existing + announced projects |

---

## 3. International Trade

### What's Needed

For each fuel `f`, region `r` with port/border access, and period `p`:

| Parameter | Description | Units |
|-----------|-------------|-------|
| M̂^{imp}_{f,r,p} | Maximum import capacity | units/year |
| M̂^{exp}_{f,r,p} | Maximum export capacity | units/year |
| P^{imp}_{f,r,p} | Import price (if fixed) | $/unit |
| P^{exp}_{f,r,p} | Export price (if fixed) | $/unit |
| γ_{f,r,k,p}, δ_{f,r,k,p} | Demand curve parameters (if used) | varies |

### Potential Sources

#### Import/Export Volumes and Prices

- **EIA Petroleum & Other Liquids**: Import/export volumes, prices, by port
- **EIA Natural Gas Imports/Exports**: Pipeline (Canada/Mexico), LNG
- **US Census Bureau**: Trade statistics
- **BP Statistical Review**: Global benchmarks

#### LNG Specifics

- **EIA LNG Reports**: Export terminal capacity, utilization
- **FERC LNG Reports**: Terminal data
- **DOE export authorizations**: Permitted volumes

#### Demand Curve Parameters

This is the hardest data to obtain. Options:

- **NEMS**: May have implicit elasticities in trade module
- **Academic literature**: Trade elasticity studies
- **Calibration**: Adjust to match historical price-quantity relationships
- **Sensitivity analysis**: Test range of slopes

### Data Structure (Example)

```
Table: international_trade
----------------------------------------------------------------------
fuel      region  period  max_import  max_export  import_price  export_price
----------------------------------------------------------------------
crude     R1      2025    2000        0           70.00         -
gasoline  R1      2025    500         800         2.10          1.95
lng       R1      2025    0           1500        -             8.00
natgas    R2      2025    1000        0           3.50          -  (Canada pipe)
...
```

### Gaps and Challenges

| Gap | Severity | Mitigation |
|-----|----------|------------|
| Demand curve slopes | High | Start with fixed prices; add curves later if needed |
| Regional port allocation | Medium | Assign imports/exports to nearest regions |
| Future capacity (esp. LNG) | Medium | Use DOE projections + announced projects |
| Price projections | Medium | Use AEO or scenario assumptions |

---

## 4. Product Interrelationships

### What's Needed

#### Refinery Yields (if using coupling constraints)

| Parameter | Description | Units |
|-----------|-------------|-------|
| α_f | Normalized yield coefficient for product f | fraction |
| ρ_{f,f'}, ρ̄_{f,f'} | Bounds on product ratios | fraction |
| δ̄_{f,r} | Maximum deviation from base yields | fraction |

#### Associated Gas (if modeling)

| Parameter | Description | Units |
|-----------|-------------|-------|
| β_r | Associated gas ratio (gas per barrel crude) | MCF/bbl |
| Ā_r | Max non-associated gas production | MCF/year |
| φ_r | Max flaring fraction | fraction |

### Potential Sources

#### Refinery Yields

- **EIA Refinery Capacity Report**: Regional refinery characteristics
- **EIA Petroleum Supply Monthly**: Product yields by PAD District
- **API/AFPM data**: Industry refinery statistics
- **Expert judgment**: Working group refinery engineers

**Typical US Refinery Yields** (approximate):

| Product | Typical Yield (% of crude) |
|---------|---------------------------|
| Gasoline | 45-50% |
| Diesel/Heating Oil | 25-30% |
| Jet Fuel | 8-10% |
| LPG/NGLs | 3-5% |
| Residual Fuel Oil | 3-5% |
| Other | 5-10% |

*Note: Yields vary significantly by crude slate and refinery configuration*

#### Associated Gas

- **EIA statistics**: Associated gas production by state
- **State agencies**: Texas RRC, New Mexico OCD
- **Academic literature**: Basin-level studies (Permian, Bakken, etc.)

### Gaps and Challenges

| Gap | Severity | Mitigation |
|-----|----------|------------|
| Regional yield variation | Medium | Get input from refinery engineers |
| Yield flexibility bounds | Medium | Expert judgment needed |
| Associated gas ratios | Medium | State-level data available |
| Flaring regulations | Low | EPA/state data |

---

## 5. Validation Data

### What's Needed

Historical data for model calibration and validation:

| Data | Purpose |
|------|---------|
| Regional fuel prices | Compare model shadow prices to actuals |
| Production volumes | Compare supply curve dispatch |
| Trade flows | Compare model trade to actuals |
| Consumption by region | Validate demand side |

### Potential Sources

- **EIA historical data**: Extensive price and volume data
- **State energy offices**: State-level detail
- **Academic studies**: Calibration approaches

### Validation Approach

1. **Backcast**: Run model for historical years (2015-2022)
2. **Compare**: Model prices/flows vs. actual
3. **Calibrate**: Adjust parameters to improve fit
4. **Sensitivity**: Test robustness to parameter changes

---

## Summary: Data Availability Assessment

| Data Category | Availability | Quality | Effort to Obtain |
|--------------|--------------|---------|------------------|
| Gas supply curves | Medium | Medium | High (need to construct) |
| Petroleum supply curves | Low-Medium | Medium | High |
| Gas pipeline capacity | High | Good | Medium |
| Petroleum transport | Medium | Medium | Medium |
| International trade volumes | High | Good | Low |
| International prices | High | Good | Low |
| Demand curve parameters | Low | Unknown | High |
| Refinery yields | Medium | Good | Medium |
| Associated gas | Medium | Medium | Medium |
| Validation data | High | Good | Low |

---

## Key Data Gaps Requiring Group Attention

### Critical Gaps

1. **Regional supply curves**: No published source. Must construct from disaggregated data or expert judgment. **Need to assign ownership.**

2. **Demand curve slopes for international trade**: Literature sparse. May need to use sensitivity analysis or calibration. **Question: Is this feature essential, or can we use fixed prices?**

### Important Gaps

3. **Refinery yield flexibility**: How much can yields vary? Regional differences? **Need refinery engineer input.**

4. **Aggregation to 9 regions**: Most data is at state or pipeline level. Need consistent mapping. **Need to define regional concordance.**

### Lower Priority Gaps

5. **Future projections**: Can use AEO or scenario assumptions
6. **Transport costs**: Can estimate from tariffs or literature

---

## Data Requirements by Scope Package

See [03_scope_packages.md](03_scope_packages.md) for full package descriptions.

### Package A (Foundation)

| Data Category | Required | Notes |
|---------------|----------|-------|
| Regional supply curves | Yes (all 7 fuels) | Must construct from EIA/NEMS |
| Trade capacities | Major corridors | EIA pipeline data |
| Transport costs | Yes | Tariffs, estimates |
| World prices | Fixed | AEO projections |
| Product coupling bounds | Soft bounds only | Refinery expertise |
| Demand curve parameters | No | Not needed |

### Package B (Core)

All of Package A, plus:

| Data Category | Required | Notes |
|---------------|----------|-------|
| LNG export demand curves | Yes | World gas market studies |
| Canada pipeline integration | Yes | North American trade data |
| Bounded product ratios | Yes | Refinery expertise |
| Associated gas ratios | Optional | State production data |

### Package C (Full)

All of Package B, plus:

| Data Category | Required | Notes |
|---------------|----------|-------|
| Crude supply curves | Yes | EIA/NEMS, state data |
| Crude import demand curves | Yes | World oil market studies |
| Refinery yields | Yes | Regional refinery data |
| Refinery costs | Yes | Industry data |
| Refinery capacities | Yes | EIA data |

---

## Questions for Working Group

1. **NEMS data access**: Can we get supply curve data from NEMS or must we construct it?

2. **Refinery yields**: What parameters should we use? Regional variation?

3. **Data ownership**: Who will lead data acquisition for each category?

4. **Validation**: What historical period should we use for calibration?

5. **Demand curves**: Essential feature or can we defer?

---

*Next document: [05_glossary.md](05_glossary.md) — Terminology and notation reference*
