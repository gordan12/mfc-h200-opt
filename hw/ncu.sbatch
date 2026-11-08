#!/bin/bash
#SBATCH -A YOUR_PROJECT -p dev -N1 --gres=gpu:1 -c 12 -t 02:00:00
#SBATCH -J mfc-ncu -o /work/your_user/mfc-opt/hw/logs/%x-%j.out
#SBATCH --exclude=25a-hgpn[001,039,069]
# usage: sbatch ncu.sbatch <tag>   (first RHS kernels of viscous_weno5_sgb_acoustic gbpp16, full set)
TAG=${1:-base}
/work/your_user/mfc-opt/hw/run.sh benchmarks/viscous_weno5_sgb_acoustic/case.py 1 $TAG-ncu \
  --ncu --set full --import-source yes -c 70 -o ncu_$TAG \
  -k "regex:hllc|weno|viscous|monotonicity|bubble|tvd_rk|convert_conservative|advection_source|pack_weno|additional_physics"
