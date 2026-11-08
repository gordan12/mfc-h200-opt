import csv, sys, os
d = sys.argv[1] if len(sys.argv) > 1 else "."
rows = list(csv.DictReader(open(os.path.join(d, "kern.csv"))))
tot = sum(float(r["Total Time (ns)"]) for r in rows)
print("kernels", len(rows), "total ms", round(tot / 1e6, 1))
for r in rows[:25]:
    print("%5s %8.1fms x%4s %7.3f %s" % (r["Time (%)"], float(r["Total Time (ns)"]) / 1e6, r["Instances"],
                                         float(r["Avg (ns)"]) / 1e6, r["Name"][:95]))
print()
for r in list(csv.DictReader(open(os.path.join(d, "nvtx.csv"))))[:20]:
    print(r.get("Time (%)"), round(float(r["Total Time (ns)"]) / 1e6, 1), r["Instances"], r["Range"])
print(open(os.path.join(d, "mem.csv")).read()[:800])
