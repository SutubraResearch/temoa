# OEO Hydrocarbon Module — Working Group Materials

**Prepared for**: Hydrocarbon Module Working Group  
**Date**: January 2026  
**Status**: Pre-Meeting Materials for Scoping Discussion

---

## Document Index

**Start here:**

| Document | Description | Priority |
|----------|-------------|----------|
| [01_framing_memo.md](01_framing_memo.md) | Why this project, vision, and scope boundaries | Context |
| [02_decision_framework.md](02_decision_framework.md) | **The core mechanisms, decision hierarchy, and all options** | Essential |
| [03_scope_packages.md](03_scope_packages.md) | **Three coherent scope bundles (A/B/C) with trade-offs** | Essential |

**Reference:**

| Document | Description |
|----------|-------------|
| [04_data_requirements.md](04_data_requirements.md) | Data needs, potential sources, and identified gaps |
| [05_glossary.md](05_glossary.md) | Terminology, notation, and acronyms |

---

## How to Use These Materials

### Before the Meeting

**Minimum read** (30-40 min):
1. Skim the Framing Memo (01) for context
2. Read the Decision Framework (02) — understand the mechanisms and key decisions
3. Read the Scope Packages (03) — understand the three options

**Deeper dive** (additional 20-30 min):
4. Review Data Requirements (04) — especially gaps relevant to your expertise
5. Reference the Glossary (05) as needed

### At the Meeting

We need to resolve:

**Tier 1 (Foundational)**:
- Crude oil: explicit or implicit?
- International trade: price-taker or demand curves?

**Tier 2 (Core Scope)**:
- Product coupling method
- Inter-regional trade detail
- Canada/Mexico treatment

**Scope Package Selection**:
- Which package (A/B/C) aligns with OEO's needs?
- What's the phasing approach?

---

## Context

These materials build on the original concept note ("OEO Hydrocarbon Minimum Viable Product," December 2025). They formalize the scoping decisions needed to move forward with implementation.

### What This Module Does

Replace OEO's current fuel supply representation (exogenous prices) with:

- **Regional supply curves** — fuel costs vary by region and quantity
- **Inter-regional trade** — fuel moves between US regions via pipelines, etc.
- **International trade** — US imports/exports interact with world markets
- **Endogenous prices** — fuel prices emerge from supply-demand balance
- **Product coupling** — petroleum products are appropriately linked

### Why It Matters

- Fuel prices affect technology choice (EVs vs ICE, heat pumps vs gas furnaces)
- Current fixed prices miss supply constraints, market feedback, and endogenous price dynamics
- Decarbonization scenarios stress fuel markets in ways we can't currently capture

---

## Working Group Expertise

This effort requires input from:

| Expertise | Key Contributions |
|-----------|-------------------|
| **Temoa developers** | Implementation feasibility, code architecture |
| **Refinery engineers** | Product coupling realism, yield parameters |
| **Energy data (EIA)** | Data availability, NEMS comparison, what's practical |
| **All** | What questions must the module answer? |

---

## Key Decisions Summary

| Decision | Options | Status |
|----------|---------|--------|
| Crude oil explicit? | Implicit / Explicit | **Needs resolution** |
| International pricing | Fixed / Demand curves / Hybrid | **Needs resolution** |
| Product coupling | Soft / Bounded / Refinery | **Needs resolution** |
| Inter-regional trade | Corridors / Full network | **Needs resolution** |
| Canada/Mexico | International / Integrated / Bilateral | **Needs resolution** |
| Scope package | A (Foundation) / B (Core) / C (Full) | **Needs resolution** |

---

## Questions?

Contact [working group lead] with questions before the meeting.
