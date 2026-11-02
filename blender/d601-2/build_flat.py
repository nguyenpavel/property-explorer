"""Flat D.601 (Mocca Rezidence, building D, 6.NP, 3+kk) rebuilt from the developer's sales plan.

Run:  blender -b --factory-startup -P build_flat.py -- [--render]

Positions are PDF points of the sheet "D.601 (2).pdf" (A3, the plan clipped to 533..972 x
163..670 pt). The walls are drawn twice, masonry and plaster 0.63 pt (15 mm) apart; rooms
are measured to the plaster faces. One scale fits the whole area table: S = 41.797 pt/m
(1743.6..1750.1 pt2 per m2 keeps all eight rooms on their rounded value), and the sheet's
10 080 and 11 390 dimensions measure 41.799 and 41.796 pt/m between masonry faces.
WALLS is the plan's visible black (outline stroke removed, shaft voids filled), its edges
snapped to the vector coordinates. Heights are not on the plan and are assumptions
(constants below). Doors carry their hinge and closing angle as custom properties, so the
web viewer can swing them; the hinges are the centres of the plan's swing arcs.
"""
import bpy, bmesh, math, os, sys
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []

S = 41.797               # pt per metre
CX, CY = 752.8, 416.2    # plan point at the world origin (middle of the flat)
FLOOR = -0.02            # top of the structural slab; finishes fill FLOOR..0
CEIL = 2.70              # flat: ceiling height
DOOR_H = 2.10            # interior doors
FRONT_H = 2.20           # front door
SILL, HEAD = 0.85, 2.30  # windows
WT = 0.90                # kitchen worktop
RAIL = 1.10              # loggia railing
JAMB = 2.09              # door frame (pt): opening minus the arc radius, halved
PROUD = 0.84             # interior door frames stand 20 mm proud of the wall: the arcs' centres


def X(px): return (px - CX) / S
def Y(py): return (CY - py) / S
def M(m): return m * S   # metres -> pt, for sizes


# ---------------------------------------------------------------- scene
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'


def collection(name, hide_render=False):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    c.hide_render = hide_render
    return c


SITE, ST, FL, OP, KF, FU = (collection(n) for n in ('Site', 'Structure', 'Floors', 'Doors & Windows', 'Fitout', 'Furniture'))
CEILING = collection('Ceiling', hide_render=True)
RIG = collection('Cameras & Lights')


# ---------------------------------------------------------------- materials
def material(name, color, rough=0.5, metal=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    if alpha < 1:
        p.inputs['Alpha'].default_value = alpha
        m.surface_render_method = 'BLENDED'
    m.diffuse_color = (*color, alpha)
    return m


def tiled(name, c1, c2, mortar, width, height, offset=0.5, rough=0.4, turn=False):
    """Brick texture in world space, so neighbouring floor pieces line up."""
    m = material(name, c1, rough)
    nt = m.node_tree
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    mapping = nt.nodes.new('ShaderNodeMapping')
    mapping.inputs['Rotation'].default_value[2] = math.pi / 2 if turn else 0.0
    brick = nt.nodes.new('ShaderNodeTexBrick')
    brick.offset = offset
    brick.inputs['Color1'].default_value = (*c1, 1)
    brick.inputs['Color2'].default_value = (*c2, 1)
    brick.inputs['Mortar'].default_value = (*mortar, 1)
    brick.inputs['Scale'].default_value = 1.0
    brick.inputs['Mortar Size'].default_value = 0.0025
    brick.inputs['Brick Width'].default_value = width
    brick.inputs['Row Height'].default_value = height
    nt.links.new(geo.outputs['Position'], mapping.inputs['Vector'])
    nt.links.new(mapping.outputs['Vector'], brick.inputs['Vector'])
    nt.links.new(brick.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color'])
    return m


WALL = material('Plaster', (0.80, 0.80, 0.78), 0.9)
CONCRETE = material('Concrete', (0.30, 0.30, 0.30), 0.9)
CEIL_MAT = material('Ceiling', (0.85, 0.85, 0.83), 0.9)
OAK_FLOOR = tiled('Oak planks', (0.45, 0.30, 0.17), (0.50, 0.34, 0.20), (0.25, 0.16, 0.09), 1.2, 0.19, turn=True)
LOGGIA_TILE = tiled('Hall tiles', (0.55, 0.54, 0.52), (0.52, 0.51, 0.49), (0.35, 0.34, 0.33), 0.6, 0.6, offset=0.0, rough=0.5)
BATH_TILE = tiled('Bath floor tiles', (0.45, 0.45, 0.46), (0.42, 0.42, 0.43), (0.30, 0.30, 0.31), 0.6, 0.6, offset=0.0, rough=0.3)
WHITE = material('White lacquer', (0.88, 0.88, 0.88), 0.35)
CERAMIC = material('Ceramic', (0.95, 0.95, 0.95), 0.1)
OAK = material('Oak', (0.42, 0.28, 0.16), 0.5)
DARK = material('Anthracite', (0.06, 0.06, 0.07), 0.4)
BLACK_GLASS = material('Black glass', (0.01, 0.01, 0.01), 0.05)
STEEL = material('Steel', (0.75, 0.75, 0.77), 0.25, metal=1.0)
CHROME = material('Chrome', (0.90, 0.90, 0.90), 0.05, metal=1.0)
GLASS = material('Glass', (0.75, 0.85, 0.90), 0.0, alpha=0.18)
FABRIC = material('Sofa fabric', (0.16, 0.20, 0.25), 0.9)
BEDDING = material('Bedding', (0.85, 0.85, 0.83), 0.9)
CUSHION = material('Cushion', (0.55, 0.45, 0.32), 0.9)
WARDROBE = material('Wardrobe', (0.78, 0.75, 0.70), 0.5)


# ---------------------------------------------------------------- geometry helpers
def link(name, me, loc, coll, mat):
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    coll.objects.link(ob)
    return ob


def box(name, coll, mat, x0, y0, x1, y1, z0, z1, bevel=0.0):
    """Axis-aligned box: plan rectangle x0..x1, y0..y1 in pt, heights z0..z1 in metres."""
    ax, bx = sorted((X(x0), X(x1)))
    ay, by = sorted((Y(y0), Y(y1)))
    hx, hy, hz = (bx - ax) / 2, (by - ay) / 2, (z1 - z0) / 2
    me = bpy.data.meshes.new(name)
    me.from_pydata(
        [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
         (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)], [],
        [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
    ob = link(name, me, ((ax + bx) / 2, (ay + by) / 2, (z0 + z1) / 2), coll, mat)
    if bevel:
        mod = ob.modifiers.new('Bevel', 'BEVEL')
        mod.width, mod.segments = bevel, 2
    return ob


def cylinder(name, coll, mat, cx, cy, rx, ry, z0, z1, seg=40):
    """Vertical elliptic cylinder; centre and radii in plan pt."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=1.0, radius2=1.0, depth=1.0,
                          matrix=Matrix.Diagonal((rx / S, ry / S, z1 - z0, 1)))
    for f in bm.faces:
        f.smooth = len(f.verts) == 4
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return link(name, me, (X(cx), Y(cy), (z0 + z1) / 2), coll, mat)


def prism(name, coll, mat, pts, z0, z1):
    """Plan polygon (pt) extruded from z0 to z1, origin at its centroid."""
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    bm = bmesh.new()
    lo = [bm.verts.new((X(px) - X(cx), Y(py) - Y(cy), -(z1 - z0) / 2)) for px, py in pts]
    hi = [bm.verts.new((X(px) - X(cx), Y(py) - Y(cy), (z1 - z0) / 2)) for px, py in pts]
    bm.faces.new(lo)
    bm.faces.new(hi)
    n = len(pts)
    for i in range(n):
        bm.faces.new((lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return link(name, me, (X(cx), Y(cy), (z0 + z1) / 2), coll, mat)


def wall(coll, x0, y0, x1, y1, z0, z1, name='Wall'):
    return box(name, coll, WALL, x0, y0, x1, y1, z0, z1)


def door(did, label, rect, hinge_end, swing, top=DOOR_H, leaf_mat=WHITE, frame_mat=WHITE, floor_mat=None, proud=0.0):
    """Door in an opening rect (pt, spanning the wall thickness), drawn open as on the plan.

    hinge_end: 'start' or 'end' of the opening along its length; swing: +1/-1, the side
    the leaf opens to (perpendicular to the wall, in plan pt). The leaf stores its hinge and
    the rotation that closes it, in three.js terms (y up, plan y = +z). proud moves the hinge
    off the wall face into the swing side (pt).
    """
    x0, y0, x1, y1 = rect
    jamb = JAMB
    along_x = (x1 - x0) > (y1 - y0)
    a0, a1 = (x0, x1) if along_x else (y0, y1)
    f0, f1 = (y0, y1) if along_x else (x0, x1)
    hinge_a = a0 + jamb if hinge_end == 'start' else a1 - jamb
    hinge_f = (f1 if swing > 0 else f0) + swing * proud
    length = (a1 - a0) - 2 * jamb
    to_close = 1 if hinge_end == 'start' else -1
    # frame: two jambs and a head across the wall thickness (proud on the swing side), on the floor finish
    g0, g1 = f0 - (proud if swing < 0 else 0), f1 + (proud if swing > 0 else 0)
    for i, (j0, j1) in enumerate(((a0, a0 + jamb), (a1 - jamb, a1))):
        r = (j0, g0, j1, g1) if along_x else (g0, j0, g1, j1)
        box(f'{label} jamb {i + 1}', OP, frame_mat, *r, 0, top)
    head = (a0 + jamb, g0, a1 - jamb, g1) if along_x else (g0, a0 + jamb, g1, a1 - jamb)
    box(f'{label} head', OP, frame_mat, *head, top - 0.06, top)
    if floor_mat:
        sill = (a0 + jamb, f0, a1 - jamb, f1) if along_x else (f0, a0 + jamb, f1, a1 - jamb)
        box(f'{label} threshold floor', FL, floor_mat, *sill, FLOOR, 0)
    # open leaf: perpendicular to the wall at the hinge, on the swing side
    t = M(0.04)
    side = (0, t) if to_close > 0 else (-t, 0)
    ext = (hinge_f, hinge_f + swing * length)
    if along_x:
        lr = (hinge_a + side[0], min(ext), hinge_a + side[1], max(ext))
        open_dir, close_dir = (0, swing), (to_close, 0)
    else:
        lr = (min(ext), hinge_a + side[0], max(ext), hinge_a + side[1])
        open_dir, close_dir = (swing, 0), (0, to_close)
    leaf = box(f'Door {did}', OP, leaf_mat, *lr, 0.005, top - 0.065, 0.003)
    # handle near the free end, through the leaf
    ea = hinge_a + (side[0] + side[1]) / 2
    ef = hinge_f + swing * (length - M(0.10))
    ha, hf = M(0.06), M(0.045)
    hr = (ea - ha, ef - hf, ea + ha, ef + hf) if along_x else (ef - hf, ea - ha, ef + hf, ea + ha)
    handle = box(f'Door {did} handle', OP, CHROME, *hr, 1.0, 1.03)
    ox, oz = open_dir
    cx, cz = close_dir
    leaf['door_id'] = did
    leaf['door_label'] = label
    leaf['hinge_x'] = X(hinge_a if along_x else hinge_f)
    leaf['hinge_z'] = -Y(hinge_f if along_x else hinge_a)
    leaf['close_angle'] = -math.atan2(ox * cz - oz * cx, ox * cx + oz * cz)
    leaf['level'] = 0
    handle['door_part'] = did
    return leaf


def window(name, rect, z0, z1, mullions=(), bottom=True):
    """Frame and glass; rect is the opening along its length and the frame depth across."""
    x0, y0, x1, y1 = rect
    f, g = M(0.05), M(0.006)
    if (x1 - x0) > (y1 - y0):
        box(f'{name} frame left', OP, DARK, x0, y0, x0 + f, y1, z0, z1)
        box(f'{name} frame right', OP, DARK, x1 - f, y0, x1, y1, z0, z1)
        box(f'{name} frame top', OP, DARK, x0 + f, y0, x1 - f, y1, z1 - 0.07, z1)
        if bottom:
            box(f'{name} frame bottom', OP, DARK, x0 + f, y0, x1 - f, y1, z0, z0 + 0.07)
        for i, m in enumerate(mullions):
            box(f'{name} mullion {i + 1}', OP, DARK, m - f / 2, y0, m + f / 2, y1, z0 + 0.07, z1 - 0.07)
        gm, cuts = (y0 + y1) / 2, [x0 + f, *(c for m in mullions for c in (m - f / 2, m + f / 2)), x1 - f]
        for k in range(0, len(cuts), 2):
            box(f'{name} glass', OP, GLASS, cuts[k], gm - g, cuts[k + 1], gm + g, z0 + (0.07 if bottom else 0), z1 - 0.07)
    else:
        box(f'{name} frame left', OP, DARK, x0, y0, x1, y0 + f, z0, z1)
        box(f'{name} frame right', OP, DARK, x0, y1 - f, x1, y1, z0, z1)
        box(f'{name} frame top', OP, DARK, x0, y0 + f, x1, y1 - f, z1 - 0.07, z1)
        if bottom:
            box(f'{name} frame bottom', OP, DARK, x0, y0 + f, x1, y1 - f, z0, z0 + 0.07)
        for i, m in enumerate(mullions):
            box(f'{name} mullion {i + 1}', OP, DARK, x0, m - f / 2, x1, m + f / 2, z0 + 0.07, z1 - 0.07)
        gm, cuts = (x0 + x1) / 2, [y0 + f, *(c for m in mullions for c in (m - f / 2, m + f / 2)), y1 - f]
        for k in range(0, len(cuts), 2):
            box(f'{name} glass', OP, GLASS, gm - g, cuts[k], gm + g, cuts[k + 1], z0 + (0.07 if bottom else 0), z1 - 0.07)


def wall_window(name, opening, frame, mullions=()):
    """Window in a wall opening: sill wall, lintel, and the frame set in the wall's depth."""
    wall(ST, *opening, FLOOR, SILL, f'{name} sill wall')
    wall(ST, *opening, HEAD, CEIL, f'{name} lintel')
    window(name, frame, SILL, HEAD, mullions)


def chair(name, coll, cx, cy, back, z=0.0, mat=DARK):
    """Chair centred at (cx, cy) pt; back = side of the backrest: 'N', 'S', 'E' or 'W'."""
    h, leg, bk = M(0.21), M(0.02), M(0.035)
    box(f'{name} seat', coll, mat, cx - h, cy - h, cx + h, cy + h, z + 0.43, z + 0.47, 0.004)
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        lx, ly = cx + sx * (h - leg), cy + sy * (h - leg)
        box(f'{name} leg {i + 1}', coll, mat, lx - leg / 2, ly - leg / 2, lx + leg / 2, ly + leg / 2, z, z + 0.43)
    r = {'N': (cx - h, cy - h, cx + h, cy - h + bk), 'S': (cx - h, cy + h - bk, cx + h, cy + h),
         'W': (cx - h, cy - h, cx - h + bk, cy + h), 'E': (cx + h - bk, cy - h, cx + h, cy + h)}[back]
    box(f'{name} back', coll, mat, *r, z + 0.47, z + 0.86, 0.004)


def bed(name, coll, x0, y0, x1, y1, head, z=0.0):
    """Bed filling the rectangle, headboard included; head = 'N', 'S', 'E' or 'W'."""
    i, p, hb, q = M(0.02), M(0.25), M(0.05), M(0.06)
    hr = {'N': (x0, y0, x1, y0 + hb), 'S': (x0, y1 - hb, x1, y1), 'W': (x0, y0, x0 + hb, y1), 'E': (x1 - hb, y0, x1, y1)}[head]
    box(f'{name} headboard', coll, OAK, *hr, z, z + 0.95)
    x0, y0, x1, y1 = {'N': (x0, y0 + hb, x1, y1), 'S': (x0, y0, x1, y1 - hb), 'W': (x0 + hb, y0, x1, y1), 'E': (x0, y0, x1 - hb, y1)}[head]
    box(f'{name} frame', coll, OAK, x0, y0, x1, y1, z, z + 0.30, 0.01)
    box(f'{name} mattress', coll, BEDDING, x0 + i, y0 + i, x1 - i, y1 - i, z + 0.30, z + 0.50, 0.03)
    pr = {'N': (x0 + q, y0 + q, x1 - q, y0 + q + p), 'S': (x0 + q, y1 - q - p, x1 - q, y1 - q),
          'W': (x0 + q, y0 + q, x0 + q + p, y1 - q), 'E': (x1 - q - p, y0 + q, x1 - q, y1 - q)}[head]
    box(f'{name} pillow', coll, BEDDING, *pr, z + 0.50, z + 0.60, 0.03)


def desk(name, coll, x0, y0, x1, y1, z=0.0):
    s = M(0.03)
    box(f'{name} top', coll, OAK, x0, y0, x1, y1, z + 0.72, z + 0.75, 0.003)
    if (x1 - x0) > (y1 - y0):
        box(f'{name} side 1', coll, WHITE, x0, y0, x0 + s, y1, z, z + 0.72)
        box(f'{name} side 2', coll, WHITE, x1 - s, y0, x1, y1, z, z + 0.72)
    else:
        box(f'{name} side 1', coll, WHITE, x0, y0, x1, y0 + s, z, z + 0.72)
        box(f'{name} side 2', coll, WHITE, x0, y1 - s, x1, y1, z, z + 0.72)


def table(name, coll, x0, y0, x1, y1, top, leg=0.04, inset=0.04):
    box(f'{name} top', coll, OAK, x0, y0, x1, y1, top - 0.03, top, 0.003)
    a, b = M(inset), M(inset + leg)
    for i, (lx, ly) in enumerate(((x0 + a, y0 + a), (x1 - b, y0 + a), (x0 + a, y1 - b), (x1 - b, y1 - b))):
        box(f'{name} leg {i + 1}', coll, DARK, lx, ly, lx + M(leg), ly + M(leg), 0, top - 0.03)


def wc(name, coll, cx, cy, facing, z=0.0):
    """Wall-hung WC, bowl centred at (cx, cy) pt, facing 'N', 'S', 'E' or 'W' (away from the wall)."""
    vertical = facing in 'NS'
    rl, rw = M(0.24), M(0.18)
    rx, ry = (rw, rl) if vertical else (rl, rw)
    cylinder(f'{name} bowl', coll, CERAMIC, cx, cy, rx, ry, z + 0.30, z + 0.40)
    cylinder(f'{name} seat', coll, CERAMIC, cx, cy, rx + M(0.01), ry + M(0.01), z + 0.40, z + 0.43)
    d = {'N': (0, 1), 'S': (0, -1), 'E': (-1, 0), 'W': (1, 0)}[facing]   # towards the wall
    mx, my = cx + d[0] * M(0.25), cy + d[1] * M(0.25)
    h = M(0.12)
    box(f'{name} mount', coll, CERAMIC, mx - h, my - h, mx + h, my + h, z + 0.28, z + 0.42, 0.01)


def basin(name, coll, x0, y0, x1, y1, z=0.0):
    box(f'{name}', coll, CERAMIC, x0, y0, x1, y1, z + 0.70, z + 0.85, 0.015)
    cylinder(f'{name} bowl', coll, STEEL, (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) * 0.32, (y1 - y0) * 0.30, z + 0.849, z + 0.851)


def wardrobe(name, coll, x0, y0, x1, y1, z=0.0, height=2.40):
    box(f'{name}', coll, WARDROBE, x0, y0, x1, y1, z, z + height, 0.004)


# ================================================================ STRUCTURE
# The plan's visible black, plaster faces (walls2.py output; the two window reveals folded
# into their openings). The two installation shafts are solid.
WALLS = [
    (593.10, 163.76, 638.27, 174.22), (680.06, 163.76, 972.28, 174.22),            # entrance side, top
    (593.10, 174.22, 609.01, 296.67), (684.66, 174.22, 826.77, 177.76),
    (963.45, 174.22, 972.28, 363.56),                                              # room 04, east
    (684.66, 177.76, 741.92, 207.43),                                              # shaft above the WC
    (817.16, 177.76, 826.77, 293.74),                                              # bathroom / room 04
    (684.66, 207.43, 691.13, 293.74), (728.76, 207.43, 741.92, 293.74),            # WC sides
    (533.56, 279.60, 593.10, 296.67),                                              # storeroom, north
    (691.13, 287.27, 693.23, 293.74), (726.67, 287.27, 728.76, 293.74),            # WC / bathroom fronts
    (741.92, 287.27, 754.46, 293.74), (787.90, 287.27, 817.16, 293.74),
    (609.01, 290.62, 636.17, 296.67), (820.72, 293.74, 826.77, 300.02),
    (533.56, 296.67, 546.52, 354.35), (630.11, 296.67, 636.17, 301.90),
    (546.52, 325.93, 569.51, 354.35),                                              # shaft by the storeroom
    (630.11, 335.34, 636.17, 354.35), (820.72, 337.63, 826.77, 354.35),
    (569.51, 339.72, 630.11, 354.35),                                              # storeroom / living
    (636.17, 343.91, 651.01, 354.35), (688.64, 343.91, 820.72, 354.35),            # hall / living
    (826.77, 343.91, 885.08, 354.35), (951.96, 343.91, 963.45, 363.56),            # room 04, south
    (533.56, 354.35, 543.38, 657.90),                                              # west facade
    (845.58, 354.35, 885.08, 363.56), (845.58, 363.56, 865.23, 381.31),            # living, east
    (856.65, 464.91, 865.23, 528.03), (845.58, 464.91, 856.65, 509.84),
    (543.38, 509.84, 572.64, 515.90), (610.26, 509.84, 757.18, 515.90),            # living / room 03
    (846.21, 509.84, 856.65, 528.03), (839.30, 513.40, 846.21, 528.03),            # loggia column
    (760.74, 645.27, 775.37, 668.67), (823.42, 645.27, 865.23, 668.67),            # loggia piers
    (543.38, 649.02, 757.18, 657.90), (757.18, 649.02, 760.74, 668.67),            # room 03, south
    (712.00, 657.90, 757.18, 668.67),
]
for r in WALLS:
    wall(ST, *r, FLOOR, CEIL)

# Doors: openings with their lintels, hinged as the plan's arcs
DOORS = [  # id, label, opening, hinge end, swing, top, leaf, frame, threshold floor
    ('entrance', 'Front door', (638.27, 163.76, 680.06, 174.22), 'start', 1, FRONT_H, DARK, DARK, OAK_FLOOR),
    ('d07', 'Storeroom door', (630.11, 301.90, 636.17, 335.34), 'end', -1, DOOR_H, WHITE, WHITE, BATH_TILE),
    ('d06', 'WC door', (693.23, 287.27, 726.67, 293.74), 'start', -1, DOOR_H, WHITE, WHITE, BATH_TILE),
    ('d05', 'Bathroom door', (754.46, 287.27, 787.90, 293.74), 'start', -1, DOOR_H, WHITE, WHITE, BATH_TILE),
    ('d04', 'Room 04 door', (820.72, 300.02, 826.77, 337.63), 'end', 1, DOOR_H, WHITE, WHITE, OAK_FLOOR),
    ('d02', 'Living room door', (651.01, 343.91, 688.64, 354.35), 'end', 1, DOOR_H, WHITE, WHITE, OAK_FLOOR),
    ('d03', 'Room 03 door', (572.64, 509.84, 610.26, 515.90), 'start', 1, DOOR_H, WHITE, WHITE, OAK_FLOOR),
]
for did, label, rect, end, swing, top, leaf, frame, fm in DOORS:
    wall(ST, *rect, top, CEIL, f'{label} lintel')
    door(did, label, rect, end, swing, top, leaf, frame, fm, proud=0 if did == 'entrance' else PROUD)

# Facade windows (a side-hung sash each, as drawn)
wall_window('Room 04 window', (885.08, 343.91, 951.96, 363.56), (885.08, 349.80, 951.96, 353.30))
wall_window('Living window', (845.58, 381.31, 865.23, 464.91), (851.48, 381.31, 854.98, 464.91), mullions=(423.74,))

# Loggia glazing: no masonry on the plan, only the frame line (3.56 pt deep)
for r in ((757.18, 509.84, 845.58, 513.40), (757.18, 513.40, 760.74, 649.02)):
    wall(ST, *r, HEAD, CEIL, 'Loggia glazing lintel')
for r in ((757.18, 509.84, 760.74, 518.41), (840.77, 509.84, 845.58, 513.40)):
    box('Loggia glazing post', OP, DARK, *r, FLOOR, HEAD)
for name, r in (('Living loggia window', (760.74, 509.84, 800.65, 513.40)),
                ('Room 03 loggia window', (757.18, 558.53, 760.74, 649.02))):
    wall(ST, *r, FLOOR, SILL, f'{name} sill wall')
    window(name, r, SILL, HEAD)
for did, label, r, end, swing in (('l02', 'Loggia door, living room', (800.65, 509.84, 840.77, 513.40), 'end', -1),
                                  ('l03', 'Loggia door, room 03', (757.18, 518.41, 760.74, 558.53), 'start', -1)):
    door(did, label, r, end, swing, DOOR_H, GLASS, DARK)
    window(f'{label} transom', r, DOOR_H, HEAD, bottom=False)

# Loggia railings, glass in a slim frame, where the plan draws them
for name, r in (('Loggia railing east', (851.30, 528.03, 854.00, 645.27)),
                ('Loggia railing south', (775.37, 645.60, 823.42, 648.60))):
    along_x = (r[2] - r[0]) > (r[3] - r[1])
    box(f'{name} base', OP, DARK, *r, 0, 0.05)
    box(f'{name} rail', OP, DARK, *r, RAIL - 0.05, RAIL)
    m = ((r[1] + r[3]) / 2, M(0.006)) if along_x else ((r[0] + r[2]) / 2, M(0.006))
    g = (r[0], m[0] - m[1], r[2], m[0] + m[1]) if along_x else (m[0] - m[1], r[1], m[0] + m[1], r[3])
    box(f'{name} glass', OP, GLASS, *g, 0.05, RAIL - 0.05)

# ================================================================ FLOORS (room polygons, plaster faces)
ROOMS = [  # number, Czech name, English name, table m2, rectangles, finish
    ('01', 'Chodba', 'Hall', 10.4, [(609.01, 174.22, 684.66, 290.62), (636.17, 290.62, 684.66, 293.74),
                                    (636.17, 293.74, 820.72, 343.91)], OAK_FLOOR),
    ('02', 'Obývací pokoj + KK', 'Living room + kitchen', 26.9, [(543.38, 354.35, 845.58, 509.84)], OAK_FLOOR),
    ('03', 'Pokoj', 'Bedroom', 16.3, [(543.38, 515.90, 757.18, 649.02)], OAK_FLOOR),
    ('04', 'Pokoj', 'Bedroom', 13.3, [(826.77, 174.22, 963.45, 343.91)], OAK_FLOOR),
    ('05', 'Koupelna', 'Bathroom', 4.7, [(741.92, 177.76, 817.16, 287.27)], BATH_TILE),
    ('06', 'WC', 'WC', 1.7, [(691.13, 207.43, 728.76, 287.27)], BATH_TILE),
    ('07', 'Komora', 'Storeroom', 1.9, [(546.52, 296.67, 630.11, 325.93), (569.51, 325.93, 630.11, 339.72)], BATH_TILE),
    ('08', 'Lodžie', 'Loggia', 8.3, [(760.74, 513.40, 839.30, 645.27), (839.30, 528.03, 865.23, 645.27),
                                     (775.37, 645.27, 823.42, 668.67)], LOGGIA_TILE),
]
print('AREAS  room  model m2  table m2')
for no, cz, en, table_m2, rects, finish in ROOMS:
    area = sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in rects) / S ** 2
    ok = round(area, 1) == table_m2
    print(f'AREA {no} {cz:20s} {area:7.3f} {table_m2:5.1f} {"ok" if ok else "MISMATCH"}')
    for r in rects:
        box(f'Floor {no} {en}', FL, finish, *r, FLOOR, 0)

# Structural slab under the flat's outline, and the ceiling slab (shown only while walking)
OUTLINE = [(593.10, 163.76), (972.28, 163.76), (972.28, 363.56), (865.23, 363.56), (865.23, 668.67),
           (712.00, 668.67), (712.00, 657.90), (533.56, 657.90), (533.56, 279.60), (593.10, 279.60)]
prism('Floor slab', SITE, CONCRETE, OUTLINE, -0.25, FLOOR)
prism('Ceiling slab', CEILING, CEIL_MAT, OUTLINE, CEIL, CEIL + 0.25)

# ================================================================ FITOUT
# Kitchen (02): L of 600 mm base units, sink and hob on the long run
for i, r in enumerate(((545.5, 356.4, 620.7, 381.5), (545.5, 381.5, 570.6, 506.9))):
    box(f'Kitchen base {i + 1}', KF, WHITE, *r, 0.10, WT - 0.04, 0.003)
    box(f'Worktop {i + 1}', KF, OAK, *r, WT - 0.04, WT, 0.002)
box('Kitchen plinth 1', KF, DARK, 547.0, 357.9, 619.2, 379.4, 0, 0.10)
box('Kitchen plinth 2', KF, DARK, 547.0, 379.4, 568.5, 505.4, 0, 0.10)
for x in (570.6, 595.6):
    box('Kitchen unit joint', KF, DARK, x - 0.15, 380.9, x + 0.15, 381.6, 0.12, WT - 0.06)
for y in (406.6, 431.7, 456.8, 481.8):
    box('Kitchen unit joint', KF, DARK, 570.0, y - 0.15, 570.7, y + 0.15, 0.12, WT - 0.06)
box('Sink', KF, STEEL, 549.0, 385.0, 567.0, 403.0, WT, WT + 0.004)
box('Sink bowl', KF, DARK, 550.5, 386.5, 565.5, 401.5, WT + 0.004, WT + 0.005)
cylinder('Kitchen tap', KF, CHROME, 546.8, 394.0, 1.0, 1.0, WT, WT + 0.28)
box('Hob', KF, BLACK_GLASS, 547.5, 432.8, 568.6, 455.8, WT, WT + 0.006)
for i, (cx, cy, r) in enumerate(((553.0, 438.4, 4.0), (563.0, 438.4, 4.6), (553.0, 449.8, 4.6), (563.0, 449.8, 3.7))):
    cylinder(f'Hob ring {i + 1}', KF, DARK, cx, cy, r, r, WT + 0.006, WT + 0.007)

# Bathroom (05): bath across the end wall, WC on the west wall, double basin, towel rail
box('Bathtub', KF, CERAMIC, 741.92, 177.76, 817.16, 211.20, 0, 0.55, 0.02)
box('Bathtub inside', KF, STEEL, 745.5, 181.0, 813.5, 208.0, 0.549, 0.551)
wc('WC 05', KF, 757.0, 230.0, 'E')
basin('Basin 05 a', KF, 797.1, 217.6, 817.16, 242.7)
basin('Basin 05 b', KF, 797.1, 246.9, 817.16, 271.9)
box('Towel rail', KF, WHITE, 742.0, 257.5, 744.5, 283.0, 0.20, 1.40)
# WC (06): bowl on the shaft wall, hand basin on the east wall
wc('WC 06', KF, 710.0, 221.5, 'S')
basin('Hand basin 06', KF, 718.3, 245.0, 728.76, 260.0)
# Storeroom (07): washing machine
box('Washing machine', KF, WHITE, 548.6, 298.8, 573.7, 323.8, 0, 0.85, 0.01)
cylinder('Washing machine door', KF, DARK, 561.15, 311.3, 7.0, 7.0, 0.85, 0.852)

# ================================================================ FURNITURE
wardrobe('Hall wardrobe', FU, 611.0, 176.3, 636.3, 289.0)
# Living room
box('Sideboard', FU, WHITE, 692.0, 356.4, 843.5, 373.2, 0, 0.45, 0.003)
box('TV', FU, BLACK_GLASS, 748.3, 364.0, 789.7, 366.7, 0.55, 1.15, 0.002)
table('Coffee table', FU, 743.6, 388.2, 791.8, 415.2, 0.42)
box('Sofa base', FU, FABRIC, 710.8, 429.9, 823.2, 465.9, 0.02, 0.25, 0.01)
box('Sofa back', FU, FABRIC, 710.8, 457.9, 823.2, 465.9, 0.25, 0.80, 0.02)
box('Sofa arm 1', FU, FABRIC, 710.8, 429.9, 720.0, 457.9, 0.25, 0.60, 0.02)
box('Sofa arm 2', FU, FABRIC, 814.0, 429.9, 823.2, 457.9, 0.25, 0.60, 0.02)
for i, (a, b) in enumerate(((720.0, 749.6), (749.8, 784.4), (784.4, 814.0))):
    box(f'Sofa cushion {i + 1}', FU, FABRIC, a + 0.2, 430.1, b - 0.2, 457.7, 0.25, 0.44, 0.03)
box('Pillow 1', FU, CUSHION, 722.0, 452.0, 742.0, 457.7, 0.44, 0.70, 0.03)
box('Pillow 2', FU, CUSHION, 792.0, 452.0, 812.0, 457.7, 0.44, 0.70, 0.03)
table('Dining table', FU, 619.0, 424.5, 655.1, 480.7, 0.75)
for i, (cx, cy, back) in enumerate(((617.6, 438.9, 'W'), (617.6, 466.35, 'W'), (656.45, 438.9, 'E'), (656.45, 466.35, 'E'))):
    chair(f'Dining chair {i + 1}', FU, cx, cy, back)
# Room 03
wardrobe('Wardrobe 03', FU, 545.4, 518.3, 570.6, 646.9)
bed('Bed 03', FU, 611.7, 562.4, 679.9, 646.6, 'S')
for i, r in enumerate(((591.7, 628.6, 609.7, 646.6), (681.9, 628.6, 699.9, 646.6))):
    box(f'Night table {i + 1}', FU, OAK, *r, 0, 0.50, 0.004)
desk('Desk 03', FU, 706.1, 622.1, 748.8, 646.7)
chair('Chair 03', FU, 727.95, 614.0, 'N')
box('Monitor 03', FU, BLACK_GLASS, 717.3, 641.0, 737.6, 643.0, 0.80, 1.15, 0.002)
box('Monitor 03 stand', FU, DARK, 725.5, 641.4, 729.5, 643.9, 0.75, 0.80)
# Room 04
wardrobe('Wardrobe 04', FU, 828.2, 176.6, 853.4, 285.0)
bed('Bed 04', FU, 924.9, 176.9, 962.2, 261.1, 'N')
desk('Desk 04', FU, 936.9, 266.4, 961.5, 309.2)
chair('Chair 04', FU, 931.8, 287.3, 'W')
box('Monitor 04', FU, BLACK_GLASS, 955.4, 272.5, 957.6, 303.1, 0.80, 1.15, 0.002)
box('Monitor 04 stand', FU, DARK, 956.2, 285.8, 958.7, 289.8, 0.75, 0.80)

# ---------------------------------------------------------------- lights, cameras, renders
world = scene.world or bpy.data.worlds.new('World')
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.62, 0.66, 0.72, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.9
sun = bpy.data.lights.new('Sun', 'SUN')
sun.energy = 3.5
sun.angle = math.radians(8)
sun_ob = bpy.data.objects.new('Sun', sun)
sun_ob.rotation_euler = (math.radians(22), math.radians(-8), math.radians(-30))
RIG.objects.link(sun_ob)

CROP = (520, 114, 1010, 676)      # plan-sheet.png: the plan with its dimension lines


def camera(name, loc, target=None, lens=35, ortho=None):
    from mathutils import Vector
    cd = bpy.data.cameras.new(name)
    cd.clip_end = 200
    if ortho:
        cd.type, cd.ortho_scale = 'ORTHO', ortho
    else:
        cd.lens = lens
    ob = bpy.data.objects.new(name, cd)
    ob.location = loc
    if target:
        ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    RIG.objects.link(ob)
    return ob


cam_top = camera('Cam plan (top)', (X((CROP[0] + CROP[2]) / 2), Y((CROP[1] + CROP[3]) / 2), 40),
                 ortho=max(CROP[2] - CROP[0], CROP[3] - CROP[1]) / S)
cam_view = camera('Cam 3D', (-7.5, -10.0, 12.0), (0.2, 0.0, 1.0), lens=32)
scene.camera = cam_view
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.eevee.taa_render_samples = 48
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'
                    space.clip_end = 200

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'd601-2.blend'))
print('SAVED')

if '--render' in ARGS:
    out = os.path.join(HERE, 'renders')
    os.makedirs(out, exist_ok=True)
    # Top view at 4 px per pt over CROP, so plan-sheet.png lays over it pixel for pixel
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'FLAT'
    scene.display.shading.color_type = 'MATERIAL'
    scene.camera = cam_top
    scene.render.resolution_x, scene.render.resolution_y = (CROP[2] - CROP[0]) * 4, (CROP[3] - CROP[1]) * 4
    scene.render.resolution_percentage = 100
    scene.render.filepath = os.path.join(out, 'top.png')
    bpy.ops.render.render(write_still=True)
    print('RENDERED top.png')
    # Plan cut at 1.0 m (camera clip), walls only: the footprint to compare with the plan's black
    cam_top.data.clip_start = cam_top.location.z - 1.0
    scene.render.film_transparent = True
    hidden = [ob for ob in scene.objects if ob.type == 'MESH' and (ob.users_collection[0] is not ST or 'sill wall' in ob.name)]
    for ob in hidden:
        ob.hide_render = True
    scene.render.filepath = os.path.join(out, 'cut-walls.png')
    bpy.ops.render.render(write_still=True)
    for ob in hidden:
        ob.hide_render = False
    scene.render.film_transparent = False
    scene.render.filepath = os.path.join(out, 'cut-all.png')
    bpy.ops.render.render(write_still=True)
    cam_top.data.clip_start = 0.1
    print('RENDERED cut-walls.png cut-all.png')
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.camera = cam_view
    scene.render.resolution_x, scene.render.resolution_y = 1600, 1200
    scene.render.filepath = os.path.join(out, 'view-3d.png')
    bpy.ops.render.render(write_still=True)
    print('RENDERED view-3d.png')
