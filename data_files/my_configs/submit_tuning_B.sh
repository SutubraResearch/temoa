#!/bin/bash
#SBATCH --job-name=tune_B
#SBATCH --output=/trace/group/adams/cwade2/temoa_v4/servers/tune_B_%j.out
#SBATCH --error=/trace/group/adams/cwade2/temoa_v4/servers/tune_B_%j.err
#SBATCH --mem=300G
#SBATCH --time=23:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --exclusive
#SBATCH -p adams

source /trace/packages/anaconda3/2023.03-1/etc/profile.d/conda.sh
conda activate temoa

cd /trace/home/cwade2/code_repos/temoa_github/temoa

# Experiment B: 64 threads + PreSparsify + aggressive scaling
export TEMOA_THREADS=16
export TEMOA_PRE_SPARSIFY=1
export TEMOA_SCALE_FLAG=2

temoa run --silent data_files/my_configs/config_srv_20_tuneB.toml
