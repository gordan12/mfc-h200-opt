"""Host CUDA API calls inside the GPU gap between two named kernels: gapapi.py report.sqlite <prev_substr> <next_substr>"""
import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
prev_s, next_s = sys.argv[2], sys.argv[3]
names = dict(c.execute("select id, value from StringIds"))
ks = [(s, e, names[n]) for s, e, n in c.execute("select start,end,shortName from CUPTI_ACTIVITY_KIND_KERNEL order by start")]
api = c.execute("select start,end,nameId,correlationId from CUPTI_ACTIVITY_KIND_RUNTIME order by start").fetchall()
kcorr = dict(c.execute("select correlationId, start from CUPTI_ACTIVITY_KIND_KERNEL"))
shown = 0
for i in range(len(ks) - 1):
    if ks[i][2].endswith(prev_s) and ks[i + 1][2].endswith(next_s):
        g0, g1 = ks[i][1], ks[i + 1][0]
        print("gap %.1f us between %s and %s" % ((g1 - g0) / 1e3, ks[i][2], ks[i + 1][2]))
        # API calls that overlap the window [g0 - 50us, g1]
        tot = {}
        for s, e, nid, corr in api:
            if e >= g0 - 50000 and s <= g1:
                nm = names.get(nid, "?")
                tot.setdefault(nm, [0, 0])
                tot[nm][0] += 1
                tot[nm][1] += min(e, g1) - max(s, g0 - 50000)
        for nm, (cnt, t) in sorted(tot.items(), key=lambda kv: -kv[1][1])[:10]:
            print("   %-45s n=%4d  %.1f us" % (nm[:45], cnt, t / 1e3))
        shown += 1
        if shown == 3:
            break
