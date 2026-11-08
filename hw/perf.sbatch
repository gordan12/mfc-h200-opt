#!/bin/bash
#SBATCH -A YOUR_PROJECT -p dev -N1 --gres=gpu:1 -c 12 -t 02:00:00
#SBATCH -J mfc-perf -o /work/your_user/mfc-opt/hw/logs/%x-%j.out
#SBATCH --exclude=25a-hgpn[001,039,069]
# baseline: case-optimized viscous_weno5_sgb_acoustic, 1x H200, gbpp=16; then same binary under nsys
C=examples/3D_performance_test/case.py
/work/your_user/mfc-opt/hw/run.sh $C 1 perf-1g
/work/your_user/mfc-opt/hw/run.sh $C 1 perf-1g-nsys --nsys
