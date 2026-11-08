#!/bin/bash
#SBATCH -A YOUR_PROJECT -p dev -N1 --gres=gpu:1 -c 12 -t 01:30:00
#SBATCH -J mfc-build -o /work/your_user/mfc-opt/hw/logs/%x-%j.out
#SBATCH --exclude=25a-hgpn[001,039,069]
cd /work/your_user/mfc-opt && source hw/env.sh
nvidia-smi -L; which nvfortran mpif90
./mfc.sh build --gpu acc -j 12 "$@"
