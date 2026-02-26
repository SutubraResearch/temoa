# TRE/TREW January 4-Week Comparison

Side-by-side comparison of v4/unstable and mip-dev branches using a small,
solvable Texas (TRE + TREW) model with 4 weekly seasons (January).

## Quick Start

All commands run from the **project root** (`temoa-SRfork/`).

### 1. v4 Build-Only (fast — seconds)

```bash
python data_files/mip_migration_workspace/comparison/run_v4_comparison.py \
  --config data_files/mip_migration_workspace/comparison/config_comparison_v4.toml \
  --build-only
```

Produces `v4_metrics.json` with var/constraint counts, timing, and LP file.

### 2. v4 Full Solve

```bash
python data_files/mip_migration_workspace/comparison/run_v4_comparison.py \
  --config data_files/mip_migration_workspace/comparison/config_comparison_v4.toml
```

Adds objective, capacity, and flow data to `v4_metrics.json`.

### 3. mip-dev Side

**Important:** mip-dev requires Python <=3.11 and an older Pyomo (<6.8). It cannot
run in our Python 3.12 venv due to `imp` module removal and Pyomo parameter loading
changes. You need a separate conda/venv environment.

The v3 DB has been pre-cleaned to TRE/TREW only (orphan techs, commodities, and
non-TRE/TREW data removed from all tables).

**Option A: Server (recommended)**

Run on the server where the mip-dev conda environment is already set up:

```bash
# Copy DB to server
scp data_files/mip_migration_workspace/data_files/jan_TRE_TREW_4week.sqlite \
  server:temoa/data_files/

# SSH in and run
conda activate mip-dev
cd temoa && git checkout mip-dev
python temoa_model/ --config=path/to/config_comparison_mipdev
```

**Option B: Local conda environment**

```bash
# Create a Python 3.11 environment
conda create -n mipdev python=3.11 pyomo=6.7 gurobi -c conda-forge -c gurobi
conda activate mipdev

# Switch branch
git stash && git checkout mip-dev

# Copy DB and run
cp data_files/mip_migration_workspace/data_files/jan_TRE_TREW_4week.sqlite \
   data_files/jan_TRE_TREW_4week.sqlite
echo "" | python temoa_model/ \
  --config=data_files/mip_migration_workspace/comparison/config_comparison_mipdev

# Switch back
git checkout db-migration/mip-dev && git stash pop
conda deactivate
```

**Option C: Standalone runner (Python 3.12, experimental)**

`run_mipdev.py` patches the `imp` module for Python 3.12 compatibility and bypasses
the mip-dev CLI. However, Pyomo 6.8+ changed how it loads `.dat` file parameters, so
the CapacityFactorTech (5-dim indexed) data may not load correctly. Use only if you've
confirmed Pyomo compatibility.

```bash
python data_files/mip_migration_workspace/comparison/run_mipdev.py \
  --config data_files/mip_migration_workspace/comparison/config_comparison_mipdev
```

### 4. Extract mip-dev Metrics

After the mip-dev solve completes (by any method), extract metrics. The DB will have
region-prefixed tech names; the extractor strips them automatically.

```bash
python data_files/mip_migration_workspace/comparison/extract_mipdev_metrics.py \
  data_files/mip_migration_workspace/data_files/jan_TRE_TREW_4week.sqlite \
  --scenario jan_4week_mipdev \
  --output data_files/mip_migration_workspace/comparison/mipdev_metrics.json
```

### 5. Compare

```bash
python data_files/mip_migration_workspace/comparison/compare_results.py \
  data_files/mip_migration_workspace/comparison/v4_metrics.json \
  data_files/mip_migration_workspace/comparison/mipdev_metrics.json
```

## Files

| File | Purpose |
|------|---------|
| `create_4week_subset_v4.py` | Subset a 52-week v4 DB to 4 weeks |
| `validate_4week_db.py` | Validate any 4-week DB (v3 or v4) |
| `run_v4_comparison.py` | Build+solve on v4, capture metrics to JSON |
| `extract_mipdev_metrics.py` | Extract metrics from mip-dev output DB |
| `compare_results.py` | Diff two metric JSONs, produce report |
| `config_comparison_v4.toml` | v4 config for comparison run |
| `config_comparison_mipdev` | mip-dev config (old format) |
| `run_mipdev.py` | Standalone mip-dev runner (Python 3.12 shim, experimental) |

## Databases

In `data_files/mip_migration_workspace/data_files/`:

| File | Schema | Purpose |
|------|--------|---------|
| `jan_TRE_TREW_4week.sqlite` | v3.1 | For mip-dev branch |
| `jan_TRE_TREW_4week_v4_stripped.sqlite` | v4 | For this branch |

Source (52-week) databases are preserved as `test_TRE_TREW_52week*`.

Note: The v3 DB has been cleaned to TRE/TREW only — orphan technologies,
commodities, and data from other regions were removed. The 52-week source
still has national data in some tables.

## What to Compare

1. **Model size**: Variable and constraint counts — should be similar order of magnitude.
   v4 may have slightly more due to additional constraint types.

2. **Build time**: How long to construct the Pyomo model. This is where the 48h vs 6-10h
   gap manifests at full national scale.

3. **Objective**: Total system cost. Should match within ~0.1% if the models are equivalent.

4. **Capacity/Flow**: Per-tech, per-period results. Differences here indicate formulation
   divergence between branches.

5. **LP structure**: Comparing LP files directly (row/column counts, variable names) can
   reveal structural differences in the formulation.

## Thresholds

Default comparison thresholds (adjustable via CLI flags):

- Objective: <0.1% relative difference = PASS
- Capacity: >1 MW absolute or >1% relative = flagged
- Flow: >1 MWh absolute or >1% relative = flagged
