#!/bin/bash
#SBATCH --job-name=temoa_national_v4
#SBATCH --output=/trace/group/adams/cwade2/temoa2026/temoa_national_%j.out
#SBATCH --error=/trace/group/adams/cwade2/temoa2026/temoa_national_%j.err
#SBATCH --mem=500G
#SBATCH --time=47:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH -p adams

source /trace/packages/anaconda3/2023.03-1/etc/profile.d/conda.sh
conda activate temoa

cd /trace/home/cwade2/code_repos/temoa_github/temoa
temoa run --silent data_files/my_configs/full_national_myopic.toml
