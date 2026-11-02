"""Draw each vector style of the plan on its own PNG (flat region, displayed coords) to identify it."""
import pymupdf, sys, collections, os
from PIL import Image, ImageDraw
d = pymupdf.open(sys.argv[1]); p = d[0]; M = p.rotation_matrix
OUT = sys.argv[2]; os.makedirs(OUT, exist_ok=True)
X0, Y0, X1, Y1, K = 90, 50, 740, 790, 2.0
groups = collections.defaultdict(list)
for g in p.get_drawings():
    key = (g['type'], tuple(round(v, 2) for v in g['color']) if g.get('color') else None,
           tuple(round(v, 2) for v in g['fill']) if g.get('fill') else None, round(g.get('width') or 0, 2))
    groups[key].append(g)
def pt(q):
    q = pymupdf.Point(q) * M
    return ((q.x - X0) * K, (q.y - Y0) * K)
for i, (key, gs) in enumerate(sorted(groups.items(), key=lambda kv: -len(kv[1]))):
    im = Image.new('RGB', (int((X1 - X0) * K), int((Y1 - Y0) * K)), 'white')
    dr = ImageDraw.Draw(im)
    for g in gs:
        for it in g['items']:
            if it[0] == 'l':
                dr.line([pt(it[1]), pt(it[2])], fill='black', width=1)
            elif it[0] == 'c':
                dr.line([pt(it[1]), pt(it[2]), pt(it[3]), pt(it[4])], fill='blue', width=1)
            elif it[0] == 're':
                r = it[1]
                ps = [pt(r.tl), pt(r.tr), pt(r.br), pt(r.bl), pt(r.tl)]
                dr.line(ps, fill='red', width=1)
            elif it[0] == 'qu':
                q = it[1]
                dr.line([pt(q.ul), pt(q.ur), pt(q.lr), pt(q.ll), pt(q.ul)], fill='green', width=1)
    name = f'{i:02d}_{key[0]}_{key[1]}_{key[2]}_{key[3]}_{len(gs)}'.replace(' ', '').replace('(', '').replace(')', '').replace(',', '-')
    im.save(os.path.join(OUT, name + '.png'))
    print(name)
