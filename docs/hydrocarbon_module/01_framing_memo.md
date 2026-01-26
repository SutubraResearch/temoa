# Framing Memo: Endogenous Hydrocarbon Markets for OEO

**Purpose**: Establish shared understanding of why we're pursuing this project, what we aim to achieve, and where the boundaries lie.

---

## 1. The Problem

The Open Energy Outlook (OEO) databases currently model fuel supply in a simplified manner:

- **Fuels are imported at fixed, exogenous prices** — gasoline, diesel, natural gas, etc. are available in unlimited quantities at prices specified by the modeler (which can vary by region, but are still exogenous)
- **No inter-regional fuel trade** — regions cannot exchange fuels with each other
- **No supply constraints** — fuel availability is unlimited at the specified price
- **No price response to demand** — if demand doubles, price stays the same

This simplification made sense when the focus was on the electricity sector, where fuel costs are just one input among many. But as OEO expands to analyze economy-wide decarbonization, transportation electrification, industrial fuel switching, and hydrogen/e-fuel pathways, the fuel supply representation becomes increasingly inadequate.

---

## 2. Why This Matters

### 2.1 Fuel Prices Drive Technology Choice

In OEO, **service demands are exogenous** (passenger-km, heating BTU, industrial output), but **technology choice is endogenous**. The model decides whether to meet transportation demand with EVs or ICE vehicles, whether to heat buildings with heat pumps or gas furnaces, whether to generate electricity with gas turbines or wind farms.

These decisions depend critically on **relative fuel prices**. If natural gas is cheap, gas technologies win. If gas becomes expensive, electric alternatives become competitive. But with fixed (exogenous) fuel prices, the model cannot capture:

- **Price-induced fuel switching**: High gas prices -> more EVs -> lower gas demand -> prices moderate
- **Endogenous price dynamics**: Why is gas cheap in Texas and expensive in New England? What happens if that changes?
- **Supply constraints**: Shale production limits, pipeline bottlenecks, refinery capacity
- **Market feedback**: Demand changes affect prices, which in turn affect technology choice

### 2.2 Decarbonization Scenarios Stress Fuel Markets

Deep decarbonization scenarios involve dramatic shifts in fuel consumption:

- Gasoline and diesel demand collapse as transportation electrifies
- Natural gas demand may spike (as a transition fuel) then decline
- Hydrogen and e-fuels emerge as new commodities
- Biofuel mandates and blending affect petroleum markets

With fixed fuel prices, the model cannot capture how these shifts affect fuel markets — and how fuel market responses affect the energy transition.

### 2.3 Policy Analysis Requires Price Signals

Many policy questions involve fuel markets directly:

- What happens to US natural gas prices if LNG exports expand?
- How do refinery constraints affect gasoline/diesel price spreads?
- What's the impact of a carbon price on regional fuel costs?
- How do oil supply disruptions propagate through the economy?

Answering these questions requires endogenous fuel prices.

---

## 3. The Vision

We propose to develop an **endogenous hydrocarbon supply and price module** that integrates with Temoa/OEO. The module would:

### 3.1 Represent Regional Supply

- **Supply curves** for each fuel in each region (upward-sloping, piecewise-linear)
- Captures: regional resource endowments, extraction costs, production capacity
- Marginal cost increases as production increases

### 3.2 Enable Inter-Regional Trade

- **Trade flows** between US regions for pipeline-transportable fuels
- Bilateral capacity constraints (pipeline capacity, logistics)
- Transport costs and losses
- Prices equalize across regions (up to transport cost)

### 3.3 Model International Trade

- **Imports and exports** to/from world markets
- Net-export demand curves (US is large enough to affect world prices)
- Captures: LNG exports, petroleum product trade, Canadian gas imports

### 3.4 Capture Product Interrelationships

- **Refinery yield constraints** linking gasoline, diesel, jet fuel, etc.
- **Associated gas** from oil production
- Reflects physical/economic coupling between fuel products

### 3.5 Produce Endogenous Prices

- **Regional fuel prices** emerge as shadow prices of market balance constraints
- Prices respond to supply/demand conditions
- Technology choice responds to prices
- Full equilibrium within the optimization

---

## 4. What This Is (and Isn't)

### This IS:

- An extension of Temoa's commodity network "upstream" into fuel supply
- A partial equilibrium model of fuel markets integrated with energy system optimization
- Designed to capture fuel price dynamics, regional variation, and trade
- LP-compatible (piecewise-linear formulation preserves tractability)

### This is NOT:

- A general equilibrium model (no economy-wide feedback, no income effects)
- A replacement for detailed refinery models (stylized representation)
- A short-term market simulation (annual/multi-year resolution, not hourly)
- A stand-alone fuel market model (integrated with Temoa energy system)

---

## 5. Relationship to Other Models

### NEMS (EIA's National Energy Modeling System)

NEMS includes detailed modules for oil, gas, and coal supply. Our approach draws inspiration from NEMS but differs in:

- **Integration**: Embedded in optimization framework (Temoa) rather than simulation
- **Scope**: Focused on US regional markets, not global supply chains
- **Resolution**: Aggregated (9 regions, annual) vs. NEMS's greater detail
- **Data**: We can leverage NEMS documentation and data where applicable

### GCAM, TIMES/MARKAL, ReEDS

Other energy models handle fuel supply with varying sophistication:

- GCAM: Global resource supply curves, but aggregated US representation
- TIMES/MARKAL: Can represent supply curves, but often simplified
- ReEDS: Electricity-focused, simple fuel price inputs

Our module would give OEO/Temoa one of the more sophisticated fuel supply representations among open-source energy system models.

---

## 6. Scope Boundaries

### In Scope (for this initiative):

- **Fuels**: Gasoline, diesel, jet fuel, LPG/NGLs, residual fuel oil, pipeline natural gas, LNG
- **Geography**: 9 US regions, plus international trade
- **Features**: Supply curves, inter-regional trade, international trade, product interrelationships
- **Integration**: Full integration with Temoa optimization

### Out of Scope (for now):

- **Upstream detail**: Exploration, drilling, field development decisions
- **Refinery operations**: Detailed unit-level refinery modeling
- **Short-term dynamics**: Inventory management, spot markets, price volatility
- **Global markets**: Detailed modeling of non-US supply (captured via trade curves)
- **Coal**: May be added later but not initial focus
- **Hydrogen/e-fuels**: Handled by existing Temoa structures

### Uncertain (needs group input):

- **Crude oil**: Explicit commodity or implicit in refined products?
- **Biofuels**: Full integration or separate treatment?
- **Canada/Mexico**: Within 9-region structure or separate international?

---

## 7. Success Criteria

The module will be successful if:

1. **Regional fuel prices are endogenous** and respond to supply/demand conditions
2. **Inter-regional trade flows** emerge from price differentials and transport costs
3. **International trade** responds to domestic market conditions
4. **Product interrelationships** (refinery yields, associated gas) are captured
5. **Model remains tractable** (solve times acceptable for scenario analysis)
6. **Results are plausible** (prices, flows, responses pass sanity checks)
7. **Validated against data** (historical prices, trade flows, production patterns)

---

## 8. Next Steps

This framing memo sets the stage. The detailed scoping decisions are presented in:

- **[02_decision_framework.md](02_decision_framework.md)** — The complete decision landscape: mechanisms, choices, dependencies
- **[03_scope_packages.md](03_scope_packages.md)** — Three coherent scope bundles with trade-offs

Key questions for the working group:

1. **Crude oil: explicit or implicit?** (Foundational choice — shapes everything)
2. **International trade: price-taker or demand curves?** (Affects price dynamics)
3. **Which scope package (A/B/C)?** (What we build)
4. **Who owns what?** (Data, implementation, expertise areas)

---

*Next: [02_decision_framework.md](02_decision_framework.md) — The complete decision landscape*
