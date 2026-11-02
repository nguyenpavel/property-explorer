"""Plot PDF vector paths (filtered by colour/width) over a labelled point grid, for tracing."""
import sys, pymupdf, cv2, numpy as np
pdf, out, x0, y0, x1, y1, S = sys.argv[1], sys.argv[2], *map(float, sys.argv[3:8])
FADE = float(sys.argv[9]) if len(sys.argv) > 9 else 0.35
grid = float(sys.argv[8]) if len(sys.argv) > 8 else 10
p = pymupdf.open(pdf)[0]
W, H = int((x1 - x0) * S), int((y1 - y0) * S)
img = np.full((H, W, 3), 255, np.uint8)
# faint underlay of the real render
pix = p.get_pixmap(matrix=pymupdf.Matrix(S, S), clip=pymupdf.Rect(x0, y0, x1, y1))
under = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3][:, :, ::-1]
under = under[:H, :W]; img[:under.shape[0], :under.shape[1]] = (255 - (255 - under) * FADE).astype(np.uint8)
def P(x, y): return int(round((x - x0) * S)), int(round((y - y0) * S))
g = grid
gx = np.ceil(x0 / g) * g
while gx < x1:
    cv2.line(img, P(gx, y0), P(gx, y1), (230, 200, 200) if gx % (g * 5) else (200, 140, 140), 1)
    cv2.putText(img, f'{gx:g}', (P(gx, y0)[0] + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (160, 60, 60), 1)
    gx += g
gy = np.ceil(y0 / g) * g
while gy < y1:
    cv2.line(img, P(x0, gy), P(x1, gy), (230, 200, 200) if gy % (g * 5) else (200, 140, 140), 1)
    cv2.putText(img, f'{gy:g}', (2, P(x0, gy)[1] - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (160, 60, 60), 1)
    gy += g
for d in p.get_drawings():
    if d['type'] != 's' or not d.get('color'): continue
    col = tuple(round(c, 2) for c in d['color']); w = d['width'] or 0
    if col == (0, 0, 0) and w >= 0.9: bgr, th = (0, 0, 0), 2
    elif col == (0, 0, 0): bgr, th = (255, 120, 0), 1
    elif col == (1.0, 0.0, 0.0) and w > 2: bgr, th = (0, 0, 255), 1
    else: continue
    for it in d['items']:
        if it[0] == 'l':
            cv2.line(img, P(it[1].x, it[1].y), P(it[2].x, it[2].y), bgr, th)
cv2.imwrite(out, img)
print(out, W, H)
