"""List vector items inside a bbox, grouped by stroke colour/width: query.py pdf x0 y0 x1 y1 [colours...]"""
import sys, pymupdf
pdf = sys.argv[1]; x0, y0, x1, y1 = map(float, sys.argv[2:6])
want = sys.argv[6:]
p = pymupdf.open(pdf)[0]
def inside(pt): return x0 <= pt.x <= x1 and y0 <= pt.y <= y1
for d in p.get_drawings():
    col = d.get('color') or d.get('fill')
    key = f"{d['type']} {tuple(round(c, 2) for c in col) if col else None} w{round(d.get('width') or 0, 2)}"
    if want and not any(w in key for w in want): continue
    out = []
    for it in d['items']:
        pts = [it[1], it[2]] if it[0] == 'l' else ([it[1].tl, it[1].br] if it[0] == 're' else [it[1], it[-1]])
        if all(inside(q) for q in pts):
            if it[0] == 'l': out.append(f"L ({it[1].x:.2f},{it[1].y:.2f})-({it[2].x:.2f},{it[2].y:.2f})")
            elif it[0] == 'c': out.append(f"C ({it[1].x:.2f},{it[1].y:.2f})->({it[4].x:.2f},{it[4].y:.2f})")
            elif it[0] == 're': out.append(f"R {it[1]}")
    if out:
        print(key, f'[{len(out)}]', ' '.join(out[:40]) + (' ...' if len(out) > 40 else ''))
