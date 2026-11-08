# source me: NVHPC 26.3 (HPC-X OpenMPI, CUDA 13.1) for H200 (sm_90)
module purge >/dev/null 2>&1
module load x86-nvhpc/26.3 cmake/4.0.0
export MFC_CUDA_CC=90
export TMPDIR=${SLURM_JOB_ID:+/tmp/your_user-$SLURM_JOB_ID}; export TMPDIR=${TMPDIR:-/work/your_user/tmp}; mkdir -p $TMPDIR  # node-local in jobs: nvfortran temp .ll files reach GBs
# HPC-X ompi from NVHPC: module leaves OPAL_PREFIX unset (help files point at /proj/nv/...); srun launch fails MPI_Init -> use mpirun
export OPAL_PREFIX=$NVHPC_ROOT/comm_libs/13.1/hpcx/hpcx-2.25.1/ompi
# mpirun binds rank0 to core 0, which may be outside the Slurm cgroup -> hwloc_set_cpubind error
export OMPI_MCA_hwloc_base_binding_policy=none
