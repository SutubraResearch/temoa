# Decision Framework: Endogenous Hydrocarbon Module

**Purpose**: Present the complete decision landscape for scoping the hydrocarbon module. This document defines the mechanisms, the choices, and how they relate.

---

## 1. The Six Core Mechanisms

The hydrocarbon module consists of six interconnected mechanisms:

| Mechanism | What It Does |
|-----------|--------------|
| **Regional Supply** | Determines where fuel comes from within each region (production) |
| **Inter-Regional Trade** | Moves fuel between US regions (pipelines, rail, etc.) |
| **International Trade** | Connects US to world markets (imports/exports) |
| **Market Clearing / Prices** | Determines regional fuel prices through supply-demand balance |
| **Product Coupling** | Links related fuels (gasoline, diesel, jet from same crude) |
| **Crude Oil / Refineries** | Optionally models the crude-to-products supply chain |

All fuels remain in the model. The question is **how** each mechanism is represented, not whether.

---

## 2. The Decision Hierarchy

Not all decisions are equal. Some are foundational; others are details.

### Tier 1: Foundational (Decide First)

| Decision | Why It's Foundational |
|----------|----------------------|
| **Crude oil: explicit or implicit?** | Determines entire petroleum supply chain structure |
| **International trade: price-taker or demand curves?** | Determines whether US actions affect world prices |

### Tier 2: Core Scope

| Decision | Why It Matters |
|----------|---------------|
| **Product coupling method** | How gasoline/diesel/jet relate (depends on crude decision) |
| **Inter-regional trade completeness** | Affects spatial price equilibrium |
| **Canada/Mexico treatment** | Special case of international trade |

### Tier 3: Detail Choices

| Decision | Impact |
|----------|--------|
| Supply curve resolution | Price smoothness vs. model size |
| LNG vs. pipeline gas distinction | Trade representation accuracy |
| Associated gas coupling | Links gas supply to oil production |
| Time dynamics of supply curves | Static vs. evolving resource base |

---

## 3. All Decisions by Mechanism

### 3.1 Regional Supply

Every fuel needs a supply representation. The current approach (exogenous prices, which may vary by region but don't respond to conditions) is replaced with endogenous supply curves.

| Decision | Options | Trade-offs |
|----------|---------|------------|
| **Structure** | Piecewise-linear blocks | Standard approach, LP-compatible |
| **Resolution** | Coarse (3-5 blocks) / Medium (5-7) / Fine (10+) | More blocks = smoother prices, larger model |
| **Time dynamics** | Static curves / Time-varying / Cumulative depletion | Realism vs. complexity, myopic compatibility |
| **Regional differentiation** | Same curves all regions / Region-specific | Data availability, regional realism |

**Recommendation**: Medium resolution (5-7 blocks), time-varying, region-specific where data supports.

---

### 3.2 Inter-Regional Trade

How fuels move between the 9 US regions.

| Decision | Options | Trade-offs |
|----------|---------|------------|
| **Network structure** | Major corridors only / Full bilateral / Infrastructure-based | Realism vs. complexity |
| **Transport costs** | Include / Exclude | Affects price spreads, data needs |
| **Capacity constraints** | None / Fixed caps / Time-varying | Reflects infrastructure limits |
| **Investment decisions** | Fixed infrastructure / Endogenous expansion (MILP) | Complexity, solve time |

**How it affects prices**: Trade creates spatial arbitrage. If regions can trade freely, prices equalize (minus transport cost). Capacity constraints allow price divergence.

**Recommendation**: Major corridors with capacity constraints, fixed infrastructure for MVP.

---

### 3.3 International Trade

How the US interacts with world markets. This is a **Tier 1 decision**.

| Decision | Options | Trade-offs |
|----------|---------|------------|
| **Import pricing** | Fixed world price / Stepped / Demand curve | Simplicity vs. price responsiveness |
| **Export pricing** | Fixed world price / Stepped / Demand curve | Simplicity vs. price responsiveness |
| **Quantity constraints** | None / Import caps / Export caps / Both | Reflects infrastructure, policy |
| **Regional access** | All regions / Coastal + border only | Realism |
| **Canada/Mexico** | As "international" / Integrated with US / Special bilateral | Reflects pipeline integration |
| **Fuel-specific treatment** | Same for all / Different by fuel | Gas may need demand curves, products may not |

#### The Key Question: Is the US a Price-Taker?

| Fuel | US Role in World Market | Implication |
|------|------------------------|-------------|
| **Crude oil** | Large importer, but global market is huge | Probably price-taker (fixed prices okay) |
| **Petroleum products** | Modest net exporter | Probably price-taker |
| **Natural gas (pipeline)** | Integrated with Canada | Special treatment needed |
| **LNG** | Now major exporter, affects global prices | Demand curves make sense |

**Recommendation**: 
- Demand curves for LNG exports (US affects world price)
- Fixed prices with caps for petroleum products
- Special bilateral treatment for Canada/Mexico pipeline gas

---

### 3.4 Market Clearing and Prices

How regional fuel prices are determined. This is mostly automatic from the LP structure.

| Decision | Options | Notes |
|----------|---------|-------|
| **Price determination** | Shadow prices of balance constraint | Standard, automatic |
| **Spatial equilibrium** | Emergent / Explicit arbitrage constraints | Emergent is sufficient, explicit is redundant but verifiable |
| **Price reporting** | Extract duals post-solve / Explicit variables | Post-solve extraction is simpler |

#### How Prices Work

**Regional fuel balance constraint**:
```
Supply_r + Trade_in_r + Imports_r = Demand_r + Trade_out_r + Exports_r
```

**Shadow price of this constraint = regional market price**

The optimizer:
1. Dispatches supply blocks in merit order (cheapest first)
2. Routes trade flows toward price differentials
3. Uses imports/exports based on international price
4. Finds the equilibrium where all balances hold

**Price = marginal cost of the last unit supplied** (whether from a supply block, trade, or import)

#### Spatial Price Equilibrium

If regions r and r' can trade:
- P_r' <= P_r + transport_cost (or trade flows from r to r')
- If trade is at capacity, prices can differ by more

This **emerges automatically** from the optimization. No explicit "price arbitrage" constraint is needed.

#### With International Demand Curves

If using demand curves P = γ + δX (where X = net exports):
- US exports push down world price (δ > 0 for export demand)
- US imports push up world price (δ < 0 for import supply)
- Domestic price equilibrates with world price (adjusted for transport)

**Recommendation**: Standard LP approach. Shadow prices for regional prices. Demand curves for LNG where US affects world market.

---

### 3.5 Product Coupling (Petroleum)

How are gasoline, diesel, jet fuel, LPG, and residual fuel oil related?

| Decision | Options | Trade-offs |
|----------|---------|------------|
| **Coupling approach** | None / Soft bounds / Bounded ratios / Fixed ratios / Explicit refineries | Independence -> full physical realism |
| **Constraint form** | Inequality (<=) / Range (<= and >=) / Equality (=) | Flexibility vs. tightness |
| **Regional variation** | Same everywhere / Region-specific | Reflects refinery configurations |

#### Options Explained

**None**: Each petroleum product has independent supply. Unrealistic but simple.

**Soft bounds**: 
```
D_gasoline <= α_g × TotalPetroleum + slack
```
Limits how much of one product can dominate.

**Bounded ratios**:
```
ρ_lower × D_diesel <= D_gasoline <= ρ_upper × D_diesel
```
Products must stay in realistic proportions.

**Fixed ratios** (strict refinery yields):
```
D_gasoline / α_g = D_diesel / α_d = D_jet / α_j = ...
```
Products come out in fixed proportions. Very restrictive.

**Explicit refineries**: Crude oil is input, products are outputs. Yields are technology parameters. (See 3.6)

**Recommendation**: Bounded ratios for MVP. Explicit refineries if crude is explicit.

---

### 3.6 Crude Oil and Refineries

This is a **Tier 1 decision**. Two fundamentally different approaches:

#### Option A: Implicit Crude (Products Directly)

- **No crude oil commodity** in the model
- Each refined product (gasoline, diesel, etc.) has its own supply curve
- Product coupling via constraints (Section 3.5)
- Simpler, fewer variables, less data

**What you can answer**: Regional product prices, trade flows, price impacts of demand changes

**What you can't easily answer**: Crude price impacts, refinery economics, crude slate optimization

#### Option B: Explicit Crude (Refinery Technologies)

- **Crude oil is a commodity** with supply curves
- **Refinery technologies** convert crude to products
- Products emerge from refinery yields (automatic coupling)
- Associated gas naturally linked to crude production
- More complex, more data, richer analysis

**What you can answer**: All of Option A, plus crude price impacts, refinery margins, associated gas

**Sub-decisions if explicit**:
| Decision | Options |
|----------|---------|
| Crude differentiation | Single crude / Light-heavy split / Full slate |
| Refinery types | Single aggregate / Simple vs. complex / Regional specifics |
| Refinery investment | Fixed capacity / Endogenous (MILP) |

**Recommendation**: This is the key strategic choice for the working group. Suggest implicit crude for faster MVP, explicit as future enhancement.

---

### 3.7 Natural Gas Specifics

| Decision | Options | Trade-offs |
|----------|---------|------------|
| **Pipeline vs. LNG** | Single commodity / Separate | LNG has different trade patterns |
| **Associated gas** | Not modeled / Constraint (gas >= β × oil) | Links gas supply to oil production |
| **Flaring** | Not modeled / Capped fraction | Environmental relevance, adds complexity |
| **Canada/Mexico pipeline** | As international / Integrated | Reflects physical pipeline network |

**Recommendation**: Separate LNG commodity. Associated gas as enhancement. Canada pipeline as special bilateral.

---

## 4. Decision Dependencies

```
┌─────────────────────────────────────────────────────────────────┐
│                    TIER 1: FOUNDATIONAL                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────┐      ┌──────────────────────────┐   │
│   │ CRUDE OIL           │      │ INTERNATIONAL TRADE      │   │
│   │ Explicit or         │      │ Price-taker or           │   │
│   │ Implicit?           │      │ Demand curves?           │   │
│   └──────────┬──────────┘      └──────────────────────────┘   │
│              │                            │                    │
│              │ Determines                 │ Independent        │
│              ▼                            │                    │
│   ┌─────────────────────┐                │                    │
│   │ PRODUCT COUPLING    │                │                    │
│   │ - If implicit:      │                │                    │
│   │   constraints       │                │                    │
│   │ - If explicit:      │                │                    │
│   │   refinery yields   │                │                    │
│   └─────────────────────┘                │                    │
│              │                            │                    │
│              │ Determines                 │                    │
│              ▼                            │                    │
│   ┌─────────────────────┐                │                    │
│   │ ASSOCIATED GAS      │                │                    │
│   │ - If implicit crude:│                │                    │
│   │   awkward           │                │                    │
│   │ - If explicit crude:│                │                    │
│   │   natural coupling  │                │                    │
│   └─────────────────────┘                │                    │
│                                          │                    │
├─────────────────────────────────────────────────────────────────┤
│                    TIER 2: CORE SCOPE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────┐      ┌──────────────────────────┐   │
│   │ INTER-REGIONAL      │      │ CANADA/MEXICO            │   │
│   │ TRADE DETAIL        │      │ TREATMENT                │   │
│   │ (Independent)       │      │ (Special case of int'l)  │   │
│   └─────────────────────┘      └──────────────────────────┘   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                    TIER 3: DETAILS                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Supply curve resolution    LNG specifics    Time dynamics    │
│   (Independent)              (Independent)    (Independent)    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. What Each Element Enables

| Scope Element | Questions It Answers |
|---------------|---------------------|
| **Regional supply curves** | How do regional production costs affect prices? What's the marginal supply source? |
| **Inter-regional trade** | How do pipeline constraints affect regional price spreads? Where are bottlenecks? |
| **Trade capacity constraints** | What happens when infrastructure is tight? Value of expansion? |
| **International demand curves** | How do LNG exports affect domestic gas prices? How does US affect world price? |
| **Fixed international prices** | Scenario analysis: "What if world oil price is $X?" (exogenous, not endogenous) |
| **Product coupling (soft)** | Approximate refinery constraints on product mix |
| **Product coupling (bounded ratios)** | How do refinery yield limits affect relative product prices? |
| **Explicit refineries** | How does crude price affect product prices? Refinery investment? Crude slate? |
| **Associated gas constraint** | How does oil production growth affect gas supply? Flaring economics? |

---

## 6. Summary: Key Questions for Working Group

### Tier 1 Decisions (Must Resolve)

**1. Crude Oil: Explicit or Implicit?**
- Explicit: Full crude-to-products chain, refineries, richer analysis, more complex
- Implicit: Products directly, coupling via constraints, simpler, faster

**2. International Trade: Price-Taker or Demand Curves?**
- Price-taker: Fixed world prices, US doesn't affect them, simpler
- Demand curves: World prices respond to US trade, more realistic for LNG
- Hybrid: Demand curves for gas/LNG, fixed for petroleum products?

### Tier 2 Decisions

**3. Product Coupling Method** (if crude is implicit)
- Soft bounds / Bounded ratios / Fixed ratios?
- How tight? Regional variation?

**4. Inter-Regional Trade**
- Full network or major corridors?
- Fixed infrastructure or investment decisions?

**5. Canada/Mexico**
- Treat as international (like rest of world)?
- Integrate with US (like domestic regions)?
- Special bilateral (explicit trade routes)?

### Tier 3 Decisions (Can Resolve Later)

**6. Supply Curve Resolution**: 3-5 blocks? 5-7? 10+?

**7. LNG Treatment**: Separate commodity or part of natural gas?

**8. Associated Gas**: Model it? Link to oil production?

---

*Next document: [03_scope_packages.md](03_scope_packages.md) — Coherent scope bundles*
