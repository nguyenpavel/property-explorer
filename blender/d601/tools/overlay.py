"""Lay the plan's linework (red) over the top-down render: overlay.py render.png plan.png out.png"""
import sys
from PIL import Image, ImageChops, ImageOps
Image.MAX_IMAGE_PIXELS = None
ren = Image.open(sys.argv[1]).convert('RGB')
plan = Image.open(sys.argv[2]).convert('L').resize(ren.size)
base = ren if '--colour' in sys.argv else ImageOps.grayscale(ren).point(lambda v: 90 + v * 0.6).convert('RGB')
ink = plan.point(lambda v: 255 if v < 110 else 0)                             # dark linework only
red = Image.new('RGB', ren.size, (230, 20, 20))
out = Image.composite(red, base, ink)
out.save(sys.argv[3])
print(sys.argv[3], out.size)
