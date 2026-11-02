"""Render the floor-plan part of unit-3407.pdf to plan-sheet.png for the viewer's floor overlay.

Run:  python make_sheet.py   (needs PyMuPDF: pip install pymupdf)

Only the plan is kept, not the title block, key plans or area table. The PDF is
1:60 on an A4 sheet, so 1 pt = 25.4 / 72 * 60 mm = 21.167 mm. The crop is rendered
at 300 px per metre; its edges in PDF points go into viewer.html (SHEET).
"""
import os, pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
M_PER_PT = 25.4 / 72 * 60 / 1000
PX_PER_M = 300
X0, Y0, W, H = 556.0, 33.0, 156.0, 459.0     # PDF points: plan, neighbour stubs and entrance arrow

page = pymupdf.open(os.path.join(HERE, 'unit-3407.pdf'))[0]
zoom = PX_PER_M * M_PER_PT
pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=pymupdf.Rect(X0, Y0, X0 + W, Y0 + H),
                      colorspace=pymupdf.csGRAY, alpha=False)
out = os.path.join(HERE, 'plan-sheet.png')
pix.save(out)
# The pixmap snaps to whole pixels, so report the edges it actually covers
print('SHEET', dict(x0=X0, y0=Y0, x1=round(X0 + pix.width / zoom, 3), y1=round(Y0 + pix.height / zoom, 3), w=pix.width, h=pix.height))
