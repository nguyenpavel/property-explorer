"""House D1-S14 (two-storey end-of-terrace house) rebuilt from the developer's 1NP and 2NP plans.

Run:  blender -b --factory-startup -P build_house.py -- [--render]

Positions are pixels of the two plan sheets (3508 x 2479), which draw both floors in the
same frame. S comes from the room table (1.01 6.51 m2, 2.02 9.34, 2.03 12.09, 2.06 12.55
measure 111-117 px/m) and the 900/800 door arcs (~115). Heights are not on the plans and
are assumptions (constants below). Doors carry their hinge and closing angle as custom
properties, so the web viewer can swing them.
"""
import bpy, bmesh, math, os, sys
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []

S = 115.0                # px per metre
CX, CY = 2321, 1291      # plan pixel at the world origin (middle of the house)
FLOOR = -0.02            # top of ground slab; ground-floor finishes fill FLOOR..0
L2 = 3.00                # upper floor level (floor to floor, assumed)
CEIL1 = 2.75             # underside of the upper-floor slab
SLAB2 = 2.98             # top of that slab; upper-floor finishes fill SLAB2..L2
TOP = 5.75               # top of upper-floor walls, underside of the roof
DOOR_H = 2.10            # interior door opening
SILL, HEAD = 0.85, 2.30  # windows, above their own floor
RISERS = 17              # stair: 17 x 176 mm


def X(px): return (px - CX) / S
def Y(py): return (CY - py) / S


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


SITE = collection('Site')
S1, F1, O1, K1, U1 = (collection(f'1NP {n}') for n in ('Structure', 'Floors', 'Doors & Windows', 'Fitout', 'Furniture'))
STAIRS = collection('Stairs')
SLABS = collection('Slabs')
S2, F2, O2, K2, U2 = (collection(f'2NP {n}') for n in ('Structure', 'Floors', 'Doors & Windows', 'Fitout', 'Furniture'))
ROOF = collection('Roof', hide_render=True)
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
OAK_FLOOR = tiled('Oak planks', (0.45, 0.30, 0.17), (0.50, 0.34, 0.20), (0.25, 0.16, 0.09), 1.2, 0.19, turn=True)
HALL_TILE = tiled('Hall tiles', (0.70, 0.67, 0.62), (0.66, 0.63, 0.58), (0.45, 0.43, 0.40), 0.6, 0.6, offset=0.0, rough=0.3)
BATH_TILE = tiled('Bath floor tiles', (0.45, 0.45, 0.46), (0.42, 0.42, 0.43), (0.30, 0.30, 0.31), 0.3, 0.3, offset=0.0, rough=0.3)
DECK = tiled('Decking', (0.28, 0.17, 0.09), (0.31, 0.19, 0.10), (0.10, 0.06, 0.03), 2.4, 0.14, rough=0.7, turn=True)
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
CANOPY = material('Canopy', (0.85, 0.85, 0.84), 0.8)
STONE = material('Hearth stone', (0.12, 0.12, 0.12), 0.6)


# ---------------------------------------------------------------- geometry helpers
def link(name, me, loc, coll, mat):
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    coll.objects.link(ob)
    return ob


def box(name, coll, mat, x0, y0, x1, y1, z0, z1, bevel=0.0):
    """Axis-aligned box: plan pixel rectangle x0..x1, y0..y1, heights z0..z1 in metres."""
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
    """Vertical elliptic cylinder; centre and radii in plan pixels."""
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
    """Plan polygon (pixels) extruded from z0 to z1, origin at its centroid."""
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


def door(did, label, coll, struct, level, rect, hinge_end, swing, top=DOOR_H, wall_top=None,
         leaf_mat=WHITE, jamb=9, frame_mat=WHITE):
    """Door in an opening rect (pixels, spanning the wall thickness), drawn open as on the plan.

    hinge_end: 'start' or 'end' of the opening along its length; swing: +1/-1, the side
    the leaf opens to (perpendicular to the wall). The leaf stores its hinge and the
    rotation that closes it, in three.js terms (y up, plan y = +z).
    """
    x0, y0, x1, y1 = rect
    along_x = (x1 - x0) > (y1 - y0)
    a0, a1 = (x0, x1) if along_x else (y0, y1)
    f0, f1 = (y0, y1) if along_x else (x0, x1)
    hinge_a = a0 + jamb if hinge_end == 'start' else a1 - jamb
    hinge_f = f1 if swing > 0 else f0
    length = (a1 - a0) - 2 * jamb
    to_close = 1 if hinge_end == 'start' else -1
    # frame: two jambs and a head across the wall thickness
    for i, (j0, j1) in enumerate(((a0, a0 + jamb), (a1 - jamb, a1))):
        r = (j0, f0, j1, f1) if along_x else (f0, j0, f1, j1)
        box(f'{label} jamb {i + 1}', coll, frame_mat, *r, level + FLOOR, level + top)
    head = (a0 + jamb, f0, a1 - jamb, f1) if along_x else (f0, a0 + jamb, f1, a1 - jamb)
    box(f'{label} head', coll, frame_mat, *head, level + top - 0.06, level + top)
    if wall_top is not None:
        wall(struct, x0, y0, x1, y1, level + top, wall_top, f'{label} lintel')
    # open leaf: perpendicular to the wall at the hinge, on the swing side
    side = (0, 9) if to_close > 0 else (-9, 0)
    ext = (hinge_f, hinge_f + swing * length)
    if along_x:
        lr = (hinge_a + side[0], min(ext), hinge_a + side[1], max(ext))
        open_dir, close_dir = (0, swing), (to_close, 0)
    else:
        lr = (min(ext), hinge_a + side[0], max(ext), hinge_a + side[1])
        open_dir, close_dir = (swing, 0), (0, to_close)
    leaf = box(f'Door {did}', coll, leaf_mat, *lr, level + 0.005, level + top - 0.065, 0.003)
    # handle near the free end, through the leaf
    ea = hinge_a + (side[0] + side[1]) / 2
    ef = hinge_f + swing * (length - 12)
    hr = (ea - 11, ef - 7, ea + 11, ef + 7) if along_x else (ef - 7, ea - 11, ef + 7, ea + 11)
    handle = box(f'Door {did} handle', coll, CHROME, *hr, level + 1.0, level + 1.03)
    ox, oz = open_dir
    cx, cz = close_dir
    leaf['door_id'] = did
    leaf['door_label'] = label
    leaf['hinge_x'] = X(hinge_a if along_x else hinge_f)
    leaf['hinge_z'] = -Y(hinge_f if along_x else hinge_a)
    leaf['close_angle'] = -math.atan2(ox * cz - oz * cx, ox * cx + oz * cz)
    leaf['level'] = level
    handle['door_part'] = did
    return leaf


def window(coll, name, x0, x1, yf0, yf1, z0, z1, mullions=(), bottom=True):
    """Frame and glass in a horizontal wall; x0..x1 the opening, yf0..yf1 the frame depth."""
    f = 13
    box(f'{name} frame left', coll, DARK, x0, yf0, x0 + f, yf1, z0, z1)
    box(f'{name} frame right', coll, DARK, x1 - f, yf0, x1, yf1, z0, z1)
    box(f'{name} frame top', coll, DARK, x0 + f, yf0, x1 - f, yf1, z1 - 0.07, z1)
    if bottom:
        box(f'{name} frame bottom', coll, DARK, x0 + f, yf0, x1 - f, yf1, z0, z0 + 0.07)
    for i, m in enumerate(mullions):
        box(f'{name} mullion {i + 1}', coll, DARK, m - 7, yf0, m + 7, yf1, z0, z1)
    gm = (yf0 + yf1) / 2
    box(f'{name} glass', coll, GLASS, x0 + f, gm - 2, x1 - f, gm + 2, z0 + (0.07 if bottom else 0), z1 - 0.07)


def facade_window(struct, coll, name, x0, x1, top_side, level, sill, head, wall_top, mullions=()):
    """Window opening in the top (garden) or bottom (street) wall with sill wall and lintel."""
    yw0, yw1 = (590, 644) if top_side else (1940, 1993)
    yf0, yf1 = (612, 628) if top_side else (1954, 1970)
    if sill > 0:
        wall(struct, x0, yw0, x1, yw1, level + (FLOOR if level == 0 else 0), level + sill, f'{name} sill wall')
    wall(struct, x0, yw0, x1, yw1, level + head, wall_top, f'{name} lintel')
    window(coll, name, x0, x1, yf0, yf1, level + sill, level + head, mullions, bottom=True)


def chair(name, coll, cx, cy, back, z=0.0, mat=DARK):
    """Chair centred at (cx, cy) px; back = side of the backrest: 'N', 'S', 'E' or 'W'."""
    h = 22
    box(f'{name} seat', coll, mat, cx - h, cy - h, cx + h, cy + h, z + 0.43, z + 0.47, 0.004)
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        lx, ly = cx + sx * (h - 3), cy + sy * (h - 3)
        box(f'{name} leg {i + 1}', coll, mat, lx - 2, ly - 2, lx + 2, ly + 2, z, z + 0.43)
    r = {'N': (cx - h, cy - h, cx + h, cy - h + 4), 'S': (cx - h, cy + h - 4, cx + h, cy + h),
         'W': (cx - h, cy - h, cx - h + 4, cy + h), 'E': (cx + h - 4, cy - h, cx + h, cy + h)}[back]
    box(f'{name} back', coll, mat, *r, z + 0.47, z + 0.86, 0.004)


def bed(name, coll, x0, y0, x1, y1, head, z=0.0):
    """Bed filling the rectangle; head = 'N', 'S', 'E' or 'W'."""
    box(f'{name} frame', coll, OAK, x0, y0, x1, y1, z, z + 0.30, 0.01)
    box(f'{name} mattress', coll, BEDDING, x0 + 2, y0 + 2, x1 - 2, y1 - 2, z + 0.30, z + 0.50, 0.03)
    p = 26
    pr = {'N': (x0 + 6, y0 + 6, x1 - 6, y0 + p), 'S': (x0 + 6, y1 - p, x1 - 6, y1 - 6),
          'W': (x0 + 6, y0 + 6, x0 + p, y1 - 6), 'E': (x1 - p, y0 + 6, x1 - 6, y1 - 6)}[head]
    box(f'{name} pillow', coll, BEDDING, *pr, z + 0.50, z + 0.60, 0.03)
    hb = {'N': (x0, y0 - 6, x1, y0), 'S': (x0, y1, x1, y1 + 6), 'W': (x0 - 6, y0, x0, y1), 'E': (x1, y0, x1 + 6, y1)}[head]
    box(f'{name} headboard', coll, OAK, *hb, z, z + 0.95)


def desk(name, coll, x0, y0, x1, y1, z=0.0):
    box(f'{name} top', coll, OAK, x0, y0, x1, y1, z + 0.72, z + 0.75, 0.003)
    if (x1 - x0) > (y1 - y0):
        box(f'{name} side 1', coll, WHITE, x0, y0, x0 + 4, y1, z, z + 0.72)
        box(f'{name} side 2', coll, WHITE, x1 - 4, y0, x1, y1, z, z + 0.72)
    else:
        box(f'{name} side 1', coll, WHITE, x0, y0, x1, y0 + 4, z, z + 0.72)
        box(f'{name} side 2', coll, WHITE, x0, y1 - 4, x1, y1, z, z + 0.72)


def wc(name, coll, cx, cy, facing, z=0.0):
    """Wall-hung WC, bowl centred at (cx, cy) px, facing 'N', 'S', 'E' or 'W'."""
    vertical = facing in 'NS'
    rx, ry = (19, 28) if vertical else (28, 19)
    cylinder(f'{name} bowl', coll, CERAMIC, cx, cy, rx, ry, z + 0.30, z + 0.40)
    cylinder(f'{name} seat', coll, CERAMIC, cx, cy, rx + 2, ry + 2, z + 0.40, z + 0.43)
    d = {'N': (0, 1), 'S': (0, -1), 'E': (-1, 0), 'W': (1, 0)}[facing]   # towards the wall
    mx, my = cx + d[0] * 30, cy + d[1] * 30
    box(f'{name} mount', coll, CERAMIC, mx - 16, my - 16, mx + 16, my + 16, z + 0.28, z + 0.42, 0.01)


def basin(name, coll, x0, y0, x1, y1, z=0.0):
    box(f'{name}', coll, CERAMIC, x0, y0, x1, y1, z + 0.70, z + 0.85, 0.015)
    cylinder(f'{name} bowl', coll, STEEL, (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) * 0.32, (y1 - y0) * 0.30, z + 0.849, z + 0.851)


def wardrobe(name, coll, x0, y0, x1, y1, z=0.0, height=2.40):
    box(f'{name}', coll, WARDROBE, x0, y0, x1, y1, z, z + height, 0.004)


# ================================================================ GROUND FLOOR (1NP)
box('Ground slab', SITE, CONCRETE, 1907, 590, 2735, 1993, -0.30, FLOOR)
box('Terrace deck', SITE, DECK, 2257, 412, 2695, 590, -0.22, -0.05)
box('Entrance canopy', SITE, CANOPY, 1925, 1993, 2350, 2060, 2.55, 2.70)

# Exterior walls run to the upper floor level
wall(S1, 1907, 590, 1960, 1993, FLOOR, L2, 'Gable wall')
wall(S1, 2660, 590, 2735, 1993, FLOOR, L2, 'Party wall')
for x0, x1 in ((1960, 2009), (2143, 2335), (2622, 2660)):
    wall(S1, x0, 590, x1, 644, FLOOR, L2, 'Garden wall')
for x0, x1 in ((1960, 2161), (2319, 2465), (2570, 2660)):
    wall(S1, x0, 1940, x1, 1993, FLOOR, L2, 'Street wall')
facade_window(S1, O1, 'Living window', 2009, 2143, True, 0, SILL, HEAD, L2)
# Terrace glazing: fixed pane, then a door to the deck
wall(S1, 2335, 590, 2521, 644, 2.35, L2, 'Terrace glazing lintel')
window(O1, 'Terrace glazing', 2335, 2521, 612, 628, 0.0, 2.35)
door('terrace', 'Terrace door', O1, S1, 0, (2521, 590, 2622, 644), 'end', 1, top=2.35, wall_top=L2,
     leaf_mat=GLASS, frame_mat=DARK)
# Front door with a side light, and the storeroom's own outside door
door('entrance', 'Front door', O1, S1, 0, (2161, 1940, 2272, 1993), 'start', -1, top=2.20, wall_top=L2,
     leaf_mat=DARK, frame_mat=DARK)
wall(S1, 2272, 1940, 2319, 1993, 2.20, L2, 'Side light lintel')
window(O1, 'Side light', 2272, 2319, 1954, 1970, 0.0, 2.20)
door('storeroom', 'Storeroom door', O1, S1, 0, (2465, 1940, 2570, 1993), 'start', -1, top=2.10, wall_top=L2,
     leaf_mat=DARK, frame_mat=DARK)

# Interior walls up to the slab
for r in ((1960, 1311, 2208, 1340), (2314, 1311, 2323, 1340),     # living room / stair hall
          (2323, 1311, 2341, 1616),                               # hall / kitchen
          (2323, 1616, 2660, 1644),                               # kitchen / entrance hall + storeroom
          (1960, 1571, 2209, 1600), (2313, 1571, 2323, 1600),     # stair hall / entrance hall
          (2144, 1600, 2157, 1629), (2144, 1721, 2157, 1749), (2144, 1841, 2157, 1940),  # WC + tech / entrance hall
          (1960, 1728, 2144, 1742),                               # WC / tech room
          (2395, 1644, 2424, 1940)):                              # entrance hall / storeroom
    wall(S1, *r, FLOOR, CEIL1)
wall(S1, 2061, 1455, 2198, 1470, FLOOR, L2 + 0.95, 'Stair divider')   # between the two flights, a parapet upstairs
wall(S1, 1962, 1000, 2015, 1062, 1.30, CEIL1, 'Chimney breast')
door('living', 'Living room door', O1, S1, 0, (2208, 1311, 2314, 1340), 'end', -1, wall_top=CEIL1)
door('hall', 'Entrance hall door', O1, S1, 0, (2209, 1571, 2313, 1600), 'start', 1, wall_top=CEIL1)
door('wc', 'WC door', O1, S1, 0, (2144, 1629, 2157, 1721), 'end', -1, wall_top=CEIL1)
door('tech', 'Tech room door', O1, S1, 0, (2144, 1749, 2157, 1841), 'start', -1, wall_top=CEIL1)
door('closet', 'Under-stair closet door', O1, S1, 0, (2182, 1475, 2198, 1571), 'end', 1, top=2.0, wall_top=2.55)

# Floors: vinyl planks in living areas, tiles in kitchen, halls, WC, tech room, storeroom
for r in ((1960, 644, 2660, 1302), (2335, 616, 2622, 644), (1960, 1302, 2341, 1311),
          (2208, 1311, 2314, 1340), (2198, 1340, 2323, 1571)):
    box('Floor 1.06 / 1.05', F1, OAK_FLOOR, *r, FLOOR, 0)
for r in ((2341, 1302, 2660, 1616), (1960, 1340, 2198, 1571), (2209, 1571, 2313, 1600),
          (2157, 1600, 2395, 1940), (2161, 1940, 2319, 1993), (2144, 1629, 2157, 1721), (2144, 1749, 2157, 1841),
          (2424, 1644, 2660, 1940), (2465, 1940, 2570, 1993)):
    box('Floor tiles', F1, HALL_TILE, *r, FLOOR, 0)
for r in ((1960, 1600, 2144, 1728), (1960, 1742, 2144, 1940)):
    box('Floor 1.03 / 1.02', F1, BATH_TILE, *r, FLOOR, 0)

# Kitchen: tall fridge, U of base units, hob on the right run, sink under the window-less wall
WT = 0.90
box('Fridge', K1, WHITE, 2342, 1311, 2410, 1382, 0, 2.10, 0.004)
for i, r in enumerate(((2342, 1382, 2410, 1545), (2342, 1545, 2660, 1615), (2589, 1311, 2660, 1545))):
    box(f'Kitchen base {i + 1}', K1, WHITE, *r, 0.10, WT - 0.04, 0.003)
    box(f'Worktop {i + 1}', K1, OAK, *r, WT - 0.04, WT, 0.002)
box('Kitchen plinth', K1, DARK, 2346, 1386, 2406, 1611, 0, 0.10)
box('Kitchen plinth 2', K1, DARK, 2406, 1549, 2656, 1611, 0, 0.10)
box('Kitchen plinth 3', K1, DARK, 2593, 1315, 2656, 1549, 0, 0.10)
box('Hob', K1, BLACK_GLASS, 2596, 1404, 2656, 1476, WT, WT + 0.006)
for i, (cx, cy) in enumerate(((2608, 1416), (2644, 1416), (2610, 1458), (2645, 1458))):
    cylinder(f'Hob ring {i + 1}', K1, DARK, cx, cy, 12, 12, WT + 0.006, WT + 0.007)
box('Sink', K1, STEEL, 2456, 1554, 2518, 1607, WT, WT + 0.004)
box('Sink bowl', K1, DARK, 2462, 1560, 2512, 1601, WT + 0.004, WT + 0.005)
box('Drainer', K1, STEEL, 2523, 1554, 2584, 1607, WT, WT + 0.004)
cylinder('Kitchen tap', K1, CHROME, 2487, 1608, 2.5, 2.5, WT, WT + 0.28)

# Fireplace stove against the gable wall, flue into the chimney breast
box('Hearth', K1, STONE, 1960, 983, 2026, 1101, 0, 0.03)
box('Stove', K1, DARK, 1966, 1012, 2020, 1072, 0.03, 1.05, 0.01)
cylinder('Stove flue', K1, DARK, 1990, 1031, 8, 8, 1.05, 1.30)

# WC and tech room
box('WC pre-wall', K1, WALL, 1961, 1600, 1978, 1728, 0, 1.20)
wc('WC 1.03', K1, 2008, 1667, 'E')
basin('Hand basin 1.03', K1, 2067, 1602, 2100, 1630)
box('Washing machine', K1, WHITE, 1968, 1784, 2039, 1855, 0, 0.85, 0.01)
box('Dryer', K1, WHITE, 1968, 1861, 2039, 1932, 0, 0.85, 0.01)

# Living room furniture
box('TV unit', U1, WHITE, 1962, 650, 2005, 980, 0, 0.45, 0.003)
box('TV', U1, BLACK_GLASS, 1988, 715, 1996, 865, 0.55, 1.05, 0.002)
box('Sofa base', U1, FABRIC, 2155, 715, 2405, 810, 0.02, 0.25, 0.01)
box('Sofa chaise base', U1, FABRIC, 2318, 810, 2405, 975, 0.02, 0.25, 0.01)
box('Sofa back', U1, FABRIC, 2155, 715, 2405, 738, 0.25, 0.80, 0.02)
box('Sofa chaise back', U1, FABRIC, 2385, 738, 2405, 975, 0.25, 0.80, 0.02)
box('Sofa arm', U1, FABRIC, 2155, 738, 2175, 810, 0.25, 0.60, 0.02)
box('Sofa cushions', U1, FABRIC, 2175, 738, 2385, 808, 0.25, 0.44, 0.03)
box('Sofa chaise cushion', U1, FABRIC, 2320, 808, 2385, 973, 0.25, 0.44, 0.03)
box('Pillow 1', U1, CUSHION, 2185, 740, 2235, 752, 0.44, 0.70, 0.03)
box('Pillow 2', U1, CUSHION, 2368, 870, 2382, 920, 0.44, 0.70, 0.03)
box('Coffee table', U1, OAK, 2170, 860, 2230, 980, 0.38, 0.42, 0.003)
for i, (lx, ly) in enumerate(((2172, 862), (2224, 862), (2172, 974), (2224, 974))):
    box(f'Coffee table leg {i + 1}', U1, DARK, lx, ly, lx + 4, ly + 4, 0, 0.38)
box('Dining table', U1, OAK, 2448, 1097, 2658, 1204, 0.72, 0.75, 0.003)
for i, (lx, ly) in enumerate(((2452, 1101), (2650, 1101), (2452, 1196), (2650, 1196))):
    box(f'Dining table leg {i + 1}', U1, DARK, lx, ly, lx + 4, ly + 4, 0, 0.72)
for i, cx in enumerate((2486, 2553, 2621)):
    chair(f'Dining chair {i + 1}', U1, cx, 1072, 'N')
    chair(f'Dining chair {i + 4}', U1, cx, 1229, 'S')
wardrobe('Hall wardrobe', U1, 2324, 1635, 2393, 1940)
wardrobe('Storeroom shelves', U1, 2590, 1645, 2658, 1940, height=2.0)

# ================================================================ STAIR (U-shaped, winders on the gable side)
# Starts in the stair hall at x = 2198 heading west, turns 180 degrees around (2061, 1462)
# and climbs east to the upper corridor. The closet 1.04 sits under the upper flight.
RISE = L2 / RISERS
C = (2061, 1462)
BOX = (1960, 1340, 2061, 1571)


def ray(theta):
    dx, dy = -math.sin(theta), -math.cos(theta)
    ts = []
    if dx < -1e-9: ts.append((BOX[0] - C[0]) / dx)
    if dy < -1e-9: ts.append((BOX[1] - C[1]) / dy)
    if dy > 1e-9: ts.append((BOX[3] - C[1]) / dy)
    t = min(ts)
    return (C[0] + dx * t, C[1] + dy * t)


CORNERS = [(math.atan2(C[0] - BOX[0], C[1] - BOX[1]), (BOX[0], BOX[1])),
           (math.atan2(C[0] - BOX[0], C[1] - BOX[3]), (BOX[0], BOX[3]))]
treads = [[(a, 1340), (b, 1340), (b, 1452), (a, 1452)] for a, b in ((2168, 2198), (2134, 2168), (2097, 2134), (2061, 2097))]
for j in range(8):
    t0, t1 = j * math.pi / 8, (j + 1) * math.pi / 8
    treads.append([C, ray(t0)] + [p for a, p in CORNERS if t0 < a < t1] + [ray(t1)])
treads += [[(a, 1470), (b, 1470), (b, 1571), (a, 1571)] for a, b in ((2061, 2097), (2097, 2134), (2134, 2168), (2168, 2198))]
for k, pts in enumerate(treads, start=1):
    h = k * RISE
    prism(f'Stair tread {k:02d}', STAIRS, OAK, pts, max(FLOOR, h - 0.22), h)

# ================================================================ UPPER FLOOR SLAB (hole over the stair)
for r in ((1960, 644, 2660, 1340), (2198, 1340, 2660, 1571), (1960, 1571, 2660, 1940)):
    box('Floor slab', SLABS, CONCRETE, *r, CEIL1, SLAB2)

# ================================================================ UPPER FLOOR (2NP)
wall(S2, 1907, 590, 1960, 1993, L2, TOP, 'Gable wall')
wall(S2, 2660, 590, 2735, 1993, L2, TOP, 'Party wall')
for x0, x1 in ((1960, 2009), (2143, 2333), (2620, 2660)):
    wall(S2, x0, 590, x1, 644, L2, TOP, 'Garden wall')
for x0, x1 in ((1960, 2083), (2306, 2465), (2565, 2660)):
    wall(S2, x0, 1940, x1, 1993, L2, TOP, 'Street wall')
facade_window(S2, O2, 'Room 2.07 window', 2009, 2143, True, L2, SILL, HEAD, TOP)
facade_window(S2, O2, 'Bedroom window', 2333, 2620, True, L2, SILL, HEAD, TOP, mullions=(2476,))
facade_window(S2, O2, 'Study window', 2083, 2306, False, L2, SILL, HEAD, TOP, mullions=(2194,))
facade_window(S2, O2, 'Room 2.03 window', 2465, 2565, False, L2, SILL, HEAD, TOP)

for r in ((2316, 644, 2329, 1034), (2316, 1138, 2329, 1179), (2316, 1271, 2329, 1298),    # corridor east side
          (2316, 1391, 2329, 1456), (2316, 1560, 2329, 1940),
          (2198, 990, 2207, 1004), (2310, 990, 2316, 1004),                                 # corridor north end
          (2184, 990, 2198, 1087), (2184, 1180, 2198, 1306),                                # corridor west side
          (1960, 1062, 2184, 1078),                                                         # 2.07 / 2.08
          (1960, 1306, 2198, 1337),                                                         # 2.08 / stair
          (1960, 1568, 2205, 1584), (2310, 1568, 2316, 1584),                               # stair / 2.02
          (2329, 1156, 2660, 1172),                                                         # 2.06 / 2.05
          (2329, 1279, 2447, 1293), (2447, 1279, 2458, 1448), (2329, 1416, 2447, 1448),      # WC 2.04
          (2458, 1434, 2660, 1448)):                                                        # 2.05 / 2.03
    wall(S2, *r, SLAB2, TOP)
wall(S2, 1962, 1000, 2015, 1062, SLAB2, TOP + 0.85, 'Chimney')
door('r207', 'Room 2.07 door', O2, S2, L2, (2207, 990, 2310, 1004), 'end', -1, wall_top=TOP)
door('r208', 'Bathroom 2.08 door', O2, S2, L2, (2184, 1087, 2198, 1180), 'start', -1, wall_top=TOP)
door('r206', 'Bedroom door', O2, S2, L2, (2316, 1034, 2329, 1138), 'end', 1, wall_top=TOP)
door('r205', 'Bathroom 2.05 door', O2, S2, L2, (2316, 1179, 2329, 1271), 'start', 1, wall_top=TOP)
door('r204', 'WC 2.04 door', O2, S2, L2, (2316, 1298, 2329, 1391), 'end', -1, wall_top=TOP)
door('r203', 'Room 2.03 door', O2, S2, L2, (2316, 1456, 2329, 1560), 'start', 1, wall_top=TOP)
door('r202', 'Study door', O2, S2, L2, (2205, 1568, 2310, 1584), 'end', 1, wall_top=TOP)
box('Stair railing glass', K2, GLASS, 2191, 1340, 2197, 1455, L2, L2 + 0.95)
box('Stair railing rail', K2, DARK, 2190, 1340, 2198, 1455, L2 + 0.95, L2 + 1.0)

for r in ((1960, 644, 2184, 1062), (2184, 644, 2316, 990), (2198, 990, 2316, 1584),
          (2329, 644, 2660, 1156), (2316, 1034, 2329, 1138), (2316, 1456, 2329, 1560), (2205, 1568, 2310, 1584),
          (2329, 1448, 2660, 1940), (1960, 1584, 2316, 1940)):
    box('Floor 2NP', F2, OAK_FLOOR, *r, SLAB2, L2)
for r in ((1960, 1078, 2184, 1306), (2184, 1087, 2198, 1180), (2329, 1172, 2660, 1279), (2458, 1279, 2660, 1434),
          (2329, 1293, 2447, 1416), (2316, 1179, 2329, 1271), (2316, 1298, 2329, 1391)):
    box('Floor 2NP tiles', F2, BATH_TILE, *r, SLAB2, L2)

# Bathrooms
basin('Basin 2.08', K2, 1962, 1090, 2006, 1150, L2)
box('Shower tray 2.08', K2, CERAMIC, 1962, 1191, 2075, 1305, L2, L2 + 0.04, 0.004)
box('Shower glass 2.08', K2, GLASS, 1962, 1185, 2075, 1189, L2 + 0.04, L2 + 2.0)
box('Shower glass 2.08 side', K2, GLASS, 2075, 1189, 2079, 1305, L2 + 0.04, L2 + 2.0)
wc('WC 2.08', K2, 2131, 1272, 'N', L2)
box('Bathtub', K2, CERAMIC, 2460, 1345, 2656, 1432, L2, L2 + 0.55, 0.02)
box('Bathtub inside', K2, STEEL, 2472, 1356, 2644, 1421, L2 + 0.549, L2 + 0.551)
basin('Basin 2.05', K2, 2588, 1239, 2640, 1297, L2)
box('Pre-wall 2.05', K2, WALL, 2640, 1173, 2656, 1345, L2, L2 + 1.2)
wc('WC 2.04', K2, 2382, 1386, 'N', L2)
basin('Hand basin 2.04', K2, 2420, 1300, 2445, 1335, L2)

# Bedrooms and study
desk('Desk 2.07', U2, 1962, 658, 2055, 805, L2)
chair('Chair 2.07', U2, 2078, 732, 'E', L2)
bed('Bed 2.07', U2, 2210, 650, 2310, 870, 'N', L2)
wardrobe('Wardrobe 2.07', U2, 2017, 1000, 2183, 1062, L2)
bed('Bed 2.06', U2, 2435, 733, 2650, 936, 'E', L2)
wardrobe('Wardrobe 2.06', U2, 2437, 1085, 2656, 1155, L2)
wardrobe('Wardrobe 2.02', U2, 1962, 1588, 2031, 1907, L2)
desk('Desk 2.02', U2, 2220, 1770, 2310, 1915, L2)
chair('Chair 2.02', U2, 2192, 1840, 'W', L2)
bed('Bed 2.03', U2, 2555, 1456, 2655, 1670, 'N', L2)
desk('Desk 2.03', U2, 2330, 1775, 2425, 1920, L2)
chair('Chair 2.03', U2, 2447, 1840, 'E', L2)
wardrobe('Wardrobe 2.03', U2, 2585, 1770, 2656, 1930, L2)

box('Roof slab', ROOF, CONCRETE, 1907, 590, 2735, 1993, TOP, TOP + 0.30)

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

CROP = (1880, 395, 2850, 2100)      # plan area of both sheets: house, terrace, canopy


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
                 ortho=(CROP[3] - CROP[1]) / S)
cam_view = camera('Cam 3D', (-9.0, -12.0, 15.0), (0.3, 0.0, 1.5), lens=32)
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

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'house-d1-s14.blend'))
print('SAVED')

if '--render' in ARGS:
    out = os.path.join(HERE, 'renders')
    os.makedirs(out, exist_ok=True)
    upper = [S2, F2, O2, K2, U2, SLABS]
    shots = [('1np-top.png', cam_top, (CROP[2] - CROP[0], CROP[3] - CROP[1]), False),
             ('2np-top.png', cam_top, (CROP[2] - CROP[0], CROP[3] - CROP[1]), True),
             ('view-3d.png', cam_view, (1600, 1200), True)]
    for fname, cam, (rx, ry), show_upper in shots:
        for c in upper:
            c.hide_render = not show_upper
        scene.camera = cam
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
        scene.render.resolution_percentage = 100
        scene.render.filepath = os.path.join(out, fname)
        bpy.ops.render.render(write_still=True)
        print('RENDERED', fname)
