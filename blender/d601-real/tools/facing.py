"""Report which way assets face: backrest offsets for chairs/sofa, mean normals of named materials."""
import bpy, os
from mathutils import Vector
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(n):
    with bpy.data.libraries.load(os.path.join(ROOT, 'assets', n + '.blend'), link=False) as (s, d):
        d.objects = s.objects
    return d.objects[0]
def high(ob, frac):
    vs = [v.co for v in ob.data.vertices]; h = max(v.z for v in vs)
    sel = [v for v in vs if v.z > frac * h]
    return Vector((sum(v.x for v in sel) / len(sel), sum(v.y for v in sel) / len(sel)))
def low(ob, frac):
    vs = [v.co for v in ob.data.vertices]; h = max(v.z for v in vs)
    sel = [v for v in vs if v.z < frac * h]
    return Vector((sum(v.x for v in sel) / len(sel), sum(v.y for v in sel) / len(sel)))
def mat_normal(ob, key):
    n = Vector(); a = 0
    for p in ob.data.polygons:
        m = ob.material_slots[p.material_index].material
        if m and key.lower() in m.name.lower():
            n += p.normal * p.area; a += p.area
    return n / a if a else None
for name in ('dining_chair', 'desk_chair', 'sofa'):
    print('BACK', name, 'top-part centre offset', [round(c, 3) for c in high(load(name), 0.8)])
f = load('faucet'); print('FAUCET', 'base centre', [round(c, 3) for c in low(f, 0.15)], 'top centre', [round(c, 3) for c in high(f, 0.85)])
for name, key in (('tv', 'Screen'), ('painting', 'Painting'), ('mirror', 'Mirror1'), ('picture_wide', 'BW'), ('media_unit', 'Wood'), ('desk', 'plastic')):
    ob = load(name)
    print('NORMAL', name, key, [s.material.name for s in ob.material_slots], mat_normal(ob, key))
d = load('desk'); print('DESK top/low centre', [round(c, 3) for c in high(d, 0.9)], [round(c, 3) for c in low(d, 0.5)])
fl = load('floor_lamp'); print('FLOORLAMP shade centre', [round(c, 3) for c in high(fl, 0.8)])
