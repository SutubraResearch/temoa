#!/bin/bash
#SBATCH --job-name=tune_A
#SBATCH --output=/trace/group/adams/cwade2/temoa_v4/servers/tune_A_%j.out
#SBATCH --error=/trace/group/adams/cwade2/temoa_v4/servers/tune_A_%j.err
#SBATCH --mem=300G
#SBATCH --time=23:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --exclusive
#SBATCH -p adams

source /trace/packages/anaconda3/2023.03-1/etc/profile.d/conda.sh
conda activate temoa

cd /trace/home/cwade2/code_repos/temoa_github/temoa

# Experiment A: baseline params + 64 threads
export TEMOA_THREADS=16

temoa run --silent data_files/my_configs/config_srv_20_tuneA.toml
