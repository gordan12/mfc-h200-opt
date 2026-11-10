#!/bin/bash
#SBATCH -A YOUR_PROJECT -p dev -N1 --gres=gpu:1 -c 12 -t 00:10:00
#SBATCH -J diag -o /work/your_user/mfc-opt/hw/logs/%x-%j.out
#SBATCH --exclude=25a-hgpn[001,039,069]
hostname; uptime; nproc; grep MHz /proc/cpuinfo | sort | uniq -c | sort -nr | head -3
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null
nvidia-smi --query-gpu=name,clocks.sm,clocks.max.sm,clocks.mem,power.draw,power.limit,enforced.power.limit,temperature.gpu,clocks_throttle_reasons.active,utilization.gpu,mig.mode.current --format=csv
nvidia-smi -q -d PERFORMANCE | sed -n 1,40p
ps -eo user,pcpu,comm --sort=-pcpu | head -8
python3 - <<'P'
import time; t=time.time(); s=0
for i in range(20_000_000): s+=i
print("py loop 20M: %.2fs" % (time.time()-t))
P
