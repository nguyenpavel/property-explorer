"""Render the plan area of the sales sheet to plan-sheet.png (4 px per pt), for the viewer.

Run:  python make_sheet.py   (needs PyMuPDF)
The crop matches CROP in build_flat.py and viewer.html.
"""
import os, pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
CROP = (520, 114, 1010, 676)
page = pymupdf.open(os.path.join(HERE, 'src', 'd601.pdf'))[0]
pm = page.get_pixmap(matrix=pymupdf.Matrix(4, 4), clip=pymupdf.Rect(*CROP), alpha=False)
pm.save(os.path.join(HERE, 'plan-sheet.png'))
print('SAVED plan-sheet.png', pm.width, pm.height)
