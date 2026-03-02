#!/bin/bash
#SBATCH --job-name=temoa-exp
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=250G
#SBATCH --time=48:00:00
#SBATCH --output=/trace/group/adams/cwade2/temoa2026/experiment_%j_%x.out
#SBATCH --error=/trace/group/adams/cwade2/temoa2026/experiment_%j_%x.err

# Server solver tuning experiments for v4 national model
#
# Usage:
#   sbatch --job-name=exp-A run_server_experiment.sh A    # ND ordering
#   sbatch --job-name=exp-C run_server_experiment.sh C    # ScaleFlag=2
#   sbatch --job-name=exp-D run_server_experiment.sh D    # BarHomogeneous=1
#   sbatch --job-name=exp-AC run_server_experiment.sh AC  # ND + ScaleFlag=2
#   sbatch --job-name=exp-AD run_server_experiment.sh AD  # ND + BarHomogeneous=1

set -euo pipefail

source /trace/packages/anaconda3/2023.03-1/etc/profile.d/conda.sh
conda activate temoa

cd /trace/home/cwade2/code_repos/temoa_github/temoa

EXPERIMENT="${1:-baseline}"

echo "=== Temoa Solver Experiment: $EXPERIMENT ==="
echo "Date: $(date)"
echo "Node: $(hostname)"
echo "Job ID: ${SLURM_JOB_ID:-local}"
echo "Working dir: $(pwd)"
echo "Python: $(which python)"
echo "Temoa: $(which temoa)"

# Reset all experiment env vars
unset TEMOA_BAR_ORDER TEMOA_SCALE_FLAG TEMOA_BAR_HOMOGENEOUS TEMOA_GUROBI_DIRECT 2>/dev/null || true

case "$EXPERIMENT" in
    baseline)
        export TEMOA_BAR_ORDER=0
        echo "Config: BarOrder=0 (AMD, baseline)"
        ;;
    A)
        export TEMOA_BAR_ORDER=-1
        echo "Config: BarOrder=-1 (auto/ND)"
        ;;
    C)
        export TEMOA_BAR_ORDER=0
        export TEMOA_SCALE_FLAG=2
        echo "Config: BarOrder=0 + ScaleFlag=2"
        ;;
    D)
        export TEMOA_BAR_ORDER=0
        export TEMOA_BAR_HOMOGENEOUS=1
        echo "Config: BarOrder=0 + BarHomogeneous=1"
        ;;
    AC)
        export TEMOA_BAR_ORDER=-1
        export TEMOA_SCALE_FLAG=2
        echo "Config: BarOrder=-1 + ScaleFlag=2"
        ;;
    AD)
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

temoa run --silent "$CONFIG"

echo ""
echo "=== Experiment $EXPERIMENT complete ==="
echo "End time: $(date)"
