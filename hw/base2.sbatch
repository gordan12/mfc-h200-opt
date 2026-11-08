#!/bin/bash
#SBATCH -A YOUR_PROJECT -p dev -N1 --gres=gpu:1 -c 12 -t 02:00:00
#SBATCH -J mfc-base2 -o /work/your_user/mfc-opt/hw/logs/%x-%j.out
#SBATCH --exclude=25a-hgpn[001,039,069]
# unmodified master (worktree) reference: timing + output checksums for both benchmark cases
export MFC_DIR=/work/your_user/mfc-base
R=/work/your_user/mfc-opt/hw/run.sh
$R benchmarks/viscous_weno5_sgb_acoustic/case.py 1 ref-visc -- --gbpp 16 --steps 20
$R examples/3D_performance_test/case.py 1 ref-perf
