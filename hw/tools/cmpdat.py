"""Compare two MFC restart files (raw float64, sys_size fields of equal length): cmpdat.py ref.dat new.dat [nvars]"""
import sys
import numpy as np

a = np.fromfile(sys.argv[1], dtype=np.float64)
b = np.fromfile(sys.argv[2], dtype=np.float64)
assert a.size == b.size, (a.size, b.size)
nv = int(sys.argv[3]) if len(sys.argv) > 3 else 1
a = a.reshape(nv, -1)
b = b.reshape(nv, -1)
print("cells per field %d, fields %d, identical values %.6f%%" % (a.shape[1], nv, 100.0 * np.mean(a == b)))
for v in range(nv):
    d = np.abs(a[v] - b[v])
    scale = np.maximum(np.abs(a[v]), 1e-300)
    rel = d / scale
    print("field %2d  max|ref| %.3e  max abs diff %.3e  max rel diff %.3e  (golden tol 1e-12 abs-or-rel: %s)" % (
        v + 1, np.abs(a[v]).max(), d.max(), rel.max(), "PASS" if np.all((d <= 1e-12) | (rel <= 1e-12)) else "FAIL"))
