import sys, json
from PIL import Image, ImageDraw
data = json.load(open(sys.argv[1])); out = sys.argv[2]
S = 6; X0, Y0 = 255, 60
img = Image.new('RGB', (int(345*S), int(312*S)), 'white'); g = ImageDraw.Draw(img)
col = {"(0.0, 0.0, 0.0)|0.99": (0,0,0), "(0.0, 0.0, 0.0)|0.28": (220,0,0), "(0.5, 0.5, 0.5)|0.28": (0,150,0),
       "(0.67, 0.67, 0.67)|0.28": (0,0,230), "(0.8, 0.8, 0.8)|0.28": (215,215,215), "(0.2, 0.25, 0.31)|0.28": (200,0,200)}
P = lambda x, y: ((x-X0)*S, (y-Y0)*S)
for d in data:
    t, w, c, f = d['k']
    if t == 'f': continue
    k = c + '|' + w; cl = col.get(k, (255,140,0)); wd = 3 if w == '0.99' else 1
    for s in d['s']:
        if s[0] in ('l','c'): g.line([P(s[1],s[2]), P(s[3],s[4])], fill=cl, width=wd)
        elif s[0] == 're': g.rectangle([P(s[1],s[2]), P(s[3],s[4])], outline=cl, width=wd)
        elif s[0] == 'qu': pts = [P(s[i],s[i+1]) for i in range(1,9,2)]; g.line(pts+[pts[0]], fill=cl, width=wd)
# grid every 10pt
for x in range(260, 600, 10):
    g.text(P(x, 61), str(x), fill=(120,120,120))
for y in range(70, 372, 10):
    g.text(P(256, y), str(y), fill=(120,120,120))
img.save(out)
