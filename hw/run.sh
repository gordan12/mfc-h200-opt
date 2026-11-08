#!/bin/bash
# usage (inside a Slurm alloc): hw/run.sh <case.py> <ngpu> <tag> [extra mfc.sh run args...] [-- case args]
# Runs a case-optimized build in node-local /tmp (outputs are GBs; /work quota is ~15 GB) and keeps only logs.
set -eo pipefail
CASE=$1; NG=$2; TAG=$3; shift 3
ROOT=${MFC_DIR:-/work/your_user/mfc-opt}; cd $ROOT; source /work/your_user/mfc-opt/hw/env.sh
RUN=/tmp/mfc-$SLURM_JOB_ID-$TAG; rm -rf $RUN; mkdir -p $RUN; cp $(dirname $CASE)/*.py $RUN/
OUT=/work/your_user/mfc-opt/hw/results/$TAG; mkdir -p $OUT
git rev-parse --short HEAD > $OUT/commit; git diff --stat >> $OUT/commit
./mfc.sh run $RUN/$(basename $CASE) -t pre_process simulation --case-optimization --gpu acc -j 12 --binary mpirun \
    -n $NG -g $(seq -s " " 0 $((NG-1))) "$@" 2>&1 | tee $OUT/run.log
( cd $RUN && find . -type f \( -path "*/p_all/*" -o -path "*/D/*" -o -path "*/restart_data/*" -o -path "*/silo_hdf5/*" \) | sort | xargs -r md5sum ) > $OUT/out.md5 || true
[ -n "$KEEP" ] && { mkdir -p $OUT/keep; cp $RUN/restart_data/*.dat $OUT/keep/ 2>/dev/null; }  # KEEP=1: save restart files for numeric comparison
cp $RUN/time_data.dat $OUT/ 2>/dev/null || true
cp -r $RUN/*.qdrep $RUN/*.nsys-rep $RUN/*.ncu-rep $OUT/ 2>/dev/null || true
rm -rf $RUN
