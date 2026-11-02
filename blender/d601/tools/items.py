"""Group paths of one stroke style into touching clusters; print each cluster's bbox (displayed pt)."""
import pymupdf, sys
sys.stdout.reconfigure(encoding='utf-8')
d = pymupdf.open(sys.argv[1]); p = d[0]; M = p.rotation_matrix
grey, width = float(sys.argv[2]), float(sys.argv[3])
BOX = (98, 85, 705, 765)
boxes = []
for g in p.get_drawings():
    if g['type'] != 's' or not g.get('color') or abs(g['color'][0] - grey) > 0.01 or abs((g.get('width') or 0) - width) > 0.01: continue
    for it in g['items']:
        pts = []
        if it[0] == 'l': pts = [it[1], it[2]]
        elif it[0] == 'c': pts = [it[1], it[2], it[3], it[4]]
        elif it[0] == 're': r = it[1]; pts = [r.tl, r.br]
        elif it[0] == 'qu': q = it[1]; pts = [q.ul, q.ur, q.lr, q.ll]
        pts = [pymupdf.Point(q) * M for q in pts]
        xs = [q.x for q in pts]; ys = [q.y for q in pts]
        b = [min(xs), min(ys), max(xs), max(ys), it[0]]
        if b[2] < BOX[0] or b[0] > BOX[2] or b[3] < BOX[1] or b[1] > BOX[3]: continue
        boxes.append(b)
# union-find on touching boxes
n = len(boxes); par = list(range(n))
def f(i):
    while par[i] != i: par[i] = par[par[i]]; i = par[i]
    return i
e = 0.3
for i in range(n):
    for j in range(i + 1, n):
        a, b = boxes[i], boxes[j]
        if a[0] <= b[2] + e and b[0] <= a[2] + e and a[1] <= b[3] + e and b[1] <= a[3] + e:
            par[f(i)] = f(j)
cl = {}
for i in range(n): cl.setdefault(f(i), []).append(boxes[i])
out = []
for k, bs in cl.items():
    x0 = min(b[0] for b in bs); y0 = min(b[1] for b in bs); x1 = max(b[2] for b in bs); y1 = max(b[3] for b in bs)
    kinds = ''.join(sorted(set(b[4] for b in bs)))
    out.append((round(y0, 1), round(x0, 1), round(x1, 1), round(y1, 1), len(bs), kinds))
MIN = float(sys.argv[4]) if len(sys.argv) > 4 else 0
for y0, x0, x1, y1, m, kinds in sorted(out, key=lambda t: (t[0], t[1])):
    if max(x1 - x0, y1 - y0) < MIN: continue
    print(f'x {x0:7.2f}..{x1:7.2f}  y {y0:7.2f}..{y1:7.2f}  w {x1-x0:6.2f} h {y1-y0:6.2f}  ({(x1-x0)*17.639:5.0f} x {(y1-y0)*17.639:5.0f} mm) n={m} {kinds}')
