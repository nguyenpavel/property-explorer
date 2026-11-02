"""Flat E 433 (Čtvrť pod Hády, building E.3, 2nd floor, 2+kk) rebuilt from the developer's plan sheet.

Run:  blender -b --factory-startup -P build_e433.py -- [--render]

The sheet is an ArchiCAD vector PDF at M 1:75 on A4, so positions are PDF points read
straight off the wall paths (src/plan_vectors.json): 1 m = 72 / 25.4 * 1000 / 75 pt.
Heights are not on the plan and are assumptions (constants below). Doors carry their
hinge and closing angle as custom properties, so the web viewer can swing them.
"""
import bpy, bmesh, math, os, sys
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []

S = 72 / 25.4 * 1000 / 75   # 37.795 pt per metre
CX, CY = 448.2, 217.2        # sheet point at the world origin (middle of the flat)
FLOOR = -0.02                # top of the structural slab; finishes fill FLOOR..0
CEIL = 2.70                  # clear height (assumed)
DOOR_H = 2.10                # interior and entrance door openings
SILL, HEAD = 0.85, 2.40      # windows; the balcony door also tops out at HEAD


def X(px): return (px - CX) / S
def Y(py): return (CY - py) / S
def M(m): return m * S       # metres -> points, for offsets


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
STRUCT = collection('Structure')
FLOORS = collection('Floors')
OPEN = collection('Doors & Windows')
FIT = collection('Fitout')
FURN = collection('Furniture')
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
OAK_FLOOR = tiled('Oak planks', (0.45, 0.30, 0.17), (0.50, 0.34, 0.20), (0.25, 0.16, 0.09), 1.2, 0.19)
HALL_TILE = tiled('Hall tiles', (0.70, 0.67, 0.62), (0.66, 0.63, 0.58), (0.45, 0.43, 0.40), 0.6, 0.6, offset=0.0, rough=0.3)
BATH_TILE = tiled('Bath floor tiles', (0.45, 0.45, 0.46), (0.42, 0.42, 0.43), (0.30, 0.30, 0.31), 0.3, 0.3, offset=0.0, rough=0.3)
DECK = tiled('Decking', (0.28, 0.17, 0.09), (0.31, 0.19, 0.10), (0.10, 0.06, 0.03), 2.4, 0.14, rough=0.7)
SHAFT = material('Shaft', (0.62, 0.80, 0.90), 0.8)
WHITE = material('White lacquer', (0.88, 0.88, 0.88), 0.35)
CERAMIC = material('Ceramic', (0.95, 0.95, 0.95), 0.1)
OAK = material('Oak', (0.42, 0.28, 0.16), 0.5)
DARK = material('Anthracite', (0.06, 0.06, 0.07), 0.4)
BLACK_GLASS = material('Black glass', (0.01, 0.01, 0.01), 0.05)
STEEL = material('Steel', (0.75, 0.75, 0.77), 0.25, metal=1.0)
CHROME = material('Chrome', (0.90, 0.90, 0.90), 0.05, metal=1.0)
GLASS = material('Glass', (0.75, 0.85, 0.90), 0.0, alpha=0.18)
MIRROR = material('Mirror', (0.85, 0.88, 0.90), 0.02, metal=1.0)
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
    """Axis-aligned box: sheet rectangle x0..x1, y0..y1 (points), heights z0..z1 in metres."""
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
    """Vertical elliptic cylinder; centre and radii in points."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=1.0, radius2=1.0, depth=1.0,
                          matrix=Matrix.Diagonal((rx / S, ry / S, z1 - z0, 1)))
    for f in bm.faces:
        f.smooth = len(f.verts) == 4
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return link(name, me, (X(cx), Y(cy), (z0 + z1) / 2), coll, mat)


def wall(x0, y0, x1, y1, z0=FLOOR, z1=CEIL, name='Wall'):
    return box(name, STRUCT, WALL, x0, y0, x1, y1, z0, z1)


def door(did, label, rect, hinge_end, swing, top=DOOR_H, leaf_mat=WHITE, frame_mat=WHITE,
         jamb=0.07, leaf=0.045, lintel=True):
    """Door in an opening rect (points, spanning the wall thickness), drawn open as on the plan.

    hinge_end: 'start' or 'end' of the opening along its length; swing: +1/-1, the side
    the leaf opens to (perpendicular to the wall). The leaf stores its hinge and the
    rotation that closes it, in three.js terms (y up, sheet y = +z).
    """
    x0, y0, x1, y1 = rect
    jamb, leaf = M(jamb), M(leaf)
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
        box(f'{label} jamb {i + 1}', OPEN, frame_mat, *r, 0, top)    # on the finishes, not through them
    head = (a0 + jamb, f0, a1 - jamb, f1) if along_x else (f0, a0 + jamb, f1, a1 - jamb)
    box(f'{label} head', OPEN, frame_mat, *head, top - 0.06, top)
    if lintel:
        wall(x0, y0, x1, y1, top, CEIL, f'{label} lintel')
    # open leaf: perpendicular to the wall at the hinge, on the swing side
    side = (0, leaf) if to_close > 0 else (-leaf, 0)
    ext = (hinge_f, hinge_f + swing * length)
    if along_x:
        lr = (hinge_a + side[0], min(ext), hinge_a + side[1], max(ext))
        open_dir, close_dir = (0, swing), (to_close, 0)
    else:
        lr = (min(ext), hinge_a + side[0], max(ext), hinge_a + side[1])
        open_dir, close_dir = (swing, 0), (0, to_close)
    ob = box(f'Door {did}', OPEN, leaf_mat, *lr, 0.005, top - 0.065, 0.003)
    # lever handle near the free end, through the leaf
    ea = hinge_a + (side[0] + side[1]) / 2
    ef = hinge_f + swing * (length - M(0.10))
    hw, hd = M(0.09), M(0.055)
    hr = (ea - hd, ef - hw, ea + hd, ef + hw) if along_x else (ef - hw, ea - hd, ef + hw, ea + hd)
    handle = box(f'Door {did} handle', OPEN, CHROME, *hr, 1.0, 1.03)
    ox, oz = open_dir
    cx, cz = close_dir
    ob['door_id'] = did
    ob['door_label'] = label
    ob['hinge_x'] = X(hinge_a if along_x else hinge_f)
    ob['hinge_z'] = -Y(hinge_f if along_x else hinge_a)
    ob['close_angle'] = -math.atan2(ox * cz - oz * cx, ox * cx + oz * cz)
    ob['level'] = 0
    handle['door_part'] = did
    return ob


def window(name, rect, z0, z1, mullions=(), bottom=True):
    """Frame and glass; rect spans the opening along the wall and the frame depth across it."""
    x0, y0, x1, y1 = rect
    along_x = (x1 - x0) > (y1 - y0)
    f, mh = M(0.07), M(0.035)

    def part(suffix, mat, a0, a1, za, zb, inset=0.0):
        if along_x:
            box(f'{name} {suffix}', OPEN, mat, a0, y0 + inset, a1, y1 - inset, za, zb)
        else:
            box(f'{name} {suffix}', OPEN, mat, x0 + inset, a0, x1 - inset, a1, za, zb)

    a0, a1 = (x0, x1) if along_x else (y0, y1)
    part('frame 1', DARK, a0, a0 + f, z0, z1)
    part('frame 2', DARK, a1 - f, a1, z0, z1)
    part('frame top', DARK, a0 + f, a1 - f, z1 - 0.07, z1)
    if bottom:
        part('frame bottom', DARK, a0 + f, a1 - f, z0, z0 + 0.07)
    for i, m in enumerate(mullions):
        part(f'mullion {i + 1}', DARK, m - mh, m + mh, z0 + (0.07 if bottom else 0), z1 - 0.07)
    depth = (y1 - y0) if along_x else (x1 - x0)
    part('glass', GLASS, a0 + f, a1 - f, z0 + (0.07 if bottom else 0), z1 - 0.07, inset=depth / 2 - M(0.006))


def chair(name, cx, cy, back):
    """Round-seat dining chair at (cx, cy); back = side of the backrest: 'N' or 'S' (sheet up/down)."""
    r = M(0.21)
    cylinder(f'{name} seat', FURN, DARK, cx, cy, r, r, 0.43, 0.47)
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        lx, ly = cx + sx * r * 0.62, cy + sy * r * 0.62
        box(f'{name} leg {i + 1}', FURN, DARK, lx - M(0.012), ly - M(0.012), lx + M(0.012), ly + M(0.012), 0, 0.43)
    by = cy - r if back == 'N' else cy + r - M(0.03)
    box(f'{name} back', FURN, DARK, cx - r * 0.8, by, cx + r * 0.8, by + M(0.03), 0.47, 0.84, 0.004)


def table(name, x0, y0, x1, y1, z, legs_in=M(0.04)):
    box(f'{name} top', FURN, OAK, x0, y0, x1, y1, z - 0.03, z, 0.003)
    for i, (lx, ly) in enumerate(((x0 + legs_in, y0 + legs_in), (x1 - legs_in, y0 + legs_in),
                                  (x0 + legs_in, y1 - legs_in), (x1 - legs_in, y1 - legs_in))):
        box(f'{name} leg {i + 1}', FURN, DARK, lx - M(0.02), ly - M(0.02), lx + M(0.02), ly + M(0.02), 0, z - 0.03)


def radiator(name, coll, x0, y0, x1, y1, z0, z1):
    box(name, coll, WHITE, x0, y0, x1, y1, z0, z1, 0.004)


# ================================================================ STRUCTURE
# Floor slab under the flat, balcony slab and decking
box('Floor slab', SITE, CONCRETE, 300.96, 70.49, 595.47, 363.95, -0.30, FLOOR)
box('Balcony slab', SITE, CONCRETE, 263.5, 98.55, 300.96, 203.34, -0.30, -0.08)
box('Balcony decking', SITE, DECK, 263.5, 105.3, 300.96, 196.68, -0.08, -0.05)

# West facade (16.4 cm: insulation outside 300.96..308.38, structure inside to 317.41)
wall(300.96, 70.49, 317.41, 104.16, name='West wall')
wall(300.96, 197.73, 317.41, 258.59, name='West wall')
wall(300.96, 324.11, 317.41, 347.5, name='West wall')
wall(300.96, 104.16, 317.41, 197.73, HEAD, CEIL, 'Balcony door lintel')
wall(300.96, 258.59, 317.41, 324.11, FLOOR, SILL, 'Living window sill wall')
wall(300.96, 258.59, 317.41, 324.11, HEAD, CEIL, 'Living window lintel')
# Balcony side walls (the heavy fins either side of the balcony)
wall(263.5, 98.55, 300.96, 105.3, -0.08, CEIL, 'Balcony side wall')
wall(263.5, 196.68, 300.96, 203.34, -0.08, CEIL, 'Balcony side wall')
# South facade with the bedroom window
wall(300.96, 347.5, 480.41, 363.95, name='South wall')
wall(545.93, 347.5, 595.47, 363.95, name='South wall')
wall(480.41, 347.5, 545.93, 363.95, FLOOR, SILL, 'Bedroom window sill wall')
wall(480.41, 347.5, 545.93, 363.95, HEAD, CEIL, 'Bedroom window lintel')
# North party wall and east corridor wall with the entrance
wall(317.41, 70.49, 586.53, 79.53, name='North wall')
wall(586.53, 70.49, 595.47, 81.33, name='East wall')
wall(586.53, 122.51, 595.47, 347.5, name='East wall')

# Partitions (12.3 cm)
wall(440.94, 79.53, 445.6, 128.12, name='Living / hall wall')
wall(440.94, 161.88, 445.6, 347.5, name='Living / bedroom wall')
wall(445.6, 196.49, 449.31, 201.15, name='Hall / bedroom wall')
wall(483.07, 196.49, 486.77, 201.15, name='Hall / bedroom wall')
wall(486.77, 136.2, 491.43, 230.15, name='Bathroom west wall')
wall(491.43, 136.2, 522.91, 140.86, name='Bathroom north wall')
wall(552.87, 136.2, 586.53, 140.86, name='Bathroom north wall')
wall(491.43, 225.5, 586.53, 230.15, name='Bathroom / bedroom wall')
wall(491.43, 221.69, 521.39, 225.5, name='Shower wall lining')
# Service shafts: the hall one against the party wall, the bathroom one in the corner
wall(468.04, 79.53, 472.7, 95.03, name='Shaft wall')
wall(510.74, 79.53, 515.4, 95.03, name='Shaft wall')
wall(472.7, 90.37, 510.74, 95.03, name='Shaft wall')
wall(560.85, 196.49, 586.53, 201.15, name='Shaft wall')
wall(560.85, 201.15, 565.51, 225.5, name='Shaft wall')
box('Hall shaft', FIT, SHAFT, 472.7, 79.53, 510.74, 90.37, FLOOR, 0.01)
box('Bathroom shaft', FIT, SHAFT, 565.51, 201.15, 586.53, 225.5, FLOOR, 0.01)
box('Hall shaft access panel', FIT, WHITE, 476.89, 95.03, 500.76, 95.6, 0.30, 1.90)

# ================================================================ DOORS AND WINDOWS
door('entrance', 'Entrance door', (586.53, 81.33, 595.47, 122.51), 'start', -1,
     leaf_mat=DARK, frame_mat=DARK, jamb=0.05, leaf=0.06)
door('living', 'Living room door', (440.94, 128.12, 445.6, 161.88), 'end', -1, jamb=0.05)
door('bedroom', 'Bedroom door', (449.31, 196.49, 483.07, 201.15), 'start', 1, jamb=0.05)
door('bathroom', 'Bathroom door', (522.91, 136.2, 552.87, 140.86), 'end', 1, jamb=0.05)
# Balcony: glazed door (hinged on the north side, opens into the room) beside a fixed pane
door('balcony', 'Balcony door', (308.38, 104.16, 311.04, 137.86), 'start', 1, top=HEAD,
     leaf_mat=GLASS, frame_mat=DARK, jamb=0.07, leaf=0.06, lintel=False)
window('Balcony glazing', (308.38, 137.86, 311.04, 197.73), 0.0, HEAD)
window('Living window', (308.38, 258.59, 311.04, 324.11), SILL, HEAD, mullions=(277.7,))
window('Bedroom window', (480.41, 353.87, 545.93, 356.44), SILL, HEAD, mullions=(527.4,))
# Boards sit on the sill walls; sharing their top face would z-fight
box('Living window board', OPEN, WHITE, 311.04, 257.6, 318.6, 325.1, SILL, SILL + 0.025)
box('Bedroom window board', OPEN, WHITE, 479.4, 346.3, 546.9, 353.87, SILL, SILL + 0.025)
# Balcony railing: glass panel with a top rail on the outer edge
box('Balcony railing glass', OPEN, GLASS, 263.5, 105.3, 264.64, 196.68, -0.05, 1.0)
box('Balcony railing rail', OPEN, DARK, 263.2, 105.3, 264.94, 196.68, 1.0, 1.04)

# ================================================================ FLOORS
for r in ((317.41, 79.53, 440.94, 347.5), (311.04, 104.16, 317.41, 197.73), (440.94, 128.12, 445.6, 161.88)):
    box('Living floor', FLOORS, OAK_FLOOR, *r, FLOOR, 0)
for r in ((445.6, 230.15, 586.53, 347.5), (445.6, 201.15, 486.77, 230.15), (449.31, 196.49, 483.07, 201.15)):
    box('Bedroom floor', FLOORS, OAK_FLOOR, *r, FLOOR, 0)
for r in ((445.6, 95.03, 586.53, 136.2), (445.6, 79.53, 468.04, 95.03), (515.4, 79.53, 586.53, 95.03),
          (445.6, 136.2, 486.77, 196.49), (586.53, 81.33, 595.47, 122.51)):
    box('Hall tiles', FLOORS, HALL_TILE, *r, FLOOR, 0)
for r in ((491.43, 140.86, 586.53, 196.49), (491.43, 196.49, 560.85, 221.69), (521.39, 221.69, 560.85, 225.5),
          (522.91, 136.2, 552.87, 140.86)):
    box('Bathroom tiles', FLOORS, BATH_TILE, *r, FLOOR, 0)

# ================================================================ FITOUT: kitchen, bathroom, radiators
WT = 0.90
KX0, KX1, KY0, KY1 = 317.41, 440.94, 79.53, 103.78
box('Kitchen base units', FIT, WHITE, KX0, KY0, KX1, KY1 - M(0.02), 0.10, WT - 0.04, 0.003)
box('Kitchen plinth', FIT, DARK, KX0, KY0, KX1, KY1 - M(0.07), 0, 0.10)
box('Worktop', FIT, OAK, KX0, KY0, KX1, KY1, WT - 0.04, WT, 0.002)
box('Hob', FIT, BLACK_GLASS, 334.91, 80.95, 357.35, 103.39, WT, WT + 0.006)
for i, (cx, cy, r) in enumerate(((340.3, 87.0, 3.6), (351.4, 86.3, 4.6), (340.6, 96.8, 4.6), (351.6, 97.4, 3.6))):
    cylinder(f'Hob ring {i + 1}', FIT, DARK, cx, cy, r, r, WT + 0.006, WT + 0.007)
box('Sink', FIT, STEEL, 406.04, 80.38, 426.58, 101.02, WT, WT + 0.004)
box('Sink bowl', FIT, DARK, 407.85, 84.19, 424.68, 99.12, WT + 0.004, WT + 0.005)
cylinder('Kitchen tap', FIT, CHROME, 416.3, 82.2, 1.0, 1.0, WT, WT + 0.30)
for i, (x0, x1) in enumerate(((KX0, 331.0), (361.3, KX1))):
    box(f'Wall cabinets {i + 1}', FIT, WHITE, x0, KY0, x1, KY0 + M(0.35), 1.50, 2.25, 0.003)
box('Cooker hood', FIT, STEEL, 331.0, KY0, 361.3, KY0 + M(0.45), 1.62, 1.72, 0.004)

# Bathroom: corner shower, basin counter, wall-hung WC on a pre-wall, washer, towel radiator
box('Shower tray', FIT, CERAMIC, 491.43, 191.74, 521.39, 221.69, 0, 0.04, 0.004)
box('Shower drain', FIT, STEEL, 494.48, 219.5, 518.35, 220.6, 0.04, 0.042)
box('Shower glass', FIT, GLASS, 491.43, 191.0, 515.0, 191.74, 0.04, 2.0)
cylinder('Shower head', FIT, CHROME, 506.4, 219.0, 3.0, 3.0, 2.05, 2.08)
box('Shower riser', FIT, CHROME, 505.9, 220.0, 506.9, 221.69, 0.9, 2.06)
box('Basin pre-wall', FIT, WALL, 521.39, 221.69, 560.85, 225.5, 0, 1.20)
box('Basin counter', FIT, WHITE, 530.9, 203.72, 553.44, 221.69, 0.55, 0.85, 0.004)
box('Basin', FIT, CERAMIC, 532.04, 204.86, 552.29, 216.75, 0.85, 0.87, 0.01)
cylinder('Basin bowl', FIT, STEEL, 542.2, 211.0, 6.0, 4.2, 0.869, 0.871)
cylinder('Basin tap', FIT, CHROME, 542.2, 219.0, 0.9, 0.9, 0.87, 1.05)
box('Mirror', FIT, MIRROR, 531.5, 224.8, 552.8, 225.5, 1.25, 1.95)
box('WC pre-wall', FIT, WALL, 580.92, 140.86, 586.53, 196.49, 0, 1.20)
cylinder('WC bowl', FIT, CERAMIC, 569.0, 179.6, 8.2, 6.4, 0.30, 0.40)
cylinder('WC seat', FIT, CERAMIC, 569.0, 179.6, 8.8, 7.0, 0.40, 0.43)
box('WC mount', FIT, CERAMIC, 575.0, 173.5, 580.92, 185.7, 0.28, 0.42, 0.01)
box('Flush plate', FIT, CHROME, 580.4, 175.5, 580.92, 183.7, 1.00, 1.15)
box('Washing machine', FIT, WHITE, 556.2, 144.1, 578.64, 166.54, 0, 0.85, 0.01)
cylinder('Washing machine door', FIT, BLACK_GLASS, 567.4, 166.6, 7.0, 0.4, 0.22, 0.62, seg=24)
radiator('Towel radiator', FIT, 491.43, 153.79, 493.6, 172.53, 0.40, 1.60)
radiator('Living radiator', FIT, 319.22, 265.53, 323.03, 317.93, 0.15, 0.75)
radiator('Bedroom radiator', FIT, 483.16, 341.89, 543.07, 345.6, 0.15, 0.75)

# ================================================================ FURNITURE
table('Dining table', 317.41, 189.36, 369.81, 215.51, 0.75)
for i, (cx, cy, back) in enumerate(((330.6, 176.1, 'N'), (356.8, 176.1, 'N'), (330.6, 228.5, 'S'), (356.8, 228.5, 'S'))):
    chair(f'Dining chair {i + 1}', cx, cy, back)
# Three-seat sofa against the partition, facing the window
box('Sofa base', FURN, FABRIC, 407.18, 242.71, 440.94, 332.48, 0.02, 0.25, 0.01)
box('Sofa back', FURN, FABRIC, 433.43, 242.71, 440.94, 332.48, 0.25, 0.80, 0.02)
box('Sofa arm 1', FURN, FABRIC, 407.18, 242.71, 433.43, 248.7, 0.25, 0.60, 0.02)
box('Sofa arm 2', FURN, FABRIC, 407.18, 326.48, 433.43, 332.48, 0.25, 0.60, 0.02)
for i, (y0, y1) in enumerate(((248.7, 276.37), (276.37, 298.81), (298.81, 326.48))):
    box(f'Sofa cushion {i + 1}', FURN, FABRIC, 407.6, y0 + 0.3, 433.4, y1 - 0.3, 0.25, 0.44, 0.03)
box('Pillow 1', FURN, CUSHION, 428.0, 251.0, 433.0, 266.0, 0.44, 0.72, 0.03)
box('Pillow 2', FURN, CUSHION, 428.0, 309.0, 433.0, 324.0, 0.44, 0.72, 0.03)
table('Coffee table', 371.71, 266.96, 394.16, 308.13, 0.42, legs_in=M(0.03))

# Bedroom: double bed with its head on the east wall, bedside tables, wardrobe by the door
box('Bed frame', FURN, OAK, 507.89, 259.54, 584.63, 319.45, 0, 0.30, 0.01)
box('Mattress', FURN, BEDDING, 508.6, 260.3, 583.9, 318.7, 0.30, 0.50, 0.03)
box('Pillow 3', FURN, BEDDING, 573.0, 262.0, 582.5, 288.0, 0.50, 0.62, 0.03)
box('Pillow 4', FURN, BEDDING, 573.0, 291.0, 582.5, 317.0, 0.50, 0.62, 0.03)
box('Duvet', FURN, CUSHION, 508.0, 259.9, 545.0, 319.1, 0.50, 0.53, 0.03)
box('Headboard', FURN, OAK, 584.63, 259.54, 586.53, 319.45, 0, 1.05)
for i, (y0, y1) in enumerate(((237.1, 259.54), (319.45, 341.89))):
    box(f'Bedside table {i + 1}', FURN, OAK, 569.7, y0, 586.53, y1, 0, 0.50, 0.004)
for i, (y0, y1) in enumerate(((254.88, 285.69), (285.69, 316.6), (316.6, 347.5))):
    box(f'Wardrobe {i + 1}', FURN, WARDROBE, 445.6, y0 + 0.15, 468.04, y1 - 0.15, 0, 2.40, 0.004)

# ================================================================ CEILING (shown only when walking inside)
box('Ceiling slab', CEILING, CONCRETE, 300.96, 70.49, 595.47, 363.95, CEIL, CEIL + 0.25)
box('Balcony above', CEILING, CONCRETE, 263.5, 98.55, 300.96, 203.34, CEIL, CEIL + 0.25)

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
sun_ob.rotation_euler = (math.radians(30), math.radians(-12), math.radians(-35))
RIG.objects.link(sun_ob)

CROP = (252, 58, 619, 376)      # sheet area of plan-sheet.png


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


cam_top = camera('Cam plan (top)', (X((CROP[0] + CROP[2]) / 2), Y((CROP[1] + CROP[3]) / 2), 30),
                 ortho=(CROP[2] - CROP[0]) / S)
cam_view = camera('Cam 3D', (-6.5, -8.5, 9.5), (0.0, 0.3, 0.5), lens=32)
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

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'e433.blend'))
print('SAVED')

if '--render' in ARGS:
    out = os.path.join(HERE, 'renders')
    os.makedirs(out, exist_ok=True)
    w, h = CROP[2] - CROP[0], CROP[3] - CROP[1]
    for fname, cam, (rx, ry) in (('top.png', cam_top, (1100, round(1100 * h / w))), ('view-3d.png', cam_view, (1400, 1050))):
        scene.camera = cam
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
        scene.render.resolution_percentage = 100
        scene.render.filepath = os.path.join(out, fname)
        bpy.ops.render.render(write_still=True)
        print('RENDERED', fname)
