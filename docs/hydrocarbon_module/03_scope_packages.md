# Scope Packages

**Purpose**: Present coherent scope bundles that combine decisions into implementable packages. Each package represents a consistent set of choices with clear trade-offs.

---

## Overview

| Package | Philosophy | Crude Oil | International Trade | Product Coupling | Effort |
|---------|-----------|-----------|---------------------|------------------|--------|
| **A: Foundation** | Get endogenous prices working | Implicit | Fixed prices + caps | Soft bounds | Lower |
| **B: Core** | Realistic market dynamics | Implicit | Demand curves for gas | Bounded ratios | Medium |
| **C: Full** | Maximum fidelity | Explicit | Full demand curves | Via refineries | Higher |

---

## Package A: Foundation

### Philosophy

Get the core mechanism working: **endogenous regional fuel prices** driven by supply curves, inter-regional trade, and international trade. Keep everything else as simple as possible.

### Scope

| Mechanism | Package A Choice |
|-----------|-----------------|
| **Regional supply** | Piecewise-linear curves, 5 blocks per fuel/region |
| **Inter-regional trade** | Major corridors only, fixed capacities, transport costs |
| **International trade** | Fixed world prices with quantity caps |
| **Prices** | Shadow prices of balance constraints |
| **Product coupling** | Soft bounds (inequality constraints) |
| **Crude oil** | Implicit (no crude commodity) |
| **Natural gas** | Single commodity, Canada as special bilateral |
| **Associated gas** | Not modeled |

### What's In

- [Y] All 7 fuels with regional supply curves
- [Y] Regional price differentiation
- [Y] Inter-regional trade on major corridors
- [Y] International imports/exports with caps
- [Y] Basic product coupling (prevents extreme imbalances)
- [Y] Spatial price equilibrium emerges from optimization

### What's Out

- [N] World price response to US actions
- [N] Detailed refinery economics
- [N] Associated gas coupling
- [N] LNG as separate commodity
- [N] Infrastructure investment decisions

### Questions It Can Answer

- How do regional production costs affect fuel prices?
- How do pipeline constraints create regional price spreads?
- What happens to prices under demand scenarios?
- Where are the marginal supply sources?

### Questions It Cannot Answer

- How do LNG exports affect domestic gas prices? (world price is fixed)
- How does crude price affect product prices? (no crude)
- What's the value of pipeline investment? (infrastructure fixed)
- How does oil production affect gas supply? (no associated gas)

### Data Requirements

| Data | Availability | Notes |
|------|--------------|-------|
| Regional supply curves (7 fuels × 9 regions) | Medium | Must construct from EIA/NEMS |
| Trade corridor capacities | High | EIA pipeline data |
| Transport costs | Medium | Tariffs, estimates |
| World prices | High | AEO projections |
| Import/export caps | High | Historical + infrastructure |
| Product coupling bounds | Medium | Refinery expertise needed |

### Implementation Notes

- Can likely be done with existing Temoa structures (technologies + constraints)
- Minimal code changes
- Good for proving the concept

### Rough Effort: Lower

---

## Package B: Core

### Philosophy

Add the key features that make this **more than just supply curves**: world price responsiveness for gas/LNG (where US is a major player), tighter product coupling, and better North American integration.

### Scope

| Mechanism | Package B Choice |
|-----------|-----------------|
| **Regional supply** | Piecewise-linear curves, 5-7 blocks per fuel/region |
| **Inter-regional trade** | Full bilateral network, capacities on major corridors |
| **International trade** | Demand curves for nat gas/LNG; fixed prices for petroleum |
| **Prices** | Shadow prices with explicit reporting |
| **Product coupling** | Bounded ratios (range constraints) |
| **Crude oil** | Implicit (no crude commodity) |
| **Natural gas** | Separate pipeline gas and LNG commodities |
| **Canada/Mexico** | Integrated for pipeline gas; international for LNG |
| **Associated gas** | Optional constraint (gas >= β × regional oil supply proxy) |

### What's In

Everything in Package A, plus:

- [Y] LNG as separate commodity
- [Y] Demand curves for gas/LNG exports (US affects world price)
- [Y] Bounded ratio constraints for petroleum products
- [Y] Canada pipeline gas integration
- [Y] Optional associated gas coupling

### What's Out

- [N] Explicit crude oil commodity
- [N] Refinery technologies
- [N] Demand curves for petroleum products (US is price-taker)
- [N] Infrastructure investment decisions

### Questions It Can Answer

Everything in Package A, plus:

- How do LNG exports affect domestic natural gas prices?
- How does US LNG expansion affect world gas prices?
- How tight are refinery yield constraints (via bounded ratios)?
- How does Canada pipeline integration affect regional gas prices?

### Questions It Cannot Answer

- How does crude price affect product prices?
- Refinery investment decisions
- Detailed crude slate optimization

### Data Requirements

Everything in Package A, plus:

| Data | Availability | Notes |
|------|--------------|-------|
| LNG export demand curve parameters | Low-Medium | World gas market elasticity |
| Pipeline gas demand curve (Canada) | Medium | North American market studies |
| Bounded product ratios | Medium | Refinery expertise needed |
| Regional oil production (for associated gas) | High | EIA data |

### Implementation Notes

- Likely requires some Temoa code additions:
  - Native handling of demand curves (piecewise-linear in Pyomo)
  - Separate LNG commodity and trade
  - Bounded ratio constraints
- More complex data preparation

### Rough Effort: Medium

---

## Package C: Full

### Philosophy

Model the **complete crude-to-products supply chain**. Crude oil is an explicit commodity with supply curves. Refineries are technologies that convert crude to products. Maximum fidelity to physical reality.

### Scope

| Mechanism | Package C Choice |
|-----------|-----------------|
| **Regional supply** | Curves for crude and nat gas; products from refineries |
| **Inter-regional trade** | Full network; crude and products; capacities |
| **International trade** | Demand curves for crude, LNG; bounded for products |
| **Prices** | Full price reporting infrastructure |
| **Product coupling** | Natural (emerges from refinery yields) |
| **Crude oil** | Explicit commodity with supply curves |
| **Refineries** | Technologies: crude -> products; regional capacity |
| **Natural gas** | Separate pipeline and LNG; associated gas from crude |
| **Associated gas** | Automatic (linked to crude production) |

### What's In

Everything in Package B, plus:

- [Y] Crude oil as explicit commodity
- [Y] Regional crude supply curves
- [Y] Refinery technologies (crude -> products)
- [Y] Product coupling natural from refinery yields
- [Y] Associated gas automatic
- [Y] International crude trade

### What's Out

- [N] Detailed refinery unit operations (still aggregate)
- [N] Crude quality differentiation (single crude type)
- [N] Refinery investment decisions (fixed capacity for now)

### Questions It Can Answer

Everything in Package B, plus:

- How does crude oil price affect refined product prices?
- What are refinery margins by region?
- How does associated gas production interact with oil supply?
- How do crude supply constraints propagate to products?

### Questions It Cannot Answer (Without Further Extension)

- Detailed refinery optimization (unit-level)
- Crude slate optimization (multiple crude types)
- Refinery investment decisions

### Data Requirements

Everything in Package B, plus:

| Data | Availability | Notes |
|------|--------------|-------|
| Regional crude supply curves | Medium | EIA/NEMS, state data |
| Crude import demand curves | Low-Medium | World oil market elasticity |
| Refinery yields by region | Medium-High | EIA refinery reports, expert input |
| Refinery operating costs | Medium | Industry data, literature |
| Refinery capacity by region | High | EIA data |

### Implementation Notes

- Significant Temoa additions:
  - Crude oil commodity
  - Refinery technologies
  - Linkage between crude, gas, and products
- Most complex data preparation
- Closest to NEMS-style representation

### Rough Effort: Higher

---

## Package Comparison

### Feature Matrix

| Feature | A: Foundation | B: Core | C: Full |
|---------|---------------|---------|---------|
| Regional supply curves | [Y] | [Y] | [Y] |
| Inter-regional trade | Major corridors | Full network | Full network |
| International prices | Fixed | Demand curves (gas) | Demand curves (crude, gas) |
| Product coupling | Soft bounds | Bounded ratios | Refinery yields |
| Crude oil explicit | [N] | [N] | [Y] |
| Refineries explicit | [N] | [N] | [Y] |
| Separate LNG | [N] | [Y] | [Y] |
| Associated gas | [N] | Optional | Automatic |
| Canada/Mexico integration | Basic | Pipeline gas | Full |

### Analytical Capabilities

| Question | A | B | C |
|----------|---|---|---|
| Regional fuel prices | [Y] | [Y] | [Y] |
| Price response to demand | [Y] | [Y] | [Y] |
| Inter-regional price spreads | [Y] | [Y] | [Y] |
| LNG export impact on gas prices | [N] | [Y] | [Y] |
| Crude price impact on products | [N] | [N] | [Y] |
| Refinery margins | [N] | [N] | [Y] |
| Associated gas dynamics | [N] | Partial | [Y] |

### Effort and Risk

| Aspect | A | B | C |
|--------|---|---|---|
| Implementation effort | Lower | Medium | Higher |
| Data preparation | Medium | Medium-High | High |
| Risk of scope creep | Low | Medium | Higher |
| Time to first results | Fastest | Moderate | Longest |
| Long-term value | Good | Better | Best |

---

## Recommended Path

### Option 1: Start with A, Plan for B

1. Implement Package A (foundation)
2. Validate basic functionality
3. Add Package B features incrementally
4. Defer Package C unless clear need

**Rationale**: De-risks implementation, delivers value early, preserves optionality.

### Option 2: Go Directly to B

1. Implement Package B as the target
2. Accept longer timeline
3. Skip A as intermediate step

**Rationale**: If LNG dynamics are critical to analysis questions, don't waste time on A.

### Option 3: Commit to C

1. Design for Package C from the start
2. Implement crude-to-products chain
3. Most ambitious, most capability

**Rationale**: If crude oil economics and refinery analysis are core needs.

---

## Questions for Working Group

1. **Which package aligns with OEO's analytical needs?**
   - What questions must we be able to answer?
   - Is LNG export impact critical? (B required)
   - Is crude price impact critical? (C required)

2. **What's the tolerance for development time?**
   - Need results quickly? -> Start with A
   - Can invest more time? -> Go to B or C

3. **What data resources do we have?**
   - Strong EIA/NEMS access? -> C more feasible
   - Limited data access? -> A or B more practical

4. **What's the phasing preference?**
   - Incremental (A -> B -> C)?
   - Direct to target (B or C)?

---

## Implementation Architecture (Brief Note)

Regardless of package, implementation options are:

| Approach | Description | Fit |
|----------|-------------|-----|
| **Data-only** | Use existing Temoa constructs (techs, constraints) | A, maybe B |
| **Temoa extension** | Add native Pyomo components for fuel markets | B, C |
| **Submodule** | Separate hydrocarbon module with clean interface | C |

The Temoa developers can advise on which approach is practical for each package.

---

*Next: Review [04_data_requirements.md](04_data_requirements.md) for alignment with chosen package*
