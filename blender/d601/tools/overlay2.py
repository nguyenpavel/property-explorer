"""Plan ink over a colour render: black linework red, grey (furniture) linework green."""
import sys
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
ren = Image.open(sys.argv[1]).convert('RGB')
plan = Image.open(sys.argv[2]).convert('RGB').resize(ren.size)
px, pr, out = plan.load(), ren.load(), ren.copy()
po = out.load()
for y in range(ren.height):
    for x in range(ren.width):
        r, g, b = px[x, y]
        v = (r + g + b) / 3
        if v < 100: po[x, y] = (230, 20, 20)
        elif 110 < v < 185 and max(r, g, b) - min(r, g, b) < 12: po[x, y] = (0, 160, 40)
out.save(sys.argv[3]); print(sys.argv[3])
