#!/bin/bash
#SBATCH -A YOUR_PROJECT -p dev -N1 --gres=gpu:1 -c 12 -t 01:00:00
#SBATCH -J mfc-full -o /work/your_user/mfc-opt/hw/logs/%x-%j.out
# usage: sbatch full.sbatch <tag> <kernel regex> [count]  -> ncu --set full on matching kernels (viscous case)
hostname; nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader
/work/your_user/mfc-opt/hw/run.sh benchmarks/viscous_weno5_sgb_acoustic/case.py 1 $1 --ncu --set full -c ${3:-2} -o ncu_$1 -k "regex:$2"
