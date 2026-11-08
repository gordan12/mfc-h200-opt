"""GPU idle-gap breakdown in steady-state TIMESTEP ranges of an nsys sqlite export: python3 gaps.py report.sqlite"""
import sqlite3, sys, statistics as st
c = sqlite3.connect(sys.argv[1])
names = dict(c.execute("select id, value from StringIds"))
k = [(s, e, "K:" + names.get(n, "?")) for s, e, n in c.execute("select start,end,shortName from CUPTI_ACTIVITY_KIND_KERNEL")]
m = [(s, e, "M:%d" % ck) for s, e, ck in c.execute("select start,end,copyKind from CUPTI_ACTIVITY_KIND_MEMCPY")]
ts = c.execute("select n.start,n.end from NVTX_EVENTS n left join StringIds s on n.textId=s.id "
               "where coalesce(n.text,s.value)='TIMESTEP' order by n.start").fetchall()
a, b = ts[2][0], ts[-1][1]
ev = sorted(x for x in k + m if a <= x[0] <= b)
gaps_after = {}
gl = []
last_e, last_t = ev[0][1], ev[0][2]
for s, e, t in ev[1:]:
    g = s - last_e
    if g > 0:
        key = ("after memcpy" if last_t.startswith("M") else "after kernel") + (" -> memcpy" if t.startswith("M") else " -> kernel")
        gaps_after.setdefault(key, []).append(g)
        gl.append(g)
    if e > last_e:
        last_e, last_t = e, t
span = b - a
print("span ms %.1f  idle ms %.1f (%.1f%%)  gaps %d  median us %.1f" % (span / 1e6, sum(gl) / 1e6, 100 * sum(gl) / span, len(gl), st.median(gl) / 1e3))
for key, v in sorted(gaps_after.items(), key=lambda kv: -sum(kv[1])):
    print("%-28s n=%5d total ms %7.1f  median us %6.1f  p90 us %6.1f" % (key, len(v), sum(v) / 1e6, st.median(v) / 1e3,
                                                                         sorted(v)[int(0.9 * len(v))] / 1e3))
# biggest single gaps and what precedes them
big = []
last_e, last_t = ev[0][1], ev[0][2]
for s, e, t in ev[1:]:
    if s - last_e > 0:
        big.append((s - last_e, last_t, t))
    if e > last_e:
        last_e, last_t = e, t
agg = {}
for g, p, n in big:
    agg.setdefault((p[:60], n[:60]), []).append(g)
print("\ntop gap sources (prev -> next):")
for (p, n), v in sorted(agg.items(), key=lambda kv: -sum(kv[1]))[:12]:
    print("%7.1f ms n=%4d  %s -> %s" % (sum(v) / 1e6, len(v), p, n))
