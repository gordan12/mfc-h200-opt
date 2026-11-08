#!/bin/bash
#SBATCH -A YOUR_PROJECT -p dev -N1 --gres=gpu:2 -c 24 -t 02:00:00
#SBATCH -J mfc-test -o /work/your_user/mfc-opt/hw/logs/%x-%j.out
#SBATCH --exclude=25a-hgpn[001,039,069]
# usage: sbatch test.sbatch [mfc.sh test args...]   (golden-file regression on GPU, generic build)
cd ${MFC_DIR:-/work/your_user/mfc-opt} && source /work/your_user/mfc-opt/hw/env.sh
export PATH=/work/your_user/mfc-opt/hw/bin:$PATH  # srun -> mpirun shim
export SETUPTOOLS_SCM_PRETEND_VERSION=5.7.0  # snapshot dirs have no .git
cat SNAPSHOT.base 2>/dev/null; git rev-parse --short HEAD 2>/dev/null; md5sum SNAPSHOT.diff 2>/dev/null
./mfc.sh test --gpu acc -j 24 -g 0 1 --no-examples "$@"
