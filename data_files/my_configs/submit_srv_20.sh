#!/bin/bash
#SBATCH --job-name=srv_20
#SBATCH --output=/trace/group/adams/cwade2/temoa_v4/servers/srv_20_%j.out
#SBATCH --error=/trace/group/adams/cwade2/temoa_v4/servers/srv_20_%j.err
#SBATCH --mem=150G
#SBATCH --time=23:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH -p adams

source /trace/packages/anaconda3/2023.03-1/etc/profile.d/conda.sh
conda activate temoa

cd /trace/home/cwade2/code_repos/temoa_github/temoa
temoa run --silent data_files/my_configs/config_srv_20.toml
