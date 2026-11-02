"""Summarise the plan's vector paths by style, in rotated (as displayed) page points."""
import pymupdf, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
d = pymupdf.open(sys.argv[1]); p = d[0]
M = p.rotation_matrix
dr = p.get_drawings()
c = collections.Counter()
ex = {}
for g in dr:
    key = (g['type'], tuple(round(v, 2) for v in g['color']) if g.get('color') else None,
           tuple(round(v, 2) for v in g['fill']) if g.get('fill') else None, round(g.get('width') or 0, 2))
    c[key] += 1
    r = g['rect'] * M
    ex.setdefault(key, []).append((round(r.x0), round(r.y0), round(r.x1), round(r.y1), len(g['items'])))
for k, n in c.most_common():
    print(n, k, ex[k][:4])
# text spans with positions
for b in p.get_text('dict')['blocks']:
    for l in b.get('lines', []):
        for s in l['spans']:
            t = s['text'].strip()
            if t:
                r = pymupdf.Rect(s['bbox']) * M
                print('T', repr(t), round(r.x0, 1), round(r.y0, 1), round(r.x1, 1), round(r.y1, 1), round(s['size'], 2), l['dir'])
