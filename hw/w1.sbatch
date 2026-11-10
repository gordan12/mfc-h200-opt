#!/bin/bash
#SBATCH -A YOUR_PROJECT -p dev -N1 --gres=gpu:1 -c 12 -t 03:00:00
#SBATCH -J mfc-w1 -o /work/your_user/mfc-opt/hw/logs/%x-%j.out
hostname; uptime; nvidia-smi --query-gpu=index,utilization.gpu,clocks.sm,power.draw --format=csv
cd /work/your_user/mfc-opt
C=benchmarks/viscous_weno5_sgb_acoustic/case.py; R=hw/run.sh
for v in 96 168 80 255; do
  sed -i "s/^set(MFC_WENO_MAXREG .*/set(MFC_WENO_MAXREG $v)/" CMakeLists.txt
  $R $C 1 w1-$v -- --gbpp 16 --steps 20
  B=$(ls -td build/install/gpu-acc-*/bin/simulation | head -1)
  source hw/env.sh >/dev/null 2>&1; cuobjdump -res-usage $B 2>/dev/null | grep -A1 "m_weno_s_weno_1088_gpu" | grep -o "REG:[0-9]*\|LOCAL:[0-9]*" | paste -sd' ' | sed "s/^/w1-$v /"
done
