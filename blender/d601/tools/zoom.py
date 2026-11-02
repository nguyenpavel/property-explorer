"""Crop the displayed page with a labelled pt grid: zoom.py pdf out.png x0 y0 x1 y1 [step]
Renders the whole page once at 600 dpi (cached as src/page-600.png)."""
import pymupdf, sys, os, math
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
pdf, out, x0, y0, x1, y1 = sys.argv[1], sys.argv[2], *map(float, sys.argv[3:7])
step = float(sys.argv[7]) if len(sys.argv) > 7 else 10
DPI = 600
cache = os.path.join(os.path.dirname(pdf), 'page-600.png')
if not os.path.exists(cache):
    pymupdf.open(pdf)[0].get_pixmap(dpi=DPI).save(cache)
k = DPI / 72
im = Image.open(cache).crop((int(x0 * k), int(y0 * k), int(x1 * k), int(y1 * k))).convert('RGB')
sc = min(1.0, 1400 / max(im.size))
im = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
k *= sc
dr = ImageDraw.Draw(im)
gx = math.ceil(x0 / step) * step
while gx < x1:
    X = (gx - x0) * k
    dr.line([(X, 0), (X, im.height)], fill=(255, 0, 0) if round(gx) % round(step * 5) == 0 else (255, 175, 175), width=1)
    dr.text((X + 2, 2), f'{gx:g}', fill=(200, 0, 0))
    gx += step
gy = math.ceil(y0 / step) * step
while gy < y1:
    Y = (gy - y0) * k
    dr.line([(0, Y), (im.width, Y)], fill=(255, 0, 0) if round(gy) % round(step * 5) == 0 else (255, 175, 175), width=1)
    dr.text((2, Y + 2), f'{gy:g}', fill=(200, 0, 0))
    gy += step
im.save(out); print(out, im.size)
