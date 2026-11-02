"""Flat D.601 with real furniture: the D.601 build (../d601/build_d601.py) furnished with models from
the NVIDIA Residential and SimReady Furniture packs, prepared by tools/prep_assets.py into assets/*.blend.

Run:  blender -b --factory-startup -P build_real.py -- [--render]

Positions are PDF points of 'D.601 - Půdorys a dispozice.pdf' as displayed (the page is
rotated 90 degrees), read from its vector linework. The sheet is 1:50, so one point is
25.4 / 72 x 50 = 17.639 mm; the dimension strings agree (room 04: 3300 mm = 187.09 pt).
Heights the sheet gives: doors 2100, windows 2280 tall on a 535 sill, loggia glazing 2970
from -155. All openings end at 2.815 m, the soffit. Suspended ceilings T02b sit at 2.550 m.
Doors carry their hinge and closing angle as custom properties for the web viewer.
"""
import bpy, bmesh, json, math, os, sys
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []

K = 25.4 / 72 * 50 / 1000    # metres per PDF point (1:50)
S = 1 / K                    # points per metre
CX, CY = 400.0, 420.0        # plan point at the world origin (middle of the flat)
FLOOR = -0.02                # finishes fill FLOOR..0
CEIL = 2.815                 # soffit: head of every window and glazed door on the sheet
SUSP = 2.55                  # suspended ceilings T02b (hall, WC, bathroom, storage, kitchen)
DOOR_H = 2.10                # every door on the sheet is x/2100, the front door included
SILL, HEAD = 0.535, CEIL     # windows 2280 (535)
LOGGIA = -0.03               # loggia paving (assumed, below the insulation top +17.085 on a +17.160 floor)
WT = 0.90                    # kitchen worktop
JAMB = 0.05 * S              # door frame: 800 opening for a 700 leaf


def X(px): return (px - CX) * K
def Y(py): return (CY - py) * K


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


STRUCT = collection('Structure')
FLOORS = collection('Floors')
OPEN = collection('Doors & Windows')
FIT = collection('Fitout')
FURN = collection('Furniture')
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
CEILING = material('Ceiling', (0.90, 0.90, 0.89), 0.9)
OAK_FLOOR = tiled('Oak planks', (0.45, 0.30, 0.17), (0.50, 0.34, 0.20), (0.25, 0.16, 0.09), 1.2, 0.19)
HALL_TILE = tiled('Hall tiles', (0.70, 0.67, 0.62), (0.66, 0.63, 0.58), (0.45, 0.43, 0.40), 0.6, 0.6, offset=0.0, rough=0.3)
BATH_TILE = tiled('Bath floor tiles', (0.45, 0.45, 0.46), (0.42, 0.42, 0.43), (0.30, 0.30, 0.31), 0.3, 0.3, offset=0.0, rough=0.3)
PAVING = tiled('Paving', (0.48, 0.48, 0.46), (0.44, 0.44, 0.42), (0.25, 0.25, 0.24), 0.6, 0.3, rough=0.8)
WHITE = material('White lacquer', (0.88, 0.88, 0.88), 0.35)
CERAMIC = material('Ceramic', (0.95, 0.95, 0.95), 0.1)
ENAMEL = material('Enamel', (0.80, 0.82, 0.84), 0.15)
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
TEXDIR = os.path.join(HERE, 'cache', 'tex')
ASSETS = os.path.join(HERE, 'assets')


def textured(name, color, normal=None, orm=None, rough=None, tile=1.0):
    """Image-textured material for the modelled pieces; tile = metres per texture repeat (world-space UVs)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1 / tile, 1 / tile, 1)
    nt.links.new(tc.outputs['UV'], mp.inputs['Vector'])

    def img(f, non_color):
        n = nt.nodes.new('ShaderNodeTexImage')
        n.image = bpy.data.images.load(os.path.join(TEXDIR, f), check_existing=True)
        n.image.colorspace_settings.name = 'Non-Color' if non_color else 'sRGB'
        nt.links.new(mp.outputs['Vector'], n.inputs['Vector'])
        return n
    nt.links.new(img(color, False).outputs['Color'], p.inputs['Base Color'])
    if orm:
        sep = nt.nodes.new('ShaderNodeSeparateColor')
        nt.links.new(img(orm, True).outputs['Color'], sep.inputs['Color'])
        nt.links.new(sep.outputs['Green'], p.inputs['Roughness'])
        nt.links.new(sep.outputs['Blue'], p.inputs['Metallic'])
    elif rough:
        nt.links.new(img(rough, True).outputs['Color'], p.inputs['Roughness'])
    else:
        p.inputs['Roughness'].default_value = 0.85
    if normal:
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nt.links.new(img(normal, True).outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], p.inputs['Normal'])
    return m


# Wood and fabric from the Residential pack's Daybed, for the pieces the packs have no model of
ASH = textured('Ash wood', 'Ash_BaseColor_f0255d_512.jpg', 'Ash_Normal_40e2c2_512.jpg', orm='Ash_ORM_cc445b_512.jpg', tile=0.8)
COTTON = textured('Cotton', 'cotton_roughly_woven_diff_7c96bc_512.jpg', 'cotton_roughly_woven_norm_f2c8fb_512.jpg',
                  rough='cotton_roughly_woven_rough_3de4d0_512.jpg', tile=0.35)
FELT = textured('Felt', 'felt_white_diff_0b7e80_512.jpg', tile=0.5)


# ---------------------------------------------------------------- geometry helpers
def link(name, me, loc, coll, mat):
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    coll.objects.link(ob)
    return ob


def box(name, coll, mat, x0, y0, x1, y1, z0, z1, bevel=0.0):
    """Axis-aligned box: plan point rectangle x0..x1, y0..y1, heights z0..z1 in metres."""
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
    """Vertical elliptic cylinder; centre and radii in plan points."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=1.0, radius2=1.0, depth=1.0,
                          matrix=Matrix.Diagonal((rx * K, ry * K, z1 - z0, 1)))
    for f in bm.faces:
        f.smooth = len(f.verts) == 4
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return link(name, me, (X(cx), Y(cy), (z0 + z1) / 2), coll, mat)


def prism(name, coll, mat, pts, z0, z1):
    """Plan polygon (points) extruded from z0 to z1, origin at its centroid."""
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


def inset(pts, e):
    """Move every edge of a rectilinear polygon inwards by e points."""
    n = len(pts)
    area2 = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    sgn = 1 if area2 > 0 else -1          # +1: counter-clockwise in plan points (y down)
    out = []
    for i in range(n):
        p, a, b = pts[i], pts[i - 1], pts[(i + 1) % n]
        nx = ny = 0.0
        for (x0, y0), (x1, y1) in ((a, p), (p, b)):
            dx, dy = x1 - x0, y1 - y0
            L = math.hypot(dx, dy)
            # inward normal of the edge
            nx += -sgn * dy / L
            ny += sgn * dx / L
        out.append((p[0] + nx * e, p[1] + ny * e))
    return out


def wall(x0, y0, x1, y1, z0=FLOOR, z1=CEIL, name='Wall'):
    return box(name, STRUCT, WALL, x0, y0, x1, y1, z0, z1)


def door(did, label, rect, hinge_end, swing, top=DOOR_H, wall_top=CEIL,
         leaf_mat=WHITE, frame_mat=WHITE, jamb=JAMB):
    """Door in an opening rect (points, spanning the wall thickness), drawn open as on the plan.

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
    for i, (j0, j1) in enumerate(((a0, a0 + jamb), (a1 - jamb, a1))):
        r = (j0, f0, j1, f1) if along_x else (f0, j0, f1, j1)
        box(f'{label} jamb {i + 1}', OPEN, frame_mat, *r, 0, top)
    head = (a0 + jamb, f0, a1 - jamb, f1) if along_x else (f0, a0 + jamb, f1, a1 - jamb)
    box(f'{label} head', OPEN, frame_mat, *head, top - 0.06, top)
    if wall_top is not None and wall_top > top:
        wall(x0, y0, x1, y1, top, wall_top, f'{label} lintel')
    # open leaf: perpendicular to the wall at the hinge, on the swing side, 45 mm thick
    t = 0.045 * S
    side = (0, t) if to_close > 0 else (-t, 0)
    ext = (hinge_f, hinge_f + swing * length)
    if along_x:
        lr = (hinge_a + side[0], min(ext), hinge_a + side[1], max(ext))
        open_dir, close_dir = (0, swing), (to_close, 0)
    else:
        lr = (min(ext), hinge_a + side[0], max(ext), hinge_a + side[1])
        open_dir, close_dir = (swing, 0), (0, to_close)
    leaf = box(f'Door {did}', OPEN, leaf_mat, *lr, 0.005, top - 0.065, 0.002)
    # handle near the free end, through the leaf
    ea = hinge_a + (side[0] + side[1]) / 2
    ef = hinge_f + swing * (length - 0.07 * S)
    hw, hd = 0.06 * S, 0.035 * S
    hr = (ea - hd, ef - hw, ea + hd, ef + hw) if along_x else (ef - hw, ea - hd, ef + hw, ea + hd)
    handle = box(f'Door {did} handle', OPEN, CHROME, *hr, 1.0, 1.03)
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


def glazing(name, axis, a0, a1, f0, f1, z0, z1, mullions=(), bottom=True, fr=0.06):
    """Frame and glass in an opening along `axis` ('x' or 'y') from a0 to a1; f0..f1 is the frame depth."""
    f = fr * S
    r = (lambda p0, p1: (p0, f0, p1, f1)) if axis == 'x' else (lambda p0, p1: (f0, p0, f1, p1))
    box(f'{name} frame 1', OPEN, DARK, *r(a0, a0 + f), z0, z1)
    box(f'{name} frame 2', OPEN, DARK, *r(a1 - f, a1), z0, z1)
    box(f'{name} frame top', OPEN, DARK, *r(a0 + f, a1 - f), z1 - fr, z1)
    zb = z0 + fr if bottom else z0
    if bottom:
        box(f'{name} frame bottom', OPEN, DARK, *r(a0 + f, a1 - f), z0, zb)
    for i, m in enumerate(mullions):
        box(f'{name} mullion {i + 1}', OPEN, DARK, *r(m - f / 2, m + f / 2), zb, z1 - fr)
    gm, g = (f0 + f1) / 2, 0.004 * S
    gr = (a0 + f, gm - g, a1 - f, gm + g) if axis == 'x' else (gm - g, a0 + f, gm + g, a1 - f)
    box(f'{name} glass', OPEN, GLASS, *gr, zb + 0.001, z1 - fr - 0.001)   # clear of frames and mullions


def chair(name, coll, cx, cy, back, mat=DARK, half=0.21):
    """Chair centred at (cx, cy) points; back = side of the backrest: 'N', 'S', 'E' or 'W'."""
    h, leg, rest = half * S, 0.02 * S, 0.035 * S
    box(f'{name} seat', coll, mat, cx - h, cy - h, cx + h, cy + h, 0.43, 0.47, 0.004)
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        lx, ly = cx + sx * (h - leg * 1.5), cy + sy * (h - leg * 1.5)
        box(f'{name} leg {i + 1}', coll, mat, lx - leg, ly - leg, lx + leg, ly + leg, 0, 0.43)
    r = {'N': (cx - h, cy - h, cx + h, cy - h + rest), 'S': (cx - h, cy + h - rest, cx + h, cy + h),
         'W': (cx - h, cy - h, cx - h + rest, cy + h), 'E': (cx + h - rest, cy - h, cx + h, cy + h)}[back]
    box(f'{name} back', coll, mat, *r, 0.47, 0.86, 0.004)


def bed(name, x0, y0, x1, y1, head):
    """Bed filling the rectangle; head = 'N', 'S', 'E' or 'W'."""
    box(f'{name} frame', FURN, ASH, x0, y0, x1, y1, 0, 0.30, 0.01)
    e, p, hb = 0.02 * S, 0.30 * S, 0.035 * S
    box(f'{name} mattress', FURN, FELT, x0 + e / 2, y0 + e / 2, x1 - e / 2, y1 - e / 2, 0.30, 0.50, 0.03)
    pr = {'N': (x0 + e, y0 + e, x1 - e, y0 + p), 'S': (x0 + e, y1 - p, x1 - e, y1 - e),
          'W': (x0 + e, y0 + e, x0 + p, y1 - e), 'E': (x1 - p, y0 + e, x1 - e, y1 - e)}[head]
    box(f'{name} pillow', FURN, COTTON, *pr, 0.50, 0.60, 0.03)
    hr = {'N': (x0, y0 - hb, x1, y0), 'S': (x0, y1, x1, y1 + hb), 'W': (x0 - hb, y0, x0, y1), 'E': (x1, y0, x1 + hb, y1)}[head]
    box(f'{name} headboard', FURN, ASH, *hr, 0, 0.95)


def desk(name, x0, y0, x1, y1):
    box(f'{name} top', FURN, OAK, x0, y0, x1, y1, 0.72, 0.75, 0.003)
    s = 0.025 * S
    if (x1 - x0) > (y1 - y0):
        box(f'{name} side 1', FURN, WHITE, x0, y0, x0 + s, y1, 0, 0.72)
        box(f'{name} side 2', FURN, WHITE, x1 - s, y0, x1, y1, 0, 0.72)
    else:
        box(f'{name} side 1', FURN, WHITE, x0, y0, x1, y0 + s, 0, 0.72)
        box(f'{name} side 2', FURN, WHITE, x0, y1 - s, x1, y1, 0, 0.72)


def wc(name, x0, y0, x1, y1, wall_side):
    """Wall-hung WC filling the drawn outline; wall_side = 'N', 'S', 'E' or 'W' (where the wall is)."""
    vertical = wall_side in 'NS'
    m = 0.10 * S                                  # flush-mount block against the wall
    if wall_side == 'N': mount, bowl = (x0, y0, x1, y0 + m), (x0, y0 + m, x1, y1)
    elif wall_side == 'S': mount, bowl = (x0, y1 - m, x1, y1), (x0, y0, x1, y1 - m)
    elif wall_side == 'W': mount, bowl = (x0, y0, x0 + m, y1), (x0 + m, y0, x1, y1)
    else: mount, bowl = (x1 - m, y0, x1, y1), (x0, y0, x1 - m, y1)
    cx, cy = (bowl[0] + bowl[2]) / 2, (bowl[1] + bowl[3]) / 2
    rx, ry = (bowl[2] - bowl[0]) / 2, (bowl[3] - bowl[1]) / 2
    box(f'{name} mount', FIT, CERAMIC, *mount, 0.28, 0.42, 0.01)
    cylinder(f'{name} bowl', FIT, CERAMIC, cx, cy, rx, ry, 0.30, 0.40)
    cylinder(f'{name} seat', FIT, WHITE, cx, cy, rx * 0.98, ry * 0.98, 0.40, 0.43)


def basin(name, x0, y0, x1, y1):
    box(name, FIT, CERAMIC, x0, y0, x1, y1, 0.70, 0.85, 0.015)
    cylinder(f'{name} bowl', FIT, ENAMEL, (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) * 0.32, (y1 - y0) * 0.30, 0.849, 0.851)


def wardrobe(name, x0, y0, x1, y1, height=2.40):
    box(name, FURN, ASH, x0, y0, x1, y1, 0, height, 0.004)


# ---------------------------------------------------------------- pack models
ASSET_CACHE = {}
DIR = {'+X': 0, '+Y': 90, '-X': 180, '-Y': -90}     # the way a model faces in its own file
FACE = {'E': 0, 'N': 90, 'W': 180, 'S': -90}        # the way it should face on the plan (N = up the sheet)


def asset(name):
    if name not in ASSET_CACHE:
        with bpy.data.libraries.load(os.path.join(ASSETS, name + '.blend'), link=False) as (src, dst):
            dst.objects = src.objects
        ob = dst.objects[0]
        vs = [v.co for v in ob.data.vertices]
        ASSET_CACHE[name] = [ob, [max(v[k] for v in vs) - min(v[k] for v in vs) for k in range(3)], 0]
    return ASSET_CACHE[name]


def place(name, cx, cy, front, face, fit=None, scale=None, z=0.0, coll=None, stand=False):
    """Put a pack model with its footprint centre on plan point (cx, cy), its front turned to `face`.

    fit: target size in metres along the model's own x, y, z (None keeps that axis);
    stand: the model lies flat in its file (the mirror) and is stood up first."""
    entry = asset(name)
    src, dims, n = entry
    ob = src if n == 0 else src.copy()
    entry[2] += 1
    ob.name = f'{name} {n + 1}'
    s = [scale or 1.0] * 3
    if fit:
        s = [fit[i] / dims[i] if fit[i] else s[i] for i in range(3)]
    ob.scale = s
    ob.rotation_euler = (math.radians(90) if stand else 0.0, 0.0, math.radians(FACE[face] - DIR[front]))
    ob.location = (X(cx), Y(cy), z)
    (coll or FURN).objects.link(ob)
    return ob


def wall_art(name, front, face, wall, along, zc, scale=1.0, stand=False):
    """Hang a picture or mirror on the wall face at plan coordinate `wall`, centred at `along` and height zc."""
    dims = asset(name)[1]
    t = 0.0 if stand else dims[0 if front in ('+X', '-X') else 1] * scale
    h = dims[2] * scale
    off = t / 2 * S
    cx, cy = {'N': (along, wall - off), 'S': (along, wall + off), 'W': (wall - off, along), 'E': (wall + off, along)}[face]
    return place(name, cx, cy, front, face, scale=scale, z=zc if stand else zc - h / 2, stand=stand)


# ================================================================ WALLS
# Reinforced concrete (grey on the sheet): 220 mm party and core walls, 250 mm facade walls
wall(190.18, 78.91, 244.89, 91.39, name='North wall')
wall(301.58, 78.91, 686.81, 91.39, name='North wall')
wall(686.81, 78.91, 699.28, 323.26, name='East party wall')
wall(190.18, 91.39, 204.35, 257.50, name='Stair core wall')
wall(102.87, 243.32, 190.18, 257.50, name='Storage north wall')
wall(102.87, 257.50, 115.34, 335.73, name='Storage west wall')
wall(115.34, 323.26, 262.18, 335.73, name='Hall / living wall')
wall(313.20, 323.26, 526.93, 335.73, name='Hall / living wall')
wall(526.93, 323.26, 579.66, 337.43, name='Facade wall 04')
wall(670.37, 323.26, 699.28, 337.43, name='Facade wall 04')
wall(579.66, 323.26, 670.37, 337.43, FLOOR, SILL, 'Window 04 sill wall')
wall(526.93, 337.43, 541.11, 373.15, name='Facade wall 02')
wall(526.93, 486.54, 541.11, 560.52, name='Facade wall 02 and column')
wall(526.93, 373.15, 541.11, 486.54, FLOOR, SILL, 'Window 02 sill wall')
wall(102.87, 335.73, 115.34, 737.12, name='West party wall')
wall(102.87, 737.12, 308.95, 749.59, name='South party wall')
wall(308.95, 737.12, 323.12, 751.29, name='South party wall')
wall(323.12, 737.12, 411.00, 751.29, name='South party wall')
wall(411.00, 737.12, 424.89, 751.29, name='Loggia pier')
wall(501.99, 737.12, 541.11, 751.29, name='Loggia pier')

# Partitions (hatched): 115 mm, with installation layers around the bathroom and WC
wall(204.35, 250.98, 241.20, 257.50, name='Hall / storage partition')
wall(234.68, 257.50, 241.20, 265.43, name='Hall / storage partition')
wall(234.68, 310.79, 241.20, 323.26, name='Hall / storage partition')
wall(115.34, 257.50, 119.60, 298.88, name='Storage lining')
wall(115.34, 298.88, 150.78, 323.26, name='Shaft D17')
wall(150.78, 317.59, 234.68, 323.26, name='Storage installation layer')
wall(308.67, 91.39, 315.19, 253.53, name='WC partition')
wall(315.19, 247.01, 319.44, 253.53, name='WC / bath front partition')
wall(364.79, 247.01, 402.49, 253.53, name='WC / bath front partition')
wall(447.85, 247.01, 493.20, 253.53, name='WC / bath front partition')
wall(369.04, 91.39, 375.56, 247.01, name='WC / bath partition')
wall(375.56, 91.39, 384.07, 247.01, name='Bath installation wall')
wall(384.07, 91.39, 488.95, 97.06, name='Bath installation layer')
wall(488.95, 91.39, 493.20, 247.01, name='Bath lining')
wall(493.20, 91.39, 499.72, 262.88, name='Bath / room 04 partition')
wall(493.20, 313.91, 499.72, 323.26, name='Hall / room 04 partition')
wall(315.19, 91.39, 369.04, 117.47, name='Shaft D18')
wall(315.19, 117.47, 369.04, 127.39, name='Shaft D18 wall')
wall(315.19, 127.39, 369.04, 137.31, FLOOR, 1.20, 'WC pre-wall')
wall(115.34, 548.33, 155.88, 554.85, name='Living / room 03 partition')
wall(206.90, 548.33, 406.18, 554.85, name='Living / room 03 partition')
wall(406.18, 548.33, 411.00, 559.07, name='Glazing corner post')
wall(406.18, 731.17, 411.00, 737.12, name='Glazing pier')

# External insulation (zig-zag on the sheet), 205 mm
wall(552.73, 337.43, 579.66, 349.06, name='Insulation 04')
wall(670.37, 337.43, 699.28, 349.06, name='Insulation 04')
wall(579.66, 337.43, 670.37, 349.06, FLOOR, SILL, 'Insulation under window 04')
wall(541.11, 337.43, 552.73, 373.15, name='Insulation 02')
wall(541.11, 486.54, 552.73, 560.52, name='Insulation 02')
wall(541.11, 373.15, 552.73, 486.54, FLOOR, SILL, 'Insulation under window 02')
wall(518.40, 560.52, 552.73, 572.10, name='Insulation column')
for r in ((411.00, 731.20, 431.00, 737.12), (424.89, 737.12, 431.00, 751.29), (411.00, 751.29, 431.00, 762.90),
          (496.00, 731.20, 552.73, 737.12), (496.00, 737.12, 501.99, 751.29), (541.11, 737.12, 552.73, 751.29),
          (496.00, 751.29, 552.73, 762.90)):
    wall(*r, name='Insulation loggia pier')

# ================================================================ DOORS AND WINDOWS
door('entrance', 'Front door', (244.89, 78.91, 301.58, 91.39), 'start', 1, leaf_mat=DARK, frame_mat=DARK)
door('d07', 'Storage door', (234.68, 265.43, 241.20, 310.79), 'end', -1)
door('d02', 'Living room door', (262.18, 323.26, 313.20, 335.73), 'end', 1)
door('d06', 'WC door', (319.44, 247.01, 364.79, 253.53), 'start', -1)
door('d05', 'Bathroom door', (402.49, 247.01, 447.85, 253.53), 'start', -1)
door('d04', 'Room 04 door', (493.20, 262.88, 499.72, 313.91), 'end', 1)
door('d03', 'Room 03 door', (155.88, 548.33, 206.90, 554.85), 'start', 1)

# Loggia glazing, 2970 (-155): floor to soffit, a door in each screen hinged as drawn
glazing('Loggia screen 02', 'x', 411.00, 465.20, 548.33, 552.30, 0, CEIL)
door('l02', 'Loggia door from the living room', (465.20, 548.33, 519.50, 552.30), 'end', -1, top=CEIL,
     wall_top=None, leaf_mat=GLASS, frame_mat=DARK)
box('Loggia screen 02 post', OPEN, DARK, 519.50, 548.33, 526.93, 552.30, 0, CEIL)
door('l03', 'Loggia door from room 03', (406.18, 559.07, 411.00, 613.50), 'start', -1, top=CEIL,
     wall_top=None, leaf_mat=GLASS, frame_mat=DARK)
glazing('Loggia screen 03', 'y', 613.50, 731.17, 406.18, 411.00, 0, CEIL, mullions=(672.34,))

# Windows 2280 (535): DO21d in room 04 (one sash), DO20d in the living room (two sashes)
glazing('Window 04', 'x', 579.66, 670.37, 328.80, 333.90, SILL, HEAD)
box('Window 04 board', OPEN, WHITE, 579.66, 322.13, 670.37, 328.80, SILL, SILL + 0.02)
glazing('Window 02', 'y', 373.15, 486.54, 532.50, 537.60, SILL, HEAD, mullions=(429.85,))
box('Window 02 board', OPEN, WHITE, 525.80, 373.15, 532.50, 486.54, SILL, SILL + 0.02)

# Loggia railings: Z005b along the open side, Z010b between the piers
box('Railing Z005b glass', OPEN, GLASS, 543.60, 574.80, 545.00, 728.40, 0.08, 1.02)
box('Railing Z005b rail', OPEN, DARK, 543.30, 574.80, 545.30, 728.40, 1.02, 1.10)
box('Railing Z010b glass', OPEN, GLASS, 431.00, 760.80, 496.00, 762.20, 0.08, 1.02)
box('Railing Z010b rail', OPEN, DARK, 431.00, 760.50, 496.00, 762.50, 1.02, 1.10)

# ================================================================ FLOORS
HALL = [(204.35, 91.39), (308.67, 91.39), (308.67, 253.53), (493.20, 253.53), (493.20, 323.26),
        (241.20, 323.26), (241.20, 250.98), (204.35, 250.98)]
STORE = [(119.60, 257.50), (234.68, 257.50), (234.68, 317.59), (150.78, 317.59), (150.78, 298.88), (119.60, 298.88)]
LOGGIA_PTS = [(411.00, 552.30), (526.93, 552.30), (526.93, 560.52), (518.40, 560.52), (518.40, 572.10),
              (552.73, 572.10), (552.73, 731.20), (496.00, 731.20), (496.00, 762.90), (431.00, 762.90),
              (431.00, 731.20), (411.00, 731.20)]


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


# number: (name, polygon, area in the table, finish on the walls)
ROOMS = {
    '01': ('Hall', HALL, 10.4, 'plaster'),
    '02': ('Living room + kitchen', rect(115.34, 335.73, 526.93, 548.33), 26.9, 'plaster'),
    '03': ('Room', rect(115.34, 554.85, 406.18, 737.12), 16.3, 'plaster'),
    '04': ('Room', rect(499.72, 91.39, 686.81, 323.26), 13.3, 'plaster'),
    '05': ('Bathroom', rect(384.07, 97.06, 488.95, 247.01), 4.7, 'tiles'),
    '06': ('WC', rect(315.19, 137.31, 369.04, 247.01), 1.7, 'tiles'),
    '07': ('Storage', STORE, 1.9, 'plaster'),
    '08': ('Loggia', LOGGIA_PTS, 8.3, None),
}
prism('Floor 01 hall', FLOORS, HALL_TILE, HALL, FLOOR, 0)
prism('Floor 07 storage', FLOORS, HALL_TILE, STORE, FLOOR, 0)
for no in ('02', '03', '04'):
    prism(f'Floor {no}', FLOORS, OAK_FLOOR, ROOMS[no][1], FLOOR, 0)
for no in ('05', '06'):
    prism(f'Floor {no}', FLOORS, BATH_TILE, ROOMS[no][1], FLOOR, 0)
prism('Floor 08 loggia', FLOORS, PAVING, LOGGIA_PTS, LOGGIA - 0.04, LOGGIA)
for mat, r in ((HALL_TILE, (244.89, 78.91, 301.58, 91.39)), (HALL_TILE, (234.68, 265.43, 241.20, 310.79)),
               (OAK_FLOOR, (262.18, 323.26, 313.20, 335.73)), (BATH_TILE, (319.44, 247.01, 364.79, 253.53)),
               (BATH_TILE, (402.49, 247.01, 447.85, 253.53)), (OAK_FLOOR, (493.20, 262.88, 499.72, 313.91)),
               (OAK_FLOOR, (155.88, 548.33, 206.90, 554.85)), (OAK_FLOOR, (411.00, 548.33, 526.93, 552.30)),
               (OAK_FLOOR, (406.18, 559.07, 411.00, 731.17))):
    box('Floor in opening', FLOORS, mat, *r, FLOOR, 0)

# ================================================================ KITCHEN (L along the west and north walls of 02)
UNIT = [(119.03, 339.42, 187.06, 373.43), (119.03, 373.43, 153.05, 543.51)]
for i, r in enumerate(UNIT):
    box(f'Kitchen base {i + 1}', FIT, WHITE, *r, 0.10, WT - 0.04, 0.003)
    box(f'Worktop {i + 1}', FIT, ASH, *r, WT - 0.04, WT, 0.002)
box('Kitchen plinth 1', FIT, DARK, 120.80, 341.20, 185.30, 371.70, 0, 0.10)
box('Kitchen plinth 2', FIT, DARK, 120.80, 371.70, 151.30, 541.70, 0, 0.10)
box('Fridge column', FIT, WHITE, 187.06, 339.42, 221.08, 373.43, 0, 2.10, 0.004)
box('Sink', FIT, STEEL, 124.08, 378.32, 148.00, 402.56, WT, WT + 0.004)
box('Sink bowl', FIT, DARK, 126.90, 381.20, 145.20, 399.70, WT + 0.004, WT + 0.005)
place('faucet', 129.06, 388.76, '+Y', 'E', z=WT, coll=FIT)          # base behind the sink, spout over it
box('Hob', FIT, BLACK_GLASS, 120.70, 443.10, 151.40, 473.80, WT, WT + 0.006)
for i, (cx, cy, rr) in enumerate(((129.2, 450.8, 5.3), (143.0, 450.8, 5.3), (129.2, 466.2, 4.7), (143.0, 466.2, 4.7))):
    cylinder(f'Hob ring {i + 1}', FIT, DARK, cx, cy, rr, rr, WT + 0.006, WT + 0.007)

# ================================================================ BATHROOM 05, WC 06, STORAGE 07
box('Bathtub', FIT, CERAMIC, 385.50, 97.10, 487.50, 142.40, 0, 0.55, 0.02)
box('Bathtub inside', FIT, ENAMEL, 391.20, 102.80, 481.80, 136.70, 0.549, 0.551)
wc('WC 05', 385.50, 157.50, 417.20, 178.30, 'W')
basin('Basin 05 left', 460.30, 151.10, 487.50, 185.10)
basin('Basin 05 right', 460.30, 190.80, 487.50, 224.80)
box('Towel radiator', FIT, WHITE, 388.30, 208.30, 390.00, 237.50, 0.20, 1.40)
wc('WC 06', 333.40, 137.31, 350.80, 167.60, 'N')
basin('Hand basin 06', 353.50, 188.90, 367.60, 209.30)
box('Washing machine', FIT, WHITE, 123.30, 261.20, 157.30, 297.40, 0, 0.85, 0.01)
wall_art('mirror', '-Y', 'W', 488.95, 187.95, 1.45, stand=True)   # over the double basin

# ================================================================ FURNITURE (all positions as drawn; pack models fitted to the drawn outlines)
wardrobe('Hall wardrobe', 208.04, 95.07, 242.05, 247.29)
wardrobe('Wardrobe 04', 503.41, 95.07, 537.42, 242.47)
wardrobe('Wardrobe 03', 119.03, 558.54, 153.05, 733.43)
bed('Bed 04', 632.10, 95.07, 683.12, 208.46, 'N')
bed('Bed 03', 204.07, 620.05, 306.12, 733.43, 'S')

# Room 04: desk on the east wall, office chair facing it, a lamp on the desk, a print above it
place('desk', 666.10, 253.85, '+X', 'W', fit=(0.600, 1.000, None))
place('desk_chair', 641.00, 253.80, '+X', 'E')
place('table_lamp', 674.00, 234.00, '+X', 'W', z=0.701)
wall_art('picture_wide2', '-Y', 'W', 686.81, 253.85, 1.50)

# Room 03: nightstands with lamps either side of the bed, painting over it, desk on the south wall
for cx in (194.15, 316.04):
    place('nightstand', cx, 723.51, '+Y', 'N', fit=(0.350, 0.350, 0.50))
    place('table_lamp', cx, 723.51, '+X', 'N', z=0.50)
wall_art('painting', '+X', 'N', 737.12, 255.10, 1.55)
place('desk', 369.33, 710.76, '+X', 'N', fit=(0.800, 1.200, None))
place('desk_chair', 369.30, 684.00, '+X', 'S')

# Living room: sideboard and TV on the north wall, sofa facing it over a rug, coffee table between
for cx in (369.12, 471.87):
    place('media_unit', cx, 350.76, '-Y', 'S', fit=(1.8125, 0.400, None))
box('TV stand', FURN, DARK, 410.00, 346.50, 429.00, 356.00, 0.559, 0.589)
place('tv', 419.55, 351.30, '+X', 'S', scale=1.20 / 1.44, z=0.589)
place('rug', 419.60, 420.00, '+Y', 'W', fit=(1.70, 2.60, None), z=0.002)
place('sofa', 419.63, 462.88, '-Y', 'N', fit=(2.751, 0.900, None))
place('coffee_table', 419.55, 399.10, '+Y', 'N', fit=(1.400, 0.650, None))
place('floor_lamp', 327.00, 470.00, '+Y', 'N')
place('plant', 512.00, 386.00, '+Y', 'S')
wall_art('picture_wide', '-Y', 'N', 548.33, 419.60, 1.45)
place('dining_table', 243.76, 467.00, '+Y', 'N', fit=(0.800, 1.200, None))
for cx, cy, face in ((215.82, 449.99, 'E'), (215.82, 484.00, 'E'), (271.69, 449.99, 'W'), (271.69, 484.00, 'W')):
    place('dining_chair', cx, cy, '+Y', face)
place('pendant', 243.76, 467.00, '+Y', 'N', scale=0.65, z=CEIL - 0.615 * 0.65)

# Hall: a print on the wall opposite the wardrobe
wall_art('picture_tall', '-Y', 'W', 308.67, 175.00, 1.50)

# ================================================================ CEILINGS (shown only while walking)
SLAB = [(102.87, 243.32), (190.18, 243.32), (190.18, 78.91), (699.28, 78.91), (699.28, 349.06),
        (552.73, 349.06), (552.73, 762.90), (411.00, 762.90), (411.00, 751.29), (102.87, 751.29)]
prism('Ceiling slab', ROOF, CEILING, SLAB, CEIL, CEIL + 0.25)
for name, pts in (('hall', HALL), ('WC', ROOMS['06'][1]), ('bathroom', ROOMS['05'][1]), ('storage', STORE),
                  ('kitchen', rect(115.34, 335.73, 221.08, 548.33))):
    prism(f'Suspended ceiling {name}', ROOF, CEILING, inset(pts, 0.03), SUSP, SUSP + 0.015)
# the kitchen's lowered ceiling is open towards the living room: close its edge up to the soffit
box('Suspended ceiling kitchen edge', ROOF, CEILING, 220.37, 335.76, 221.05, 548.30, SUSP + 0.015, CEIL)

# ---------------------------------------------------------------- areas against the table
def shoelace(p):
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2


def perimeter(p):
    return sum(math.dist(p[i], p[(i + 1) % len(p)]) for i in range(len(p)))


FINISH = {'plaster': 0.014, 'tiles': 0.020, None: 0.0}   # finish on each wall face, metres
areas = {}
for no, (name, pts, table, fin) in ROOMS.items():
    raw = shoelace(pts) * K * K
    t = FINISH[fin]
    net = raw - perimeter(pts) * K * t + 4 * t * t       # rectilinear polygon shrunk by t
    areas[no] = {'name': name, 'table': table, 'raw': round(raw, 3), 'net': round(net, 3),
                 'finish_mm': t * 1000, 'ok': abs(net - table) < 0.05 + 1e-9}
    print(f'AREA {no} {name:24s} raw {raw:6.2f}  net {net:6.2f}  table {table:5.1f}  {"OK" if areas[no]["ok"] else "OFF"}')
usable = sum(a['net'] for n, a in areas.items() if n != '08')
print(f'AREA usable (01-07) net {usable:.2f}  table 75.2')
with open(os.path.join(HERE, 'areas.json'), 'w', encoding='utf-8') as f:
    json.dump(areas, f, indent=1)

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

CROP = (90, 66, 712, 776)        # plan-d601.png is this crop of the sheet at 3 px per point
PX = 3


def camera(name, loc, target=None, lens=35, ortho=None):
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


cam_top = camera('Cam plan (top)', (X((CROP[0] + CROP[2]) / 2), Y((CROP[1] + CROP[3]) / 2), 30),
                 ortho=max(CROP[2] - CROP[0], CROP[3] - CROP[1]) * K)
cam_view = camera('Cam 3D', (-7.5, -11.0, 12.5), (0.2, 0.0, 0.8), lens=32)
scene.camera = cam_view
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.eevee.taa_render_samples = 32
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'
                    space.clip_end = 200

# world-space UVs for the textured modelled pieces (wardrobes, beds, worktop), so the wood and cotton keep their real size
for ob in scene.objects:
    if ob.type == 'MESH' and any(sl.material in (ASH, COTTON, FELT) for sl in ob.material_slots):
        me = ob.data
        uv = (me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')).data
        for p in me.polygons:
            ax = max(range(3), key=lambda k: abs(p.normal[k]))
            a, b = ((1, 2), (0, 2), (0, 1))[ax]
            for li in p.loop_indices:
                co = ob.matrix_world @ me.vertices[me.loops[li].vertex_index].co
                uv[li].uv = (co[a], co[b])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'd601-real.blend'))
print('SAVED')

if '--render' in ARGS:
    out = os.path.join(HERE, 'renders')
    os.makedirs(out, exist_ok=True)
    shots = [('top.png', cam_top, ((CROP[2] - CROP[0]) * PX, (CROP[3] - CROP[1]) * PX)),
             ('view-3d.png', cam_view, (1600, 1200))]
    for fname, cam, (rx, ry) in shots:
        scene.camera = cam
        scene.render.resolution_x, scene.render.resolution_y = int(rx), int(ry)
        scene.render.resolution_percentage = 100
        scene.render.filepath = os.path.join(out, fname)
        bpy.ops.render.render(write_still=True)
        print('RENDERED', fname)
