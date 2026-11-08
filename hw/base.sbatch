#!/bin/bash
#SBATCH -A YOUR_PROJECT -p dev -N1 --gres=gpu:1 -c 12 -t 02:00:00
#SBATCH -J mfc-base -o /work/your_user/mfc-opt/hw/logs/%x-%j.out
#SBATCH --exclude=25a-hgpn[001,039,069]
# baseline: case-optimized viscous_weno5_sgb_acoustic, 1x H200, gbpp=16; then same binary under nsys
C=benchmarks/viscous_weno5_sgb_acoustic/case.py
/work/your_user/mfc-opt/hw/run.sh $C 1 base-1g -- --gbpp 16 --steps 20
/work/your_user/mfc-opt/hw/run.sh $C 1 base-1g-nsys --nsys -- --gbpp 16 --steps 20
