"""List axis-aligned segments of chosen styles (displayed pt) inside the flat's box."""
import pymupdf, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
d = pymupdf.open(sys.argv[1]); p = d[0]; M = p.rotation_matrix
want = sys.argv[2]   # e.g. "s,0.0,0.51"
typ, grey, width = want.split(',')
BOX = (95, 55, 735, 790)
H, V, O = [], [], []
for g in p.get_drawings():
    col = g.get('color') if typ == 's' else g.get('fill')
    if g['type'] != typ or not col or abs(col[0] - float(grey)) > 0.01: continue
    if typ == 's' and abs((g.get('width') or 0) - float(width)) > 0.01: continue
    for it in g['items']:
        if it[0] == 'l':
            a, b = pymupdf.Point(it[1]) * M, pymupdf.Point(it[2]) * M
            segs = [(a, b)]
        elif it[0] == 're':
            r = it[1]; q = [pymupdf.Point(r.tl) * M, pymupdf.Point(r.tr) * M, pymupdf.Point(r.br) * M, pymupdf.Point(r.bl) * M]
            segs = [(q[i], q[(i + 1) % 4]) for i in range(4)]
        elif it[0] == 'qu':
            qq = it[1]; q = [pymupdf.Point(qq.ul) * M, pymupdf.Point(qq.ur) * M, pymupdf.Point(qq.lr) * M, pymupdf.Point(qq.ll) * M]
            segs = [(q[i], q[(i + 1) % 4]) for i in range(4)]
        else:
            continue
        for a, b in segs:
            if not (BOX[0] < min(a.x, b.x) and max(a.x, b.x) < BOX[2] and BOX[1] < min(a.y, b.y) and max(a.y, b.y) < BOX[3]): continue
            if abs(a.y - b.y) < 0.05 and abs(a.x - b.x) > 0.5: H.append((round(a.y, 2), round(min(a.x, b.x), 2), round(max(a.x, b.x), 2)))
            elif abs(a.x - b.x) < 0.05 and abs(a.y - b.y) > 0.5: V.append((round(a.x, 2), round(min(a.y, b.y), 2), round(max(a.y, b.y), 2)))
            elif abs(a.x - b.x) > 0.5 or abs(a.y - b.y) > 0.5: O.append((round(a.x, 2), round(a.y, 2), round(b.x, 2), round(b.y, 2)))
print('H (y: x0-x1)')
for s in sorted(set(H)): print('  H', s)
print('V (x: y0-y1)')
for s in sorted(set(V)): print('  V', s)
print('other', len(O))
for s in O[:60]: print('  O', s)
