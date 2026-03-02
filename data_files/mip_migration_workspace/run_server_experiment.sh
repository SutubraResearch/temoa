#!/bin/bash
#SBATCH --job-name=temoa-exp
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --mem=250G
#SBATCH --time=48:00:00
#SBATCH --output=experiment_%j_%x.out
#SBATCH --error=experiment_%j_%x.err

# Server solver tuning experiments for v4 national model
#
# Usage:
#   sbatch --job-name=exp-A run_server_experiment.sh A    # ND ordering
#   sbatch --job-name=exp-C run_server_experiment.sh C    # ScaleFlag=2
#   sbatch --job-name=exp-D run_server_experiment.sh D    # BarHomogeneous=1
#   sbatch --job-name=exp-AC run_server_experiment.sh AC  # ND + ScaleFlag=2
#   sbatch --job-name=exp-AD run_server_experiment.sh AD  # ND + BarHomogeneous=1
#
# Each experiment uses environment variables to configure Gurobi options.
# The underlying code is identical — only solver params change.
#
# Memory: ~70-80 GB peak. 100G allocation leaves headroom.
# Time: 12-48h depending on experiment.
#
# Check results with:
#   sacct -j <JOB_ID> --format=JobID,JobName,MaxRSS,Elapsed,State
#   grep -E 'Ordering|Dense|Factor|Iter|Optimal' experiment_<JOB_ID>*.out

set -euo pipefail

EXPERIMENT="${1:-baseline}"

echo "=== Temoa Solver Experiment: $EXPERIMENT ==="
echo "Date: $(date)"
echo "Node: $(hostname)"
echo "Job ID: ${SLURM_JOB_ID:-local}"

# Activate environment
source .venv/bin/activate

# Reset all experiment env vars
unset TEMOA_BAR_ORDER TEMOA_SCALE_FLAG TEMOA_BAR_HOMOGENEOUS TEMOA_GUROBI_DIRECT

case "$EXPERIMENT" in
    baseline)
        # Current production settings: BarOrder=0 (AMD)
        export TEMOA_BAR_ORDER=0
        echo "Config: BarOrder=0 (AMD, baseline)"
        ;;
    A)
        # Experiment A: Nested Dissection ordering
        export TEMOA_BAR_ORDER=-1
        echo "Config: BarOrder=-1 (auto/ND)"
        ;;
    C)
        # Experiment C: Aggressive scaling with AMD
        export TEMOA_BAR_ORDER=0
        export TEMOA_SCALE_FLAG=2
        echo "Config: BarOrder=0 + ScaleFlag=2"
        ;;
    D)
        # Experiment D: Homogeneous barrier with AMD
        export TEMOA_BAR_ORDER=0
        export TEMOA_BAR_HOMOGENEOUS=1
        echo "Config: BarOrder=0 + BarHomogeneous=1"
        ;;
    AC)
        # Combo: ND + ScaleFlag
        export TEMOA_BAR_ORDER=-1
        export TEMOA_SCALE_FLAG=2
        echo "Config: BarOrder=-1 + ScaleFlag=2"
        ;;
    AD)
        # Combo: ND + BarHomogeneous (most promising combo)
        export TEMOA_BAR_ORDER=-1
        export TEMOA_BAR_HOMOGENEOUS=1
        echo "Config: BarOrder=-1 + BarHomogeneous=1"
        ;;
    *)
        echo "Unknown experiment: $EXPERIMENT"
        echo "Valid: baseline, A, C, D, AC, AD"
        exit 1
        ;;
esac

echo ""
echo "Environment:"
echo "  TEMOA_BAR_ORDER=${TEMOA_BAR_ORDER:-<default>}"
echo "  TEMOA_SCALE_FLAG=${TEMOA_SCALE_FLAG:-<not set>}"
echo "  TEMOA_BAR_HOMOGENEOUS=${TEMOA_BAR_HOMOGENEOUS:-<not set>}"
echo "  TEMOA_GUROBI_DIRECT=${TEMOA_GUROBI_DIRECT:-<not set>}"
echo ""

CONFIG="data_files/my_configs/full_national_myopic.toml"
echo "Config file: $CONFIG"
echo "Starting temoa run..."
echo ""

# Run with auto-confirm
echo y | temoa run "$CONFIG"

echo ""
echo "=== Experiment $EXPERIMENT complete ==="
echo "End time: $(date)"
