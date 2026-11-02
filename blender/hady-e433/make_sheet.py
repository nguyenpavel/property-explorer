"""Cut plan-sheet.png (the plan area of the developer PDF, 6 px per point) for the viewer.

Run:  python -I make_sheet.py src/e433.pdf plan-sheet.png
CROP must match build_e433.py and viewer.html. The corner of the key plan that pokes into
the crop (bottom left) is painted out.
"""
import sys
import pymupdf
from PIL import Image, ImageDraw

CROP = (252, 58, 619, 376)
Z = 6
page = pymupdf.open(sys.argv[1])[0]
pix = page.get_pixmap(matrix=pymupdf.Matrix(Z, Z), clip=pymupdf.Rect(*CROP), alpha=False)
img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
ImageDraw.Draw(img).rectangle([0, (352 - CROP[1]) * Z, (300 - CROP[0]) * Z, img.height], fill='white')
img = img.quantize(colors=64, dither=Image.Dither.NONE)
img.save(sys.argv[2], optimize=True)
print(img.size)
