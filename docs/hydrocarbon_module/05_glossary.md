# Glossary and Notation Reference

**Purpose**: Ensure consistent terminology across documents and discussions.

---

## Notation from Concept Note

### Sets and Indices

| Symbol | Description |
|--------|-------------|
| R = {1, ..., 9} | Regions (9 US regions in OEO) |
| r, r' | Region indices |
| F | Set of fuels: {g, d, j, l, o, n, q} |
| f | Fuel index |
| B_f | Set of supply curve blocks for fuel f |
| b | Block index |
| K_{f,r} | Set of demand curve segments for international trade |
| k | Segment index |
| p | Period (year or multi-year period) |

### Fuels

| Symbol | Fuel |
|--------|------|
| g | Gasoline |
| d | Diesel |
| j | Jet fuel |
| l | LPG / NGLs (liquefied petroleum gas / natural gas liquids) |
| o | Residual fuel oil |
| n | Pipeline natural gas |
| q | LNG (liquefied natural gas) |
| c | Crude oil (when explicitly modeled) |

### Variables

| Symbol | Description | Units |
|--------|-------------|-------|
| s_{f,r,b} | Production from supply block b | quantity/year |
| S_{f,r} | Total regional supply (Σ s_{f,r,b}) | quantity/year |
| T_{f,r->r'} | Inter-regional trade flow from r to r' | quantity/year |
| M^{imp}_{f,r} | Imports from international markets | quantity/year |
| M^{exp}_{f,r} | Exports to international markets | quantity/year |
| X_{f,r} | Net exports (M^{exp} - M^{imp}) | quantity/year |
| D_{f,r} | Regional demand for fuel f | quantity/year |
| F_r | Flaring (if modeled) | quantity/year |
| P_{f,r} | Regional price (shadow price) | $/unit |

### Parameters

| Symbol | Description | Units |
|--------|-------------|-------|
| s̄_{f,r,b} | Maximum supply from block b | quantity/year |
| λ_{f,r,b} | Marginal cost of block b | $/unit |
| T̄_{f,r->r'} | Maximum trade capacity | quantity/year |
| τ_{f,r->r'} | Transport cost | $/unit |
| M̂^{imp}_{f,r} | Maximum import capacity | quantity/year |
| M̂^{exp}_{f,r} | Maximum export capacity | quantity/year |
| γ_{f,r,k} | Intercept of demand curve segment k | $/unit |
| δ_{f,r,k} | Slope of demand curve segment k | $/unit² |
| α_f | Normalized refinery yield coefficient | fraction |
| ρ_{f,f'}, ρ̄_{f,f'} | Bounds on product ratio D_f/D_{f'} | dimensionless |
| β_r | Associated gas ratio | MCF/bbl |
| φ_r | Maximum flaring fraction | fraction |
| Ā_r | Maximum non-associated gas | quantity/year |

### Equations (Reference)

**Fuel Balance**:
$$S_{f,r} + \sum_{r' \neq r} T_{f,r' \rightarrow r} + M^{imp}_{f,r} = D_{f,r} + \sum_{r' \neq r} T_{f,r \rightarrow r'} + M^{exp}_{f,r}$$

**Supply Curve**:
$$S_{f,r} = \sum_{b \in B_f} s_{f,r,b} \quad \text{where} \quad 0 \leq s_{f,r,b} \leq \bar{s}_{f,r,b}$$

**Supply Cost**:
$$C_{f,r}(S_{f,r}) = \sum_{b \in B_f} \lambda_{f,r,b} \cdot s_{f,r,b}$$

**Shadow Price / Market Price**:
$$P_{f,r} = \text{dual}(\text{Fuel Balance Constraint})$$

---

## Temoa Terminology

### Core Concepts

| Term | Definition |
|------|------------|
| **Commodity** | An energy carrier or material flowing through the system. Types: source, physical, demand, emissions. |
| **Technology** | A process that transforms input commodities to output commodities. Defined by efficiency, costs, capacity. |
| **Vintage** | The year a technology unit is installed. Affects costs, efficiency, lifetime. |
| **Period** | A time block in the optimization (e.g., 2025, 2030). Typically multi-year. |
| **Region** | A geographic unit. OEO uses 9 US regions. |
| **Capacity** | The maximum output rate of a technology (MW, bbl/day, etc.). |
| **Activity** | The actual output of a technology in a period (MWh, bbl, etc.). |

### Key Variables in Temoa

| Variable | Description |
|----------|-------------|
| `v_flow_out` | Output flow from a technology (by region, period, season, time-of-day, input, tech, vintage, output) |
| `v_flow_out_annual` | Annual output flow (for annual technologies) |
| `v_capacity` | Capacity of a technology (by region, period, tech, vintage) |
| `v_new_capacity` | New capacity added in a period |

### Key Parameters in Temoa

| Parameter | Description |
|-----------|-------------|
| `efficiency` | Output/input ratio for a technology |
| `cost_invest` | Capital cost ($/unit capacity) |
| `cost_fixed` | Fixed O\&M cost ($/unit capacity/year) |
| `cost_variable` | Variable O\&M cost ($/unit output) |
| `lifetime_process` | Operational lifetime of a technology |
| `existing_capacity` | Pre-existing capacity at model start |

### Relevant Temoa Structures

| Structure | Description | Relevance |
|-----------|-------------|-----------|
| `tech_exchange` | Technologies for inter-regional transfer | Basis for inter-regional fuel trade |
| `limit_activity` | Constraint on technology activity | Can cap supply blocks |
| `limit_resource` | Cumulative resource constraint | Could limit total extraction |
| `commodity_physical` | Intermediate energy commodities | Fuels will be physical commodities |
| `tech_annual` | Technologies with annual (not time-slice) output | Most fuel supply is annual |

### Shadow Prices in Temoa

Shadow prices (dual values) from constraints provide economic interpretations:

| Constraint | Shadow Price Interpretation |
|------------|----------------------------|
| Commodity balance | Marginal cost of supplying one more unit = market price |
| Capacity constraint | Marginal value of capacity = rent |
| Demand constraint | Marginal cost of meeting demand = willingness to pay |

---

## Equilibrium Terminology

| Term | Definition |
|------|------------|
| **Partial Equilibrium (PE)** | Analysis of a single market/sector holding other markets constant. Temoa is a PE model. |
| **General Equilibrium (GE)** | All markets clear simultaneously. Requires economy-wide modeling. |
| **Supply Curve** | Relationship between quantity supplied and price. Upward-sloping: higher price -> more supply. |
| **Demand Curve** | Relationship between quantity demanded and price. Downward-sloping: higher price -> less demand. |
| **Market Clearing** | Condition where supply equals demand. Price adjusts to achieve this. |
| **Shadow Price** | Marginal value of a constrained resource. In LP, equals dual variable of constraint. |
| **Spatial Equilibrium** | Equilibrium across geographically separated markets connected by trade. Prices differ by transport cost. |

---

## Industry Terminology

### Petroleum

| Term | Definition |
|------|------------|
| **Crude oil** | Unrefined petroleum extracted from the ground |
| **Refinery** | Facility that converts crude oil into refined products |
| **Refinery yield** | Fraction of each product obtained from a barrel of crude |
| **Cracking** | Process to convert heavy molecules to lighter ones (increases gasoline yield) |
| **Coking** | Process to convert residual to lighter products (complex refineries) |
| **PAD District** | Petroleum Administration for Defense District (5 regions used by EIA) |
| **Product slate** | Mix of products produced by a refinery |
| **Crack spread** | Price difference between crude and refined products (refinery margin indicator) |

### Natural Gas

| Term | Definition |
|------|------------|
| **Pipeline gas** | Natural gas transported via pipeline (gaseous form) |
| **LNG** | Liquefied natural gas (cooled to liquid for ship transport) |
| **Associated gas** | Natural gas produced alongside crude oil |
| **Non-associated gas** | Natural gas from gas-only fields |
| **NGL** | Natural gas liquids (ethane, propane, butane extracted from gas stream) |
| **City gate** | Delivery point where pipeline meets local distribution system |
| **Henry Hub** | Benchmark pricing point for US natural gas |
| **Shale gas** | Natural gas extracted from shale formations (horizontal drilling + fracking) |

### Trade

| Term | Definition |
|------|------------|
| **Net exports** | Exports minus imports. Positive = net exporter, negative = net importer. |
| **Trade balance** | Supply + imports = demand + exports |
| **Bilateral trade** | Trade between two specific regions |
| **Trade capacity** | Maximum flow between regions (limited by infrastructure) |
| **Transport cost** | Cost to move commodity between regions |
| **Arbitrage** | Buying in low-price region, selling in high-price region (equalizes prices) |

---

## Acronyms

| Acronym | Expansion |
|---------|-----------|
| OEO | Open Energy Outlook |
| NEMS | National Energy Modeling System (EIA) |
| AEO | Annual Energy Outlook (EIA publication) |
| LP | Linear Program / Linear Programming |
| MILP | Mixed-Integer Linear Program |
| QP | Quadratic Program |
| NLP | Nonlinear Program |
| PE | Partial Equilibrium |
| GE | General Equilibrium |
| CGE | Computable General Equilibrium |
| EIA | Energy Information Administration |
| FERC | Federal Energy Regulatory Commission |
| PAD | Petroleum Administration for Defense (District) |
| LNG | Liquefied Natural Gas |
| NGL | Natural Gas Liquids |
| LPG | Liquefied Petroleum Gas |
| ICE | Internal Combustion Engine |
| EV | Electric Vehicle |
| MMBtu | Million British Thermal Units |
| MCF | Thousand Cubic Feet (gas volume) |
| BCF | Billion Cubic Feet |
| bbl | Barrel (oil, ~42 gallons) |

---

## Regional Concordance (OEO 9 Regions)

*Note: Exact regional definitions should be confirmed with OEO documentation*

| Region | Description | Key Characteristics |
|--------|-------------|---------------------|
| R1 | New England | Net importer, limited pipelines |
| R2 | Mid-Atlantic | Major refining, pipeline hub |
| R3 | South Atlantic | Growing demand, some refining |
| R4 | East North Central | Industrial demand, pipeline transit |
| R5 | East South Central | Refining, gas production |
| R6 | West North Central | Agricultural, limited production |
| R7 | West South Central | Major production (Texas), refining |
| R8 | Mountain | Gas production, transit |
| R9 | Pacific | Isolated market, imports |

*This table is illustrative. Actual regional definitions should be verified.*

---

*End of glossary*
