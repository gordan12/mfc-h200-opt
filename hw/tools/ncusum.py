"""Roofline table from an ncu report: python3 ncusum.py report.ncu-rep  (needs ncu on PATH)."""
import csv, io, subprocess, sys

M = {
    "t": "gpu__time_duration.sum",
    "regs": "launch__registers_per_thread",
    "occ_th": "sm__maximum_warps_per_active_cycle_pct",
    "occ": "sm__warps_active.avg.pct_of_peak_sustained_active",
    "dr": "dram__bytes_read.sum",
    "dw": "dram__bytes_write.sum",
    "dpct": "gpu__dram_throughput.avg.pct_of_peak_sustained_elapsed",
    "lld": "l1tex__t_sectors_pipe_lsu_mem_local_op_ld.sum",  # sectors (x32 B)
    "lst": "l1tex__t_sectors_pipe_lsu_mem_local_op_st.sum",
    # full set only stores per-cycle rates for these; total = rate x smsp elapsed cycles
    "dadd": "smsp__sass_thread_inst_executed_op_dadd_pred_on.sum.per_cycle_elapsed",
    "dmul": "smsp__sass_thread_inst_executed_op_dmul_pred_on.sum.per_cycle_elapsed",
    "dfma": "smsp__sass_thread_inst_executed_op_dfma_pred_on.sum.per_cycle_elapsed",
    "cyc": "smsp__cycles_elapsed.avg",
    "fp64": "sm__pipe_fp64_cycles_active.avg.pct_of_peak_sustained_active",
}
BW, FP = 4.8e12, 34e12  # H200 SXM HBM3e B/s, FP64 non-tensor FLOP/s

out = subprocess.run(["ncu", "--import", sys.argv[1], "--csv", "--page", "raw", "--metrics", ",".join(M.values())],
                     capture_output=True, text=True, check=True).stdout
rows = list(csv.reader(io.StringIO(out)))
hdr, units, data = rows[0], rows[1], rows[2:]
ix = {k: hdr.index(v) for k, v in M.items() if v in hdr}
missing = [v for v in M.values() if v not in hdr]
if missing:
    print("missing metrics (shown as 0):", missing)
name_i = hdr.index("Kernel Name")


def f(r, k):
    if k not in ix:
        return 0.0
    v = r[ix[k]].replace(",", "")
    x = float(v) if v not in ("", "n/a") else 0.0
    u = units[ix[k]]
    scale = {"ns": 1e-9, "us": 1e-6, "usecond": 1e-6, "ms": 1e-3, "msecond": 1e-3, "nsecond": 1e-9,
             "byte": 1, "Kbyte": 1e3, "Mbyte": 1e6, "Gbyte": 1e9}.get(u, 1)
    return x * scale


print("%-58s %7s %4s %5s %5s %8s %5s %8s %6s %5s %6s %6s" % (
    "kernel", "ms", "reg", "occT", "occA", "DRAM_GB", "dram%", "local_GB", "GF/s", "fp64%", "AI", "SoL%"))
for r in data:
    t = f(r, "t")
    by = f(r, "dr") + f(r, "dw")
    fl = (f(r, "dadd") + f(r, "dmul") + 2 * f(r, "dfma")) * f(r, "cyc")
    sol = max(by / BW, fl / FP) / t * 100 if t else 0  # achieved fraction of the roofline bound
    print("%-58s %7.3f %4d %5.1f %5.1f %8.3f %5.1f %8.3f %6.0f %5.1f %6.2f %6.1f" % (
        r[name_i][:58], t * 1e3, f(r, "regs"), f(r, "occ_th"), f(r, "occ"), by / 1e9, f(r, "dpct"),
        (f(r, "lld") + f(r, "lst")) * 32 / 1e9, fl / t / 1e9 if t else 0, f(r, "fp64"), fl / by if by else 0, sol))
