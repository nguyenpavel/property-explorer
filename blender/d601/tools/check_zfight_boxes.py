"""List geometry that will z-fight in the viewer: flat boxes, and boxes whose faces share a plane
on the same side (overlapping volumes). Touching faces from opposite sides are fine.

Run:  blender -b e433.blend -P check_zfight.py
"""
import bpy
from itertools import combinations

EPS, AREA = 1e-4, 1e-4
boxes = []
for ob in bpy.data.objects:
    if ob.type != 'MESH' or ob.users_collection[0].name == 'Cameras & Lights':
        continue
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    lo = [min(p[k] for p in pts) for k in range(3)]
    hi = [max(p[k] for p in pts) for k in range(3)]
    if min(hi[k] - lo[k] for k in range(3)) < EPS:
        print('FLAT', ob.name, [round(hi[k] - lo[k], 4) for k in range(3)])
    boxes.append((ob.name, lo, hi, len(ob.data.vertices) == 8))

found = 0
for (na, la, ha, ba), (nb, lb, hb, bb) in combinations(boxes, 2):
    for k in range(3):
        i, j = [a for a in range(3) if a != k]
        ov = max(0, min(ha[i], hb[i]) - max(la[i], lb[i])) * max(0, min(ha[j], hb[j]) - max(la[j], lb[j]))
        if ov < AREA:
            continue
        for side, va, vb in (('min', la[k], lb[k]), ('max', ha[k], hb[k])):
            if abs(va - vb) < EPS and ba and bb:
                print('SAME PLANE', 'xyz'[k], side, round(va, 4), f'{ov:.4f} m2', '|', na, '|', nb)
                found += 1
print('CHECKED', len(boxes), 'objects;', found, 'same-plane overlaps')
