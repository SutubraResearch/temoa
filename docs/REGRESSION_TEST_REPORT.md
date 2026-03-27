# Regression Test Report: Isolating Performance-Critical Code Changes

**Date:** 2026-03-09
**Server:** AMD EPYC 7713 64-Core, Gurobi 13.0.1, 400 GB RAM
**Model:** National 52-week, myopic, Period 1 (2027), 16 regions

## 1. Objective

We have 15 commits on `db-migration/mip-dev` that bring the v4 codebase to result parity
with mip-dev while solving 1.5x faster. Before proposing these changes upstream, we need to
know which ones actually matter for performance. This report documents server regression tests
that isolate each performance-oriented code change by reverting it and measuring the impact
on the national 52-week model.

**Goal:** Minimize the upstream diff by identifying changes we can safely drop.

## 2. Methodology

Each test creates a branch off `db-migration/mip-dev` that reverts exactly ONE code change.
The same national 52-week v4 database is used for all tests (with one exception noted below).
All tests use identical solver configuration (BarOrder=-1, BarConvTol=1e-3, FeasibilityTol=1e-4,
Method=2, Crossover=0). Only Period 1 (2027) was run — sufficient to measure barrier performance
impact without burning 8+ additional hours on Period 2.

### Baseline

The baseline is `db-migration/mip-dev` with all 15 commits applied — the same code that produced
the validated results in the original handoff report (2026-03-05). Baseline P1 barrier time:
**2,456 seconds**, 115 iterations, objective 3.903e+11.

### Tests

| Test | Branch | What was reverted | DB modification |
|------|--------|-------------------|-----------------|
| **A1** | `test/demand-annual` | Timeslice-level demand rewrite reverted to upstream annual formulation | Demand techs (`elec_distribution`, `CO2_Offset`, `Dummy_Offset`) set to `annual=1` in technology table |
| **A2** | `test/demand-annual` | Same code as A1 | None — demand techs remain non-annual (negative control) |
| **B** | `test/no-storage-init` | `v_storage_init` variable removed, storage constraint reverted to upstream closed-cycle (`time_next`) | None |
| **C** | `test/season-ramp` | Season ramp skip for `seasonal_timeslices` reverted — ramp constraints re-enabled at season boundaries | None |

**Why two demand tests?** The upstream demand formulation was designed to work with demand techs
tagged `annual=1` in the database (per the upstream developer). A1 tests the intended configuration;
A2 tests what happens without the DB fix (demand techs have both timeslice and annual variables,
linked by DemandActivity equality constraints — the "dense column" problem our rewrite solved).

## 3. Results

### 3.1 Summary Table (Period 1, 2027)

| Metric | Baseline | A1 | A2 | B | C |
|--------|----------|-----|-----|---|---|
| **Barrier time (s)** | **2,456** | **3,509 (+43%)** | **3,065 (+25%)** | **3,072 (+25%)** | **still running (~19,600 est.)** |
| Iterations | 115 | 114 | 126 | 118 | 18+ (running) |
| Factor Ops | 2.846e+11 | 2.872e+11 | 2.860e+11 | 2.906e+11 (+2.1%) | **4.449e+13 (156x)** |
| Dense columns | 1,294 | 1,294 | 1,295 | 1,294 | 1,294 |
| Presolved rows | 17,733,334 | 17,733,334 | 17,742,070 | 17,740,094 | 17,743,526 |
| Presolved cols | 17,920,134 | 17,920,134 | 17,928,871 | 17,920,134 | 17,920,134 |
| Ordering time (s) | 129 | 164 | 146 | 136 | **3,519 (27x)** |
| Presolve time (s) | 177 | 203 | 213 | 215 | 241 |
| Pre-presolve vars | 33,055,320 | 32,356,520 | 33,055,400 | 33,045,284 | 33,055,320 |
| Objective | 3.903e+11 | 3.903e+11 | 3.903e+11 | 3.903e+11 | converging |

### 3.2 Test A: Demand Formulation

**Verdict: KEEP our timeslice-level demand rewrite.**

Both upstream alternatives are significantly slower than baseline:

- **A1 (+43%):** With demand techs tagged `annual=1`, the upstream code eliminates their
  timeslice-level `v_flow_out` variables entirely. This reduces the pre-presolve model by ~700K
  variables (32.36M vs 33.06M). But after presolve, the models are identical size (17.73M rows,
  17.92M cols). Despite this, barrier time increases by 1,053 seconds. The extra time comes from
  ordering (+27%) and slower per-iteration progress — the ordering algorithm takes longer to find
  a good elimination order (164s vs 129s), suggesting the reduced variable set paradoxically gives
  the ordering less structure to work with.

- **A2 (+25%):** Without the DB fix, demand techs get both `v_flow_out` and `v_flow_out_annual`,
  linked by DemandActivity equality constraints. Surprisingly this is faster than A1 — the
  DemandActivity constraints apparently give Gurobi more presolve reduction opportunities (it
  eliminates 15.1M columns vs A1's 14.2M). The equality constraints are easily substituted away,
  and the extra structure helps ordering. But it's still 25% slower than our baseline, likely due
  to the DemandActivity constraints surviving presolve at scale and adding fill-in to the
  factorization.

- **Baseline (our rewrite):** Demand techs get timeslice-level `v_flow_out` only. No
  `v_flow_out_annual`, no DemandActivity constraints. This is the cleanest formulation — fewer
  variables, fewer constraints, and the ordering algorithm handles it best.

**Conclusion:** The timeslice-level demand rewrite is not just a workaround — it produces a
fundamentally better LP structure than either upstream alternative. The upstream developer's
suggestion of tagging demand techs `annual=1` does work for correctness but is 43% slower.
Our code change is the right fix.

### 3.3 Test B: Storage Init (v_storage_init)

**Verdict: KEEP v_storage_init.**

Removing `v_storage_init` and reverting to the upstream closed-cycle (`time_next`) storage
formulation costs 25% barrier time — 616 seconds slower than baseline (3,072s vs 2,456s).

- **Factor Ops +2.1%:** The factorization workload increases modestly (2.906e+11 vs 2.846e+11),
  but the wall-clock impact is disproportionately large — each iteration takes ~26s vs ~21s for
  baseline. This suggests worse cache/memory behaviour from increased fill-in, not just more
  arithmetic.

- **Presolved rows +6,760:** The closed-cycle storage constraints that `v_storage_init`
  eliminated survive presolve (17,740,094 vs 17,733,334 rows). The column count is identical
  (17,920,134), confirming the extra rows are the cyclic linking constraints.

- **Ordering time +5%:** Modest increase (136s vs 129s). The open-chain topology gives the
  ordering algorithm better separator nodes, reducing fill-in in the Cholesky factorization.
  This is a smaller effect than the demand formulation (where ordering was +27%), but the
  per-iteration impact is significant.

- **Pre-presolve vars -10K:** The model is slightly smaller without `v_storage_init` variables
  (33,045,284 vs 33,055,320), but this minor reduction doesn't help — the structural advantage
  of the open chain outweighs the variable count reduction.

**Conclusion:** `v_storage_init` provides a 25% performance improvement by breaking the storage
energy balance from a closed cycle into an open chain. The cyclic `time_next` linkage forces the
barrier solver into denser factorizations. This is a meaningful structural improvement, not just
a minor optimization.

### 3.4 Test C: Season Ramp Constraints

**Verdict: KEEP the season ramp skip. Catastrophic performance regression.**

*Test still running at iter 18 / 6,420s wall time. Estimated total ~19,600s if convergence
matches baseline (~115 iterations).*

Re-enabling ramp constraints at season boundaries (reverting our `seasonal_timeslices` skip)
causes a catastrophic performance regression — the worst of all four tests by a wide margin.

- **Pre-presolve model:** 32,676,008 rows, 33,055,320 cols — nearly identical to baseline
  (32,667,872 rows). Only ~8K additional ramp constraints.
- **Presolve:** 241s (vs baseline 177s, +36%). Presolved to 17,743,526 rows — only +10,192
  rows vs baseline. Column count identical (17,920,134).
- **Ordering: 3,519 seconds** (vs baseline 129s — **27x slower**). The ~10K season ramp
  constraints add coupling between the last timeslice of one season and the first timeslice of
  the next. This creates cross-season edges in the constraint graph that destroy the
  near-block-diagonal structure that the ordering algorithm exploits. What were independent
  seasonal blocks become a single connected component, causing combinatorial explosion in the
  separator search.
- **Factor Ops: 4.449e+13** (vs baseline 2.846e+11 — **156x more**). This is the smoking gun.
  The bad ordering produces catastrophic fill-in in the Cholesky factorization. Factor NZ jumps
  to 2.408e+09 (~34 GB), compared to baseline where the entire solve including ordering fits
  comfortably in memory.
- **Per-iteration time: ~140s** (vs baseline ~21s — **7x slower**). Each barrier iteration
  performs one Cholesky factorization, and with 156x more Factor Ops the per-iteration cost
  explodes.
- **Convergence:** At iteration 18 (wall time 6,420s), primal objective is 1.87e+13 vs target
  3.90e+11. Still converging but far from optimal. If it follows baseline's ~115 iteration
  pattern, total barrier time would be ~16,100s + 3,519s ordering = ~19,600s (~5.4 hours for
  barrier + ordering alone, vs baseline 2,456s total — **8x slower overall**).

**Conclusion:** The season ramp skip is by far the most impactful change tested. A 2-line code
change (checking for `seasonal_timeslices` in addition to `consecutive_days`) prevents a
structural catastrophe. The ramp constraints are tiny in number (~10K out of 17.7M presolved
rows) but they connect parts of the matrix that were previously independent. The ordering
algorithm's performance is superlinear in connectivity, not linear in constraint count — this
is a textbook example of why sparse matrix structure matters more than matrix size.

## 4. Conclusions

### Changes confirmed necessary:
1. **Demand formulation (timeslice-level rewrite)** — 25-43% performance impact. Must keep.
2. **v_storage_init (open-chain storage)** — 25% performance impact. Must keep.

3. **Season ramp skip** — Catastrophic ordering regression (25x+). Must keep.

### Changes NOT tested (already justified):
- **BarOrder=-1:** 32x speedup, already validated
- **tech_uncap DB approach:** 33% speedup on 4-week, DB-only change (no code diff)
- **Solver tolerances:** Match mip-dev, no code change needed
- **Myopic capacity threshold:** Prevents P2 variable explosion, config-only
- **Bug fixes:** Correctness fixes, not performance-related

## 5. Files and Branches

### Branches (all off `db-migration/mip-dev`, 1 commit each):
- `test/demand-annual` — upstream demand code (commodities.py, flows.py, model.py)
- `test/no-storage-init` — upstream storage code (storage.py, model.py)
- `test/season-ramp` — upstream operations code (operations.py)

### Test databases:
- `test_A1_demand_annual.sqlite` — demand techs set `annual=1`
- `test_A2_demand_no_annual.sqlite` — unmodified copy
- `test_B_no_storage_init.sqlite` — unmodified copy
- `test_C_season_ramp.sqlite` — unmodified copy

### Configs and SLURM scripts:
- `data_files/my_configs/config_test_{A1,A2,B,C}.toml`
- `data_files/my_configs/submit_test_{A1,A2,B,C}.sh`

### Baseline log:
- `data_files/mip_migration_workspace/server_results/HANDOFF_REPORT.md` (Section 5)
