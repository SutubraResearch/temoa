# M2 → M5 Handoff: Temoa SRfork

Last updated: 2026-03-26, from M2 (MacBook, 16GB).

---

## 1. Where Things Stand

**All 5 upstream PRs were merged on 2026-03-20.** Our changes are now in `upstream/unstable`.

| PR | Title | Merged |
|----|-------|--------|
| [#271](https://github.com/TemoaProject/temoa/pull/271) | Fix 4 independent bugs | 2026-03-20 |
| [#272](https://github.com/TemoaProject/temoa/pull/272) | Output threshold + myopic capacity config | 2026-03-20 |
| [#273](https://github.com/TemoaProject/temoa/pull/273) | Solver tolerances + barrier ordering | 2026-03-20 |
| [#274](https://github.com/TemoaProject/temoa/pull/274) | Configurable demand resolution / DAC skip | 2026-03-20 |
| [#275](https://github.com/TemoaProject/temoa/pull/275) | v_storage_init for non-seasonal storage | 2026-03-20 |

**The `unstable` branch at `cb703e5` is the current working tip.** It has our PRs plus
additional upstream work (season rework, JSON-to-hash testing, data_files removal, Pyomo update,
typed extensions, myopic evolving features). All 199 tests pass locally.

**The primary mission was accomplished:** v4/unstable matches mip-dev results (gen shares
within +/-0.23pp nationally, 52-week, 16 regions) and v4 is faster (P1: 2,456s vs 3,698s).

---

## 2. Remotes

```
origin    git@github.com:SutubraResearch/temoa.git     (our fork)
upstream  https://github.com/TemoaProject/temoa.git     (upstream)
```

---

## 3. Branches That Matter

| Branch | What | Status |
|--------|------|--------|
| `unstable` | Tracks `upstream/unstable`. Current working branch. | Up to date at `cb703e5` |
| `db-migration/mip-dev` | Our stable internal branch (17 commits off fork point `c7cd1f9`) | **LOCAL is canonical.** Remote `origin/db-migration/mip-dev` is STALE (pre-rebase, diverged). Needs force-push if you ever want to sync it. |
| `mip-dev` | Original mip-dev code (Python 2-era, Pyomo 4) | Reference only. Don't run from v4 branches. |
| `mip-dev-52` | Patched mip-dev for Python 3.12+ with standalone runner | For comparison runs only |
| `pr/bug-fixes`, `pr/small-features`, `pr/solver-tuning`, `pr/demand-formulation`, `pr/storage-init` | PR submission branches | Merged upstream. Can be deleted. |
| `energysystem` | Raw upstream v4 code | **IGNORE.** Never use as a base for diffs or PRs. |
| `backup/db-migration-mip-dev-pre-rebase` | Safety backup | Keep for reference |
| `ECT`, `canada`, `fuel_supply_dev` | Other project branches | Unrelated to mip-dev migration |

### Branches safe to delete (merged upstream)
```
pr/bug-fixes
pr/small-features
pr/solver-tuning
pr/demand-formulation
pr/storage-init
feat/output-threshold-filtering
feat/restore-demand-activity
fix/limit-capacity-index-check
fix/output-curtailment-fk
test/demand-annual
test/no-storage-init
test/season-ramp
worktree-agent-*
```

---

## 4. Stashes on M2

These will NOT transfer with `git clone`. If you need them, pull from M2 directly.

| Index | Contents |
|-------|----------|
| `stash@{0}` | WIP on pr/demand-formulation — old DAC skip approach |
| `stash@{1}` | WIP on pr/demand-formulation — old config-matrix JSON caches |
| `stash@{2}` | mip-dev-52 model patches (Python 3.12 compat) |
| `stash@{3}` | mip-dev comparison run data |
| `stash@{4}–{8}` | Old WIPs from ECT, canada, main — probably not needed |

---

## 5. Internal-Only Commits (NOT Upstreamed)

These live on `db-migration/mip-dev` and were intentionally kept out of upstream PRs:

| Commit | What | Why internal |
|--------|------|--------------|
| `e9d6c56` | Env-var overrides (TEMOA_BAR_ORDER, etc.) | Server infrastructure only |
| `371014f` | TEMOA_PRESOLVE env var, migrate_to_v4 tech_uncap fix | DB pipeline tooling |
| `5fa9e5e` | mip-dev comparison framework + 4-week ERCOT test results | Internal validation tooling |
| `a27785d` | National myopic config + SLURM scripts | Server-specific |
| `2b49fa1` | SLURM solver tuning experiment script | Server-specific |
| `1d2417c` | .DS_Store gitignore | Trivial |
| `a4dfe0e` | Group cleanup / RPS data fixes | DB pipeline |

If you need any of these on `unstable`, cherry-pick from `db-migration/mip-dev`.

---

## 6. DB Pipeline

### Building v4 databases from the national mip-dev source

The unified pipeline script handles everything:

```bash
python data_files/mip_migration_workspace/build_v4_db.py \
  --source data_files/mip_migration_workspace/data_files/server_current_policies_noIRA_52_week_retire_HighGasCapex.sqlite \
  --regions TRE,TREW \
  --weeks 4 \
  --output-v4 output_v4.sqlite \
  --schema temoa/db_schema/temoa_schema_v4.sql
```

Pipeline: copy → filter regions → clean techs → clean groups → clean commodities →
subset time → auto-set C2A → migrate v3.1→v4 → strip region prefixes → validate.

**Critical formula:** `C2A = N_kept_seasons × 168` (hours/week). For 4 weeks: C2A=672,
days_per_period=28. For 52 weeks: C2A=8736, days_per_period=364.

### Config settings for our databases

These are REQUIRED for mip-dev parity:
```toml
time_sequencing = "seasonal_timeslices"
reserve_margin = "static"
```

And the input database must have:
- Empty `planning_reserve_margin` table (PRM disabled via data, not code)
- Empty `tech_seasonal_storage` table (daily storage only)
- No `cost_emission` data (emission costs not in mip-dev)
- No `lifetime_survival_curve` data (not in mip-dev)

---

## 7. Two Environments — NEVER Cross

| Environment | Branch(es) | Venv | Package structure | How to run |
|-------------|-----------|------|-------------------|------------|
| v4 | `unstable`, `db-migration/mip-dev`, any `pr/*` or `feat/*` | `.venv/` (uv) | `temoa/` package | `source .venv/bin/activate && temoa run config.toml` |
| mip-dev | `mip-dev`, `mip-dev-52` | `.venv312/` (pip) | `temoa_model/` flat | `source .venv312/bin/activate && python temoa_model/temoa_run.py --config ...` |

**Switch branches before switching environments.** Running mip-dev code from a v4 branch
(or vice versa) will produce silent wrong results, not errors.

---

## 8. Running on M5

### First-time setup (v4)
```bash
# Install uv if not present
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and set up
git clone git@github.com:SutubraResearch/temoa.git temoa-SRfork
cd temoa-SRfork
git remote add upstream https://github.com/TemoaProject/temoa.git
git fetch upstream
git checkout unstable
git pull upstream unstable

# Create venv and install
uv sync
source .venv/bin/activate

# Verify
temoa --version
python -m pytest tests/ -v  # Should be 199 passing
```

### Gurobi
Gurobi must be installed and licensed. The solver is used for all real runs. Test suite
defaults should work with any solver but Gurobi is assumed throughout.

### Running a real model
```bash
source .venv/bin/activate
temoa run path/to/config.toml              # Full build + solve
temoa run path/to/config.toml --build-only # Build only (fast, catches index/constraint issues)
```

---

## 9. Large Databases Available on M2

These are in `data_files/` and are NOT in git. Copy them to M5 manually if needed.

| File | Size | What |
|------|------|------|
| `mip_migration_workspace/data_files/server_current_policies_noIRA_52_week_retire_HighGasCapex.sqlite` | 2.6 GB | Base national v3.1 DB (source for pipeline) |
| `mip_migration_workspace/data_files/full_52week_v4_stripped.sqlite` | 2.8 GB | Full national v4, all 16 regions, 52 weeks |
| `mip_migration_workspace/data_files/test_A1_demand_annual.sqlite` | 2.8 GB | Test A1 — annual demand formulation |
| `mip_migration_workspace/data_files/test_A2_demand_no_annual.sqlite` | 2.8 GB | Test A2 — no annual demand |
| `mip_migration_workspace/data_files/test_B_no_storage_init.sqlite` | 2.8 GB | Test B — without storage init |
| `mip_migration_workspace/data_files/test_C_season_ramp.sqlite` | 2.8 GB | Test C — season ramp constraints |
| `mip_migration_workspace/server_results/national_52week_solved_2026-03-04.sqlite` | 5.8 GB | Solved national model (results inside) |
| `ECT/Test_Full.sqlite` | 78 MB | ECT full model |
| `canada/MMCF2 - Transmission Analysis/*.sqlite` | ~1.1 GB each | Canada transmission models |

The 2.8GB+ databases are too large to solve on a 16GB MacBook. Use the server or M5 (if
it has more RAM). You can do `--build-only` on them locally to check construction.

---

## 10. Key Technical Decisions and Gotchas

### DemandActivity constraint must NOT be skipped blindly
Commit `eb0ba63` tried skipping DAC when only one tech serves a demand — this broke the link
between `v_flow_out_annual` and timeslice-level `v_flow_out`, delivering ~1/12 of demand while
reporting "optimal." The merged PR #274 handles this correctly: it skips DAC only for
single-tech demands AND fixes the variables to maintain consistency.

### C2A must match time structure
`C2A × SegFrac ≈ 1.0` per timeslice. If C2A=8760 with 4-week SegFrac (1/672), capacity is
inflated 13×, making thermal dispatch unnecessary. The `build_v4_db.py` script auto-sets this.

### JSON set caches are gone upstream
PR #282 replaced the massive `*_sets.json` files (50-90K lines each) with deterministic hashes.
This is great — the painful surgical-edit workflow for those files is no longer needed.

### data_files/ removed upstream
PR #283 removed the `data_files/` directory from the repo. Tutorial assets moved to
`temoa/tutorial_assets/`. Our local `data_files/` still exists (gitignored or untracked) with
all the mip-dev workspace stuff.

### Pyomo API change
PR #280 updated Pyomo. `sparse_iterkeys` → `sparse_keys`. If you see this error, you're on
old Pyomo. `uv sync` should fix it.

---

## 11. Server Information

The SLURM server (AMD EPYC 7713, 64-core, 600GB RAM) is where national-scale runs happen.
Configs and SLURM scripts are in the internal-only commits on `db-migration/mip-dev`.
Server data path pattern: `/trace/group/adams/cwade2/temoa2026/`.

### mip-dev benchmark (national 52-week myopic, 2 periods)
- P1 barrier solve: 3,698s | P2: 3,985s | Total barrier: 7,683s
- v4 equivalent: P1: 2,456s | Combined: 6,162s (1.25× faster)
- Model size: ~32M rows, ~33M cols, ~118M nonzeros (pre-presolve)

---

## 12. Key Reference Documents (in repo)

| Document | Path | What |
|----------|------|------|
| CLAUDE.md | `CLAUDE.md` | Full project guide (architecture, conventions, commands) |
| Handoff report | `data_files/mip_migration_workspace/server_results/HANDOFF_REPORT.md` | Detailed migration results |
| Regression tests | `docs/REGRESSION_TEST_REPORT.md` | Test result documentation |
| National audit | `data_files/mip_migration_workspace/server_results/national_52week_audit.md` | 52-week 16-region comparison |
| Status summary | `docs/MIP_DEV_TO_V4_STATUS.md` | High-level migration status |
| Constraint audit | `CONSTRAINT_AUDIT.md` | Constraint-by-constraint mip-dev vs v4 |
| mip-dev changes | `MIP_DEV_CHANGES_ANALYSIS.md` | Change-by-change comparison |
| Migration summary | `MIGRATION_SUMMARY.md` | When results match/differ |
| Build efficiency | `BUILD_EFFICIENCY_AUDIT.md` | Build-time performance analysis |

---

## 13. Working Preferences (for Claude on M5)

These were learned over ~3 weeks of intensive collaboration:

- **Never push without explicit permission.** Even if a plan says "push." Ask first, every time.
- **Never make changes beyond what was asked.** One instruction = one action. Stop after completing it.
- **Never mention Claude/AI in commits.** No Co-Authored-By, no "generated by", nothing.
- **Commit style:** Short imperative, one line. e.g., "Skip DemandActivity constraint when only one tech serves demand"
- **Check upstream behavior before inventing fixes.** `git log` and `git diff --stat` on upstream first.
- **Question the premise when things go wrong.** If a fix is creating more problems, the assumption is probably wrong.
- **No flip-flopping.** Make a decision, execute it. Don't propose A, reverse to B, then back to A.
- **Evidence before action.** Confidence is not evidence. Verify claims before acting on them.
- **Plan steps are hard gates.** Don't skip steps. If blocked, stop and say so.
- **Coding style:** Follow upstream conventions (ruff, single quotes, 100 chars, type hints).
- **Solver:** Gurobi, always.
- **The `energysystem` branch is NOT our base.** Fork point is commit `c7cd1f9`.

---

## 14. What's Next

The migration is done. The immediate next phase is **running data center scenarios on
upstream unstable** for ongoing research. This means:

1. Get `unstable` running on M5 with a real database (not just the toy test suite)
2. Build v4 databases for data center scenarios using the pipeline
3. Run national-scale models on the server

No outstanding code work is needed — upstream has everything.
