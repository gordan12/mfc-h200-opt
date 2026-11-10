#!/bin/bash
#SBATCH -A YOUR_PROJECT -p dev -N1 --gres=gpu:1 -c 12 -t 02:00:00
#SBATCH -J mfc-combo -o /work/your_user/mfc-opt/hw/logs/%x-%j.out
#SBATCH --exclude=25a-hgpn[001,039,069]
# usage: sbatch combo.sbatch <tag>  -> both benchmark cases, timing x2 + nsys on the viscous case
TAG=$1; R=/work/your_user/mfc-opt/hw/run.sh
V=benchmarks/viscous_weno5_sgb_acoustic/case.py; P=examples/3D_performance_test/case.py
$R $V 1 $TAG-1g -- --gbpp 16 --steps 20
$R $V 1 $TAG-1g-b -- --gbpp 16 --steps 20
$R $P 1 $TAG-perf
$R $P 1 $TAG-perf-b
$R $V 1 $TAG-nsys --nsys -- --gbpp 16 --steps 20
