#!/bin/bash
#SBATCH --job-name=tune_C
#SBATCH --output=/trace/group/adams/cwade2/temoa_v4/servers/tune_C_%j.out
#SBATCH --error=/trace/group/adams/cwade2/temoa_v4/servers/tune_C_%j.err
#SBATCH --mem=300G
#SBATCH --time=23:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH -p adams

source /trace/packages/anaconda3/2023.03-1/etc/profile.d/conda.sh
conda activate temoa

cd /trace/home/cwade2/code_repos/temoa_github/temoa

# Experiment C: 64 threads + PDHG first-order solver (Gurobi 13)
export TEMOA_THREADS=16
export TEMOA_METHOD=6

temoa run --silent data_files/my_configs/config_srv_20_tuneC.toml
