#!/bin/bash
#SBATCH -A YOUR_PROJECT -p dev -N1 --gres=gpu:1 -c 12 -t 02:00:00
#SBATCH -J mfc-bisect -o /work/your_user/mfc-opt/hw/logs/%x-%j.out
#SBATCH --exclude=25a-hgpn[001,039,069]
# usage: sbatch bisect.sbatch <worktree> <commit>... : 3D_performance_test at each commit, final restart files kept
WT=$1; shift; export KEEP=1
for c in "$@"; do
    if [ "$c" != "-" ]; then git -C $WT checkout -q --detach $c || exit 1; fi
    tag=bis-$( [ "$c" = "-" ] && basename $WT || echo $c )
    MFC_DIR=$WT /work/your_user/mfc-opt/hw/run.sh examples/3D_performance_test/case.py 1 $tag
done
