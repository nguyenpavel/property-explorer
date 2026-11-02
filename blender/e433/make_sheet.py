"""Render the drawing area of E433.pdf to plan-sheet.png for the viewer's floor overlay.

Run:  python make_sheet.py   (needs PyMuPDF: pip install pymupdf)

The sheet is a 1:50 plan printed to US Letter through "Microsoft Print to PDF", so it
was shrunk to fit: its own dimensions put 1 pt at 21.65 mm (3 300 mm living room =
152.52 pt, 7 160 mm = 330.72 pt, 3 765 mm bedroom = 173.88 pt). The page margins are
left out; the crop is rendered at 240 px per metre (under 4 096 px wide, so phones
can still use it as one texture) and its edges in PDF points go into viewer.html (SHEET).
"""
import os, pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
M_PER_PT = 0.02165
PX_PER_M = 240
X0, Y0, X1, Y1 = 36.0, 102.0, 792.0, 508.0     # PDF points: the plotted area, grid bubbles included

page = pymupdf.open(os.path.join(HERE, 'E433.pdf'))[0]
zoom = PX_PER_M * M_PER_PT
pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=pymupdf.Rect(X0, Y0, X1, Y1), alpha=False)
out = os.path.join(HERE, 'plan-sheet.png')
pix.save(out)
# The pixmap snaps to whole pixels, so report the edges it actually covers
print('SHEET', dict(x0=X0, y0=Y0, x1=round(X0 + pix.width / zoom, 3), y1=round(Y0 + pix.height / zoom, 3), w=pix.width, h=pix.height))
