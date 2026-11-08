#!/bin/bash
#SBATCH -A YOUR_PROJECT -p dev -N1 --gres=gpu:1 -c 12 -t 02:00:00
#SBATCH -J mfc-exp -o /work/your_user/mfc-opt/hw/logs/%x-%j.out
#SBATCH --exclude=25a-hgpn[001,039,069]
# usage: [NSYS=1] sbatch exp.sbatch <tag> [ncu kernel regex]  -> timing run (x2) + optional ncu of matching kernels
TAG=$1; K=$2
C=benchmarks/viscous_weno5_sgb_acoustic/case.py
R=/work/your_user/mfc-opt/hw/run.sh
# node health: other processes on our GPU or a busy node made whole runs 5x slower (2026-11-08)
hostname; uptime; nvidia-smi --query-gpu=index,utilization.gpu,clocks.sm,power.draw --format=csv; nvidia-smi --query-compute-apps=pid,used_memory --format=csv
$R $C 1 $TAG-1g -- --gbpp 16 --steps 20
$R $C 1 $TAG-1g-b -- --gbpp 16 --steps 20
[ -n "$NSYS" ] && $R $C 1 $TAG-nsys --nsys -- --gbpp 16 --steps 20
[ -n "$K" ] && $R $C 1 $TAG-ncu --ncu --metrics $(python3 /work/your_user/mfc-opt/hw/tools/ncusum.py --print-metrics) -c 6 -o ncu_$TAG -k "regex:$K"
true
