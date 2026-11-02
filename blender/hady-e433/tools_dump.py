import sys, json, collections
sys.stdout.reconfigure(encoding='utf-8')
import pymupdf as fitz
d = fitz.open(sys.argv[1]); p = d[0]
R = fitz.Rect(255, 60, 600, 372)
stats = collections.Counter()
out = []
for dr in p.get_drawings():
    r = dr['rect']
    if not R.contains(r): continue
    key = (dr['type'], round(dr.get('width') or 0, 2), tuple(round(c,2) for c in (dr.get('color') or ())), tuple(round(c,2) for c in (dr.get('fill') or ())))
    stats[key] += 1
    segs = []
    for it in dr['items']:
        if it[0] == 'l': segs.append(['l', round(it[1].x,2), round(it[1].y,2), round(it[2].x,2), round(it[2].y,2)])
        elif it[0] == 're': rr = it[1]; segs.append(['re', round(rr.x0,2), round(rr.y0,2), round(rr.x1,2), round(rr.y1,2)])
        elif it[0] == 'c': segs.append(['c', round(it[1].x,2), round(it[1].y,2), round(it[4].x,2), round(it[4].y,2)])
        elif it[0] == 'qu': q = it[1]; segs.append(['qu'] + [round(v,2) for pt in (q.ul,q.ur,q.lr,q.ll) for v in (pt.x,pt.y)])
    out.append({'k': list(map(str,key)), 'r': [round(r.x0,2),round(r.y0,2),round(r.x1,2),round(r.y1,2)], 's': segs})
for k, n in stats.most_common(): print(n, k)
json.dump(out, open(sys.argv[2], 'w'))
print(len(out))
