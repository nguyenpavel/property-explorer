"""Print fill polygons of a grey level (displayed pt) intersecting the flat box."""
import pymupdf, sys
sys.stdout.reconfigure(encoding='utf-8')
d = pymupdf.open(sys.argv[1]); p = d[0]; M = p.rotation_matrix
grey = float(sys.argv[2])
BOX = (95, 55, 735, 790)
for g in p.get_drawings():
    if g['type'] not in ('f', 'fs') or not g.get('fill') or abs(g['fill'][0] - grey) > 0.01: continue
    pts = []
    for it in g['items']:
        if it[0] == 'l':
            pts += [pymupdf.Point(it[1]) * M, pymupdf.Point(it[2]) * M]
        elif it[0] == 're':
            r = it[1]; pts += [pymupdf.Point(q) * M for q in (r.tl, r.tr, r.br, r.bl)]
        elif it[0] == 'qu':
            q = it[1]; pts += [pymupdf.Point(v) * M for v in (q.ul, q.ur, q.lr, q.ll)]
        elif it[0] == 'c':
            pts += [pymupdf.Point(it[1]) * M, pymupdf.Point(it[4]) * M]
    xs = [q.x for q in pts]; ys = [q.y for q in pts]
    if max(xs) < BOX[0] or min(xs) > BOX[2] or max(ys) < BOX[1] or min(ys) > BOX[3]: continue
    uniq = []
    for q in pts:
        t = (round(q.x, 2), round(q.y, 2))
        if not uniq or uniq[-1] != t: uniq.append(t)
    print(f'bbox x {min(xs):.2f}..{max(xs):.2f} y {min(ys):.2f}..{max(ys):.2f} n={len(uniq)}', uniq if len(uniq) <= 14 else uniq[:14] + ['...'])
