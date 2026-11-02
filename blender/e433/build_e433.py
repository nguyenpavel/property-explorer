"""Building E3, 2.NP: flat E.3/2P.3 (2+kk with loggia) rebuilt as a 3D scene.

Run:  blender -b --factory-startup -P build_e433.py -- [--render]

Source: E433.pdf, the 2.NP ASŘ plan (sheet D.1.02.1_403, E3), a 1:50 drawing printed to
US Letter through "Microsoft Print to PDF". It has no text layer, but the linework is
vector, so positions here are PDF points read from it. The shrink-to-fit leaves
1 pt = 21.65 mm: the 3 300 mm living room is 152.52 pt, its 7 160 mm length 330.72 pt,
the 3 765 mm bedroom 173.88 pt, and the 1 000 / 800 / 700 mm door leaves 46.2 / 36.96 /
32.28 pt.

From the sheet: walls (240 mm masonry + 200 mm ETICS on the facades, 125 mm partitions,
240 mm party walls), doors and their swings, 2 100 mm door heights, both windows with
their mullions, the loggia between concrete fins, the two installation shafts, the
+2.300 plasterboard ceilings in the hall and bathroom ("s.v. +2,300"), the 1.20 m
installation walls ("v.s. 1200"), and the drawn kitchen, bathroom and furniture.
Assumed: the 2.70 m ceiling elsewhere, windows from 0.45 to 2.40 m (both carry a Z/11
railing, so the sill is below 0.85 m), and the heights of everything movable.
"""
import bpy, bmesh, math, os, sys
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []

K = 0.02165                  # metres per PDF point
CX, CY = 381.12, 299.16      # centre of the flat's rooms -> world origin
H = 2.70                     # floor to ceiling (assumed)
H_SDK = 2.30                 # plasterboard ceiling in hall and bathroom (s.v. +2,300)
DOOR_TOP = 2.10              # door height on the sheet (x/2100)
SILL, HEAD = 0.45, 2.40      # window sill and head (assumed)
FLOOR = -0.02                # top of slab; floor finishes fill FLOOR..0
SHEET = (36.0, 102.0, 792.159, 508.274)  # plan-sheet.png edges in PDF points (make_sheet.py)


def X(px): return (px - CX) * K
def Y(py): return (CY - py) * K
def M(pt): return pt * K


# ---------------------------------------------------------------- scene reset
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
KITCHEN = collection('Kitchen')
BATH = collection('Bathroom')
FURN = collection('Furniture')
CEIL = collection('Ceilings', hide_render=True)
NOTES = collection('Plan labels')
REF = collection('Reference plan', hide_render=True)
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
        if hasattr(m, 'surface_render_method'):
            m.surface_render_method = 'BLENDED'
        else:
            m.blend_method = 'BLEND'
    m.diffuse_color = (*color, alpha)
    return m


def tiled(name, c1, c2, mortar, width, height, offset=0.5, rough=0.4):
    """Brick texture in world space, so neighbouring floor pieces line up."""
    m = material(name, c1, rough)
    nt = m.node_tree
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    brick = nt.nodes.new('ShaderNodeTexBrick')
    brick.offset = offset
    brick.inputs['Color1'].default_value = (*c1, 1)
    brick.inputs['Color2'].default_value = (*c2, 1)
    brick.inputs['Mortar'].default_value = (*mortar, 1)
    brick.inputs['Scale'].default_value = 1.0
    brick.inputs['Mortar Size'].default_value = 0.0025
    brick.inputs['Brick Width'].default_value = width
    brick.inputs['Row Height'].default_value = height
    nt.links.new(geo.outputs['Position'], brick.inputs['Vector'])
    nt.links.new(brick.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color'])
    return m


WALL = material('Plaster', (0.80, 0.80, 0.78), 0.9)
RENDER = material('Facade render', (0.86, 0.86, 0.84), 0.95)     # the 200 mm ETICS layer
FIN = material('Fin concrete', (0.62, 0.62, 0.61), 0.9)           # loggia side walls (W26)
CONCRETE = material('Concrete', (0.30, 0.30, 0.30), 0.9)
GRAVEL = material('Gravel', (0.52, 0.51, 0.49), 1.0)
SHAFT = material('Shaft void', (0.05, 0.05, 0.05), 1.0)
OAK_FLOOR = tiled('Oak planks', (0.45, 0.30, 0.17), (0.50, 0.34, 0.20), (0.25, 0.16, 0.09), 1.2, 0.19)
BATH_TILE = tiled('Bath floor tiles', (0.45, 0.45, 0.46), (0.42, 0.42, 0.43), (0.30, 0.30, 0.31), 0.3, 0.3, offset=0.0, rough=0.3)
TERRACE = tiled('Terrace tiles', (0.55, 0.54, 0.52), (0.52, 0.51, 0.49), (0.38, 0.37, 0.35), 0.6, 0.3, offset=0.0, rough=0.6)
WALL_TILE = material('Bath wall tiles', (0.88, 0.88, 0.86), 0.2)
WHITE = material('White lacquer', (0.88, 0.88, 0.88), 0.35)
CERAMIC = material('Ceramic', (0.95, 0.95, 0.95), 0.1)
OAK = material('Oak', (0.42, 0.28, 0.16), 0.5)
DARK = material('Anthracite', (0.06, 0.06, 0.07), 0.4)
BLACK_GLASS = material('Black glass', (0.01, 0.01, 0.01), 0.05)
STEEL = material('Steel', (0.75, 0.75, 0.77), 0.25, metal=1.0)
CHROME = material('Chrome', (0.90, 0.90, 0.90), 0.05, metal=1.0)
GLASS = material('Glass', (0.75, 0.85, 0.90), 0.0, alpha=0.18)
SOFA = material('Sofa fabric', (0.33, 0.35, 0.33), 0.95)
FABRIC = material('Bed fabric', (0.16, 0.20, 0.25), 0.9)
LINEN = material('Linen', (0.86, 0.84, 0.80), 0.9)
CUSHION = material('Cushion', (0.55, 0.45, 0.32), 0.9)
WARDROBE = material('Wardrobe', (0.78, 0.75, 0.70), 0.5)
RUG = material('Rug', (0.36, 0.38, 0.36), 1.0)
CEILING = material('Ceiling', (0.93, 0.93, 0.92), 0.9)
INK = material('Plan ink', (0.01, 0.01, 0.01), 0.9)


# ---------------------------------------------------------------- geometry helpers
def link(name, me, loc, coll, mat):
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    coll.objects.link(ob)
    return ob


def box(name, coll, mat, x0, y0, x1, y1, z0, z1, bevel=0.0):
    """Axis-aligned box: plan rectangle x0..x1, y0..y1 in PDF points, heights z0..z1 in metres."""
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
    """Vertical elliptic cylinder; centre and radii in PDF points."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=1.0, radius2=1.0, depth=1.0,
                          matrix=Matrix.Diagonal((M(rx), M(ry), z1 - z0, 1)))
    for f in bm.faces:
        f.smooth = len(f.verts) == 4
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return link(name, me, (X(cx), Y(cy), (z0 + z1) / 2), coll, mat)


def wall(name, x0, y0, x1, y1, z0=FLOOR, z1=H, mat=WALL):
    return box(name, STRUCT, mat, x0, y0, x1, y1, z0, z1)


# ---------------------------------------------------------------- structure
box('Slab', STRUCT, CONCRETE, 194.76, 122.64, 561.96, 484.80, -0.25, FLOOR)
box('Loggia slab', STRUCT, CONCRETE, 148.56, 165.60, 194.76, 278.28, -0.25, -0.04)   # between the fins
# R17: the flat roof of the floor below, in front of the living-room window
box('Roof R17', STRUCT, GRAVEL, 148.32, 330.30, 194.76, 459.70, -0.30, -0.12)

# West facade, 240 mm masonry (204.00..215.04): loggia door and living-room window
wall('Facade west pier north', 204.00, 122.64, 215.04, 164.28)
wall('Lintel loggia door', 204.00, 164.28, 215.04, 279.72, HEAD)
wall('Facade west pier', 204.00, 279.72, 215.04, 354.84)
wall('Parapet living window', 204.00, 354.84, 215.04, 435.60, FLOOR, SILL)
wall('Lintel living window', 204.00, 354.84, 215.04, 435.60, HEAD)
wall('Facade west pier south', 204.00, 435.60, 215.04, 464.52)
# ...and its 200 mm insulation (194.76..204.00), which turns 29 mm into the window reveal
wall('ETICS west north', 194.76, 122.64, 204.00, 157.32, mat=RENDER)
wall('ETICS west', 194.76, 286.68, 204.00, 356.16, mat=RENDER)
wall('ETICS parapet living window', 194.76, 356.16, 204.00, 434.28, FLOOR, SILL, mat=RENDER)
wall('ETICS lintel living window', 194.76, 356.16, 204.00, 434.28, HEAD, mat=RENDER)
wall('ETICS west south', 194.76, 434.28, 204.00, 475.56, mat=RENDER)

# South facade (masonry 464.52..475.56, insulation 475.56..484.80) with the bedroom window
wall('Facade south west', 204.00, 464.52, 416.28, 475.56)
wall('Parapet bedroom window', 416.28, 464.52, 497.16, 475.56, FLOOR, SILL)
wall('Lintel bedroom window', 416.28, 464.52, 497.16, 475.56, HEAD)
wall('Facade south east', 497.16, 464.52, 560.64, 475.56)
wall('ETICS south west', 194.76, 475.56, 417.60, 484.80, mat=RENDER)
wall('ETICS parapet bedroom window', 417.60, 475.56, 495.72, 484.80, FLOOR, SILL, mat=RENDER)
wall('ETICS lintel bedroom window', 417.60, 475.56, 495.72, 484.80, HEAD, mat=RENDER)
wall('ETICS south east', 495.72, 475.56, 561.96, 484.80, mat=RENDER)

# Loggia side walls (W26), concrete fins from the facade to the loggia edge
wall('Loggia fin north', 148.56, 157.32, 204.00, 165.60, -0.25, H, FIN)
wall('Loggia fin south', 148.56, 278.28, 204.00, 286.68, -0.25, H, FIN)

# 240 mm party walls: to the flat north of us, and to E.3/2P.2 with the entrance
wall('Party wall north', 215.04, 122.64, 547.20, 133.80)
wall('Party wall corner', 547.20, 122.64, 558.36, 136.08)
wall('Lintel entrance', 547.20, 136.08, 558.36, 186.84, DOOR_TOP)
wall('Party wall east', 547.20, 186.84, 558.36, 464.52)

# 125 mm partitions: living room | hall + bedroom, with the 800 door into the living room
wall('Partition living north', 367.56, 133.80, 373.32, 193.80)
wall('Lintel living door', 367.56, 193.80, 373.32, 235.44, DOOR_TOP)
wall('Partition living', 367.56, 235.44, 373.32, 464.52)
# Bedroom door wall at the end of the hall
wall('Bedroom door nib west', 373.32, 278.16, 377.88, 283.92)
wall('Lintel bedroom door', 377.88, 278.16, 419.52, 283.92, DOOR_TOP)
wall('Bedroom door nib east', 419.52, 278.16, 424.08, 283.92)
# Bathroom box
wall('Bath wall west', 424.08, 203.76, 429.84, 319.68)
wall('Bath wall north west', 429.84, 203.76, 468.72, 209.52)
wall('Lintel bathroom door', 468.72, 203.76, 505.68, 209.52, DOOR_TOP)
wall('Bath wall north east', 505.68, 203.76, 547.20, 209.52)
wall('Bath wall south', 429.84, 313.92, 547.20, 319.68)
wall('Shower wall lining', 429.84, 309.24, 466.80, 313.92)

# Installation shafts: IŠ/01 standing in the hall (with a 600 access panel), IŠ/02 in the bathroom corner
wall('Shaft 01 wall west', 401.04, 133.80, 406.80, 152.88)
wall('Shaft 01 wall east', 453.72, 133.80, 459.48, 152.88)
wall('Shaft 01 wall south', 406.80, 147.12, 453.72, 152.88)
wall('Shaft 02 wall west', 515.64, 278.16, 521.40, 313.92)
wall('Shaft 02 wall north', 521.40, 278.16, 547.20, 283.92)

# ---------------------------------------------------------------- floors (F11 oak, F10 tiles, F19 loggia)
box('Floor 3/4 Living room + kitchen', FLOORS, OAK_FLOOR, 215.04, 133.80, 367.56, 464.52, FLOOR, 0)
box('Floor 3/1 Hall', FLOORS, OAK_FLOOR, 373.32, 133.80, 547.20, 203.76, FLOOR, 0)
box('Floor 3/1 Hall (to bedroom)', FLOORS, OAK_FLOOR, 373.32, 203.76, 424.08, 278.16, FLOOR, 0)
box('Floor 3/3 Bedroom', FLOORS, OAK_FLOOR, 373.32, 319.68, 547.20, 464.52, FLOOR, 0)
box('Floor 3/3 Bedroom (door bay)', FLOORS, OAK_FLOOR, 373.32, 283.92, 424.08, 319.68, FLOOR, 0)
box('Floor 3/2 Bathroom', FLOORS, BATH_TILE, 429.84, 209.52, 547.20, 278.16, FLOOR, 0)
box('Floor 3/2 Bathroom (shower, basin)', FLOORS, BATH_TILE, 429.84, 278.16, 515.64, 309.24, FLOOR, 0)
box('Floor 3/2 Bathroom (basin niche)', FLOORS, BATH_TILE, 466.80, 309.24, 515.64, 313.92, FLOOR, 0)
box('Floor 3/5 Loggia', FLOORS, TERRACE, 148.80, 165.60, 204.00, 278.28, -0.045, -0.015)
box('Threshold living door', FLOORS, OAK_FLOOR, 367.56, 193.80, 373.32, 235.44, FLOOR, 0)
box('Threshold bedroom door', FLOORS, OAK_FLOOR, 377.88, 278.16, 419.52, 283.92, FLOOR, 0)
box('Threshold bathroom door', FLOORS, BATH_TILE, 468.72, 203.76, 505.68, 209.52, FLOOR, 0)
box('Threshold entrance', FLOORS, DARK, 547.20, 138.36, 558.36, 184.56, FLOOR, 0.004)
box('Threshold loggia door', FLOORS, CONCRETE, 204.00, 164.28, 215.04, 279.72, FLOOR, 0)
box('Shaft 01 void', FLOORS, SHAFT, 406.80, 133.80, 453.72, 147.12, FLOOR, 0.002)
box('Shaft 02 void', FLOORS, SHAFT, 521.40, 283.92, 547.20, 313.92, FLOOR, 0.002)

# ---------------------------------------------------------------- doors (drawn open, as on the plan)
LEAF_TOP = DOOR_TOP - 0.065
LEAF = 1.85                  # 40 mm leaf, in points


def frame(name, mat, jambs, head):
    for i, j in enumerate(jambs):
        box(f'{name} jamb {i + 1}', OPEN, mat, *j, FLOOR, DOOR_TOP)
    box(f'{name} head', OPEN, mat, *head, DOOR_TOP - 0.06, DOOR_TOP)


# Entrance D/01 L, 1 000 mm security door from the corridor, hinged at (547.20, 138.36), drawn open along y = 138.36
frame('Entrance frame', DARK, [(547.20, 136.08, 558.36, 138.36), (547.20, 184.56, 558.36, 186.84)],
      (547.20, 138.36, 558.36, 184.56))
box('Entrance door', OPEN, DARK, 501.00, 138.36, 547.20, 138.36 + LEAF, 0.005, LEAF_TOP, 0.003)
box('Entrance handle in', OPEN, CHROME, 503.5, 138.36 + LEAF, 508.5, 141.6, 1.00, 1.03)
box('Entrance handle out', OPEN, CHROME, 503.5, 137.0, 508.5, 138.36, 1.00, 1.03)

# Living room D/12 P, 800 mm, hinged at (367.56, 233.04), drawn open along y = 233.04
frame('Living door frame', WHITE, [(366.84, 192.48, 374.04, 196.08), (366.84, 233.04, 374.04, 236.76)],
      (366.84, 196.08, 374.04, 233.04))
box('Living door', OPEN, WHITE, 330.60, 233.04 - LEAF, 367.56, 233.04, 0.005, LEAF_TOP, 0.003)
box('Living door handle in', OPEN, CHROME, 332.5, 233.04 - LEAF - 1.4, 337.5, 233.04 - LEAF, 1.00, 1.03)
box('Living door handle out', OPEN, CHROME, 332.5, 233.04, 337.5, 234.44, 1.00, 1.03)

# Bedroom D/13 L, 800 mm, hinged at (380.28, 283.92), drawn open along x = 380.28
frame('Bedroom door frame', WHITE, [(376.56, 277.44, 380.28, 284.52), (417.24, 277.44, 420.84, 284.52)],
      (380.28, 277.44, 417.24, 284.52))
box('Bedroom door', OPEN, WHITE, 380.28, 283.92, 380.28 + LEAF, 320.88, 0.005, LEAF_TOP, 0.003)
box('Bedroom door handle in', OPEN, CHROME, 380.28 + LEAF, 314.5, 380.28 + LEAF + 1.4, 319.5, 1.00, 1.03)
box('Bedroom door handle out', OPEN, CHROME, 378.88, 314.5, 380.28, 319.5, 1.00, 1.03)

# Bathroom D/14 P, 700 mm, hinged at (503.40, 209.52), drawn open along x = 503.40
frame('Bathroom door frame', WHITE, [(467.28, 203.04, 471.00, 210.24), (503.40, 203.04, 507.00, 210.24)],
      (471.00, 203.04, 503.40, 210.24))
box('Bathroom door', OPEN, WHITE, 503.40 - LEAF, 209.52, 503.40, 241.80, 0.005, LEAF_TOP, 0.003)
box('Bathroom handle in', OPEN, CHROME, 503.40 - LEAF - 1.4, 235.5, 503.40 - LEAF, 240.5, 1.00, 1.03)
box('Bathroom handle out', OPEN, CHROME, 503.40, 235.5, 504.80, 240.5, 1.00, 1.03)

# ---------------------------------------------------------------- windows and the loggia door
# Frames sit in the outer 70 mm of the masonry (west 204.00..207.24, south 472.32..475.56);
# the glass is the drawn double line (205.20..206.04 and 473.52..474.48).
FR = 0.07


def west_glazing(name, y0, y1, posts, z0, z1, glass=True):
    """Frame along the west facade from y0 to y1; posts are (a, b) y ranges of jambs and mullions."""
    box(f'{name} frame bottom', OPEN, DARK, 204.00, y0, 207.24, y1, z0, z0 + FR)
    box(f'{name} frame top', OPEN, DARK, 204.00, y0, 207.24, y1, z1 - FR, z1)
    for i, (a, b) in enumerate(posts):
        box(f'{name} frame post {i + 1}', OPEN, DARK, 204.00, a, 207.24, b, z0 + FR, z1 - FR)
    if glass:
        for i, ((_, a), (b, _)) in enumerate(zip(posts, posts[1:])):
            box(f'{name} glass {i + 1}', OPEN, GLASS, 205.20, a, 206.04, b, z0 + FR, z1 - FR)


west_glazing('Living window', 354.84, 435.60, [(354.84, 357.96), (375.12, 378.36), (432.36, 435.60)], SILL, HEAD)
box('Living window board', OPEN, WHITE, 207.24, 354.84, 216.36, 435.60, SILL, SILL + 0.02, 0.002)
box('Living window sill outside', OPEN, STEEL, 192.80, 356.16, 204.00, 434.28, SILL - 0.03, SILL - 0.01)
box('Living window railing', OPEN, GLASS, 192.20, 356.16, 192.80, 434.28, SILL, 1.00)
box('Living window rail', OPEN, STEEL, 191.90, 356.16, 193.10, 434.28, 1.00, 1.03)

# South window O/01P: wide pane west, narrow east
box('Bedroom window frame bottom', OPEN, DARK, 416.28, 472.32, 497.16, 475.56, SILL, SILL + FR)
box('Bedroom window frame top', OPEN, DARK, 416.28, 472.32, 497.16, 475.56, HEAD - FR, HEAD)
for i, (a, b) in enumerate([(416.28, 419.52), (473.52, 476.76), (493.92, 497.16)]):
    box(f'Bedroom window frame post {i + 1}', OPEN, DARK, a, 472.32, b, 475.56, SILL + FR, HEAD - FR)
for i, (a, b) in enumerate([(419.52, 473.52), (476.76, 493.92)]):
    box(f'Bedroom window glass {i + 1}', OPEN, GLASS, a, 473.52, b, 474.48, SILL + FR, HEAD - FR)
box('Bedroom window board', OPEN, WHITE, 416.28, 463.20, 497.16, 472.32, SILL, SILL + 0.02, 0.002)
box('Bedroom window sill outside', OPEN, STEEL, 417.60, 475.56, 495.72, 486.50, SILL - 0.03, SILL - 0.01)
box('Bedroom window railing', OPEN, GLASS, 417.60, 486.50, 495.72, 487.10, SILL, 1.00)
box('Bedroom window rail', OPEN, STEEL, 417.60, 486.20, 495.72, 487.40, 1.00, 1.03)

# Loggia door: an 800 mm door sash (167.52..204.24) beside a fixed 1 500 mm pane, full height to the head
west_glazing('Loggia door', 164.28, 279.72, [(164.28, 167.52), (204.24, 207.48), (276.48, 279.72)], 0.0, HEAD, glass=False)
box('Loggia fixed pane rail', OPEN, DARK, 204.00, 207.48, 207.24, 276.48, FR, FR + 0.06)
box('Loggia fixed pane', OPEN, GLASS, 205.20, 207.48, 206.04, 276.48, FR + 0.06, HEAD - FR)
# The sash, drawn open into the living room along y = 167.52 (hinge at x = 207.24), 70 mm deep
SY0, SY1, SX0, SX1 = 167.52, 170.76, 207.24, 243.96
box('Loggia sash', OPEN, DARK, SX0, SY0, SX0 + 2.6, SY1, FR, HEAD - FR)
box('Loggia sash stile', OPEN, DARK, SX1 - 2.6, SY0, SX1, SY1, FR, HEAD - FR)
box('Loggia sash rail bottom', OPEN, DARK, SX0 + 2.6, SY0, SX1 - 2.6, SY1, FR, FR + 0.10)
box('Loggia sash rail top', OPEN, DARK, SX0 + 2.6, SY0, SX1 - 2.6, SY1, HEAD - FR - 0.07, HEAD - FR)
box('Loggia sash glass', OPEN, GLASS, SX0 + 2.6, 168.72, SX1 - 2.6, 169.56, FR + 0.10, HEAD - FR - 0.07)
box('Loggia sash handle', OPEN, CHROME, SX1 - 2.2, SY1, SX1 - 1.2, SY1 + 1.4, 1.00, 1.14)

# Loggia railing on the open edge
box('Loggia railing', OPEN, GLASS, 148.56, 165.60, 149.40, 278.28, -0.02, 1.00)
box('Loggia rail', OPEN, STEEL, 148.40, 165.60, 149.60, 278.28, 1.00, 1.03)

# ---------------------------------------------------------------- kitchen: the drawn 3 300 mm run on the north wall
WORK_TOP = 0.90
KY0, KY1 = 133.80, 163.74                     # wall to the drawn front line: 650 mm
box('Kitchen plinth', KITCHEN, DARK, 215.04, KY0, 367.56, KY1 - 2.0, 0, 0.10)
box('Kitchen base cabinets', KITCHEN, WHITE, 215.04, KY0, 367.56, KY1 - 0.9, 0.10, WORK_TOP - 0.04)
fronts = [215.04, 236.0, 266.0, 296.0, 326.0, 354.0, 367.56]
for i, (a, b) in enumerate(zip(fronts, fronts[1:])):
    box(f'Kitchen front {i + 1}', KITCHEN, WHITE, a + 0.2, KY1 - 0.9, b - 0.2, KY1 - 0.1, 0.12, WORK_TOP - 0.06, 0.002)
box('Worktop', KITCHEN, OAK, 215.04, KY0, 367.56, KY1 + 0.5, WORK_TOP - 0.04, WORK_TOP)
box('Splashback', KITCHEN, WALL_TILE, 215.04, KY0, 367.56, KY0 + 0.4, WORK_TOP, 1.45)
box('Hob', KITCHEN, BLACK_GLASS, 237.0, 136.0, 265.0, 160.0, WORK_TOP, WORK_TOP + 0.006)
for i, (cx, cy, r) in enumerate([(242.5, 143.5, 4.0), (255.5, 141.5, 5.0), (242.0, 155.0, 4.5), (256.5, 155.5, 3.5)]):
    cylinder(f'Hob ring {i + 1}', KITCHEN, DARK, cx, cy, r, r, WORK_TOP + 0.006, WORK_TOP + 0.007)
box('Sink', KITCHEN, STEEL, 327.5, 137.0, 353.5, 160.0, WORK_TOP, WORK_TOP + 0.003)
box('Sink bowl', KITCHEN, DARK, 329.5, 139.0, 351.5, 158.0, WORK_TOP + 0.003, WORK_TOP + 0.004)
cylinder('Tap', KITCHEN, CHROME, 340.5, 135.6, 0.8, 0.8, WORK_TOP, WORK_TOP + 0.28)
box('Tap spout', KITCHEN, CHROME, 339.9, 135.0, 341.1, 145.0, WORK_TOP + 0.25, WORK_TOP + 0.27)
walls_at = [215.04, 236.0, 266.0, 296.0, 326.0, 367.56]
for i, (a, b) in enumerate(zip(walls_at, walls_at[1:])):
    if i == 1:
        continue                               # over the hob: the hood instead
    box(f'Wall cabinet {i + 1}', KITCHEN, WHITE, a + 0.15, KY0, b - 0.15, KY0 + 16.2, 1.45, 2.15, 0.003)
box('Cooker hood', KITCHEN, STEEL, 236.5, KY0, 265.5, KY0 + 23.0, 1.56, 1.62, 0.003)
box('Hood chimney', KITCHEN, STEEL, 245.0, KY0, 257.0, KY0 + 11.0, 1.62, 2.15)

# ---------------------------------------------------------------- bathroom
TILE_TOP = 2.05
box('Wall tiles west', BATH, WALL_TILE, 429.84, 209.52, 430.04, 309.24, 0, TILE_TOP)
box('Wall tiles north west', BATH, WALL_TILE, 429.84, 209.52, 468.72, 209.72, 0, TILE_TOP)
box('Wall tiles north east', BATH, WALL_TILE, 505.68, 209.52, 540.27, 209.72, 0, TILE_TOP)
box('Wall tiles shower', BATH, WALL_TILE, 429.84, 309.04, 466.80, 309.24, 0, TILE_TOP)
box('Wall tiles shaft', BATH, WALL_TILE, 515.44, 283.92, 515.64, 307.50, 0, TILE_TOP)

# Shower: 800 mm tray in the south-west corner, glass screen on its open side
box('Shower tray', BATH, CERAMIC, 430.04, 275.30, 466.80, 309.04, 0, 0.04, 0.004)
cylinder('Shower drain', BATH, STEEL, 432.6, 306.6, 1.2, 1.2, 0.04, 0.042)
box('Shower glass', BATH, GLASS, 445.0, 274.90, 466.60, 275.70, 0.04, 2.00)
box('Shower glass profile', BATH, CHROME, 465.60, 274.70, 466.80, 275.90, 0.04, 2.01)
box('Shower mixer', BATH, CHROME, 445.0, 307.8, 450.0, 309.04, 1.00, 1.10)
box('Shower rail', BATH, CHROME, 447.0, 308.2, 448.0, 309.04, 1.10, 1.95)
cylinder('Shower head', BATH, CHROME, 447.5, 305.5, 2.6, 2.6, 1.90, 1.92)

# Towel radiator on the west wall
box('Towel radiator', BATH, WHITE, 430.04, 225.0, 431.8, 249.0, 0.20, 1.25, 0.002)

# Washbasin on its 1.20 m installation wall (v.s. 1200) against the south wall
box('Basin installation wall', BATH, WALL_TILE, 466.80, 307.50, 515.44, 313.92, 0, 1.20)
box('Vanity', BATH, OAK, 469.0, 289.0, 505.0, 307.50, 0.42, 0.80, 0.003)
box('Washbasin', BATH, CERAMIC, 468.0, 286.0, 506.0, 307.50, 0.80, 0.85, 0.01)
cylinder('Washbasin bowl', BATH, WALL_TILE, 487.0, 296.5, 12.0, 7.0, 0.849, 0.851)
cylinder('Basin tap', BATH, CHROME, 487.0, 305.4, 0.7, 0.7, 0.85, 1.005)
box('Basin spout', BATH, CHROME, 486.5, 300.5, 487.5, 305.6, 0.98, 1.00)
box('Mirror', BATH, CHROME, 469.0, 307.10, 505.0, 307.50, 1.25, 2.00)

# WC on the 150 mm installation lining (v.s. 1200) along the east wall, washing machine beside it
box('WC installation wall', BATH, WALL_TILE, 540.27, 209.52, 547.20, 278.16, 0, 1.20)
box('Flush plate', BATH, CHROME, 539.87, 255.8, 540.27, 263.2, 1.00, 1.15)
box('WC mount', BATH, CERAMIC, 533.5, 253.3, 540.27, 265.7, 0.28, 0.42, 0.01)
cylinder('WC bowl', BATH, CERAMIC, 524.5, 259.5, 10.0, 7.6, 0.30, 0.40)
cylinder('WC seat', BATH, CERAMIC, 523.8, 259.5, 11.0, 8.2, 0.40, 0.43)
box('Washing machine', BATH, WHITE, 510.0, 213.0, 537.5, 240.0, 0, 0.85, 0.006)
box('Washing machine door', BATH, BLACK_GLASS, 516.5, 240.0, 531.0, 240.5, 0.24, 0.62, 0.004)    # front-loader, facing the room

# ---------------------------------------------------------------- hall (illustrative): shoe cabinet and hooks
box('Shoe cabinet', FURN, WHITE, 462.0, 133.80, 499.0, 148.50, 0, 1.00, 0.003)
box('Coat rail', FURN, OAK, 462.0, 133.80, 499.0, 135.20, 1.65, 1.75, 0.002)
box('Shaft 01 access panel', FURN, WHITE, 412.50, 152.88, 440.80, 153.30, 0.30, 0.90)

# ---------------------------------------------------------------- living room (as drawn)
# Dining table against the west wall, four chairs
box('Dining table top', FURN, OAK, 215.30, 268.0, 279.0, 300.0, 0.72, 0.75, 0.003)
for i, (lx, ly) in enumerate([(216.5, 269.2), (276.0, 269.2), (216.5, 297.0), (276.0, 297.0)]):
    box(f'Dining table leg {i + 1}', FURN, DARK, lx, ly, lx + 1.8, ly + 1.8, 0, 0.72)


def chair(name, cx, cy, back):
    """Round chair as drawn (9 pt radius), backrest on the side away from the table (back = -1 or +1 in y)."""
    cylinder(f'{name} seat', FURN, CUSHION, cx, cy, 8.4, 8.4, 0.43, 0.48)
    cylinder(f'{name} stem', FURN, DARK, cx, cy, 0.9, 0.9, 0.02, 0.43, 16)
    cylinder(f'{name} foot', FURN, DARK, cx, cy, 6.0, 6.0, 0.0, 0.02)
    y0, y1 = (cy - 9.2, cy - 7.8) if back < 0 else (cy + 7.8, cy + 9.2)
    box(f'{name} back', FURN, CUSHION, cx - 7.0, y0, cx + 7.0, y1, 0.50, 0.84, 0.004)
    for sx in (-6.4, 5.4):
        box(f'{name} back post {1 if sx < 0 else 2}', FURN, DARK, cx + sx, y0 + 0.15, cx + sx + 1.0, y1 - 0.15, 0.47, 0.52)


chair('Chair 1', 231.0, 257.0, -1)
chair('Chair 2', 263.0, 257.0, -1)
chair('Chair 3', 231.0, 318.0, 1)
chair('Chair 4', 263.0, 318.0, 1)

# Three-seat sofa against the bedroom partition, coffee table and rug in front
SX0_, SX1_ = 326.0, 366.8
box('Sofa base', FURN, SOFA, SX0_, 336.0, SX1_, 454.0, 0.08, 0.42, 0.01)
box('Sofa back', FURN, SOFA, SX1_ - 8.6, 336.0, SX1_, 454.0, 0.42, 0.82, 0.02)
box('Sofa arm north', FURN, SOFA, SX0_, 336.0, SX1_ - 8.6, 341.6, 0.42, 0.62, 0.015)
box('Sofa arm south', FURN, SOFA, SX0_, 448.4, SX1_ - 8.6, 454.0, 0.42, 0.62, 0.015)
for i, (a, b) in enumerate([(341.6, 377.2), (377.2, 412.8), (412.8, 448.4)]):
    box(f'Sofa cushion {i + 1}', FURN, SOFA, SX0_ + 0.6, a + 0.3, SX1_ - 8.6, b - 0.3, 0.42, 0.53, 0.025)
for i, (lx, ly) in enumerate([(SX0_ + 1, 337.0), (SX0_ + 1, 451.6), (SX1_ - 2.4, 337.0), (SX1_ - 2.4, 451.6)]):
    box(f'Sofa leg {i + 1}', FURN, DARK, lx, ly, lx + 1.4, ly + 1.4, 0, 0.08)
box('Coffee table', FURN, OAK, 282.0, 366.0, 310.0, 421.0, 0.38, 0.42, 0.003)
for i, (lx, ly) in enumerate([(283.0, 367.0), (307.6, 367.0), (283.0, 418.6), (307.6, 418.6)]):
    box(f'Coffee table leg {i + 1}', FURN, DARK, lx, ly, lx + 1.4, ly + 1.4, 0, 0.38)
box('Rug', FURN, RUG, 272.0, 350.0, 322.0, 438.0, 0, 0.012)
box('Radiator living', FURN, WHITE, 216.40, 364.0, 221.40, 430.0, 0.12, 0.40, 0.003)

# ---------------------------------------------------------------- bedroom (as drawn)
# 1 600 x 2 000 bed, head to the party wall, with two nightstands
BX0, BX1, BY0, BY1 = 450.0, 547.20, 356.0, 431.0
box('Headboard', FURN, OAK, BX1 - 2.3, BY0, BX1, BY1, 0.08, 1.05, 0.004)
box('Bed frame', FURN, OAK, BX0, BY0, BX1 - 2.3, BY1, 0.08, 0.30, 0.004)
box('Mattress', FURN, LINEN, BX0 + 0.5, BY0 + 1.0, BX1 - 2.8, BY1 - 1.0, 0.30, 0.50, 0.03)
box('Duvet', FURN, FABRIC, BX0 + 0.3, BY0 + 0.6, BX1 - 26.0, BY1 - 0.6, 0.50, 0.55, 0.02)
box('Pillow 1', FURN, LINEN, BX1 - 18.0, BY0 + 3.0, BX1 - 4.0, BY0 + 35.0, 0.50, 0.62, 0.03)
box('Pillow 2', FURN, LINEN, BX1 - 18.0, BY1 - 35.0, BX1 - 4.0, BY1 - 3.0, 0.50, 0.62, 0.03)
for i, (lx, ly) in enumerate([(BX0 + 1, BY0 + 1), (BX0 + 1, BY1 - 3), (BX1 - 5, BY0 + 1), (BX1 - 5, BY1 - 3)]):
    box(f'Bed leg {i + 1}', FURN, DARK, lx, ly, lx + 2, ly + 2, 0, 0.08)
for i, (a, b) in enumerate([(335.5, 354.5), (432.5, 451.5)]):
    box(f'Nightstand {i + 1}', FURN, OAK, 528.5, a, 547.20, b, 0, 0.50, 0.004)
    cylinder(f'Lamp {i + 1} base', FURN, DARK, 538.0, (a + b) / 2, 3.0, 3.0, 0.50, 0.52)
    box(f'Lamp {i + 1} stem', FURN, DARK, 537.7, (a + b) / 2 - 0.3, 538.3, (a + b) / 2 + 0.3, 0.52, 0.72)
    cylinder(f'Lamp {i + 1} shade', FURN, LINEN, 538.0, (a + b) / 2, 4.5, 4.5, 0.72, 0.86)


# Wardrobe on the west wall, doors facing the room
def wardrobe(name, y0, y1, doors, x0=373.32, depth=26.2):
    box(f'{name} body', FURN, WARDROBE, x0, y0, x0 + depth - 1.4, y1, 0, 2.30)
    step = (y1 - y0) / doors
    for i in range(doors):
        box(f'{name} door {i + 1}', FURN, WARDROBE, x0 + depth - 1.4, y0 + i * step + 0.2,
            x0 + depth, y0 + (i + 1) * step - 0.2, 0.02, 2.28, 0.002)


wardrobe('Wardrobe', 344.0, 460.0, 4)
box('Radiator bedroom', FURN, WHITE, 420.0, 456.8, 495.0, 460.8, 0.12, 0.40, 0.003)
box('Bedroom rug', FURN, RUG, 412.0, 346.0, 452.0, 440.0, 0, 0.012)

# ---------------------------------------------------------------- ceilings (walk mode only; kept out of the renders)
for name, (x0, y0, x1, y1, h) in {
    'Ceiling 3/4': (215.04, 133.80, 367.56, 464.52, H),
    'Ceiling 3/3': (373.32, 283.92, 547.20, 464.52, H),
    'SDK ceiling 3/1': (373.32, 133.80, 547.20, 203.76, H_SDK),
    'SDK ceiling 3/1 (to bedroom)': (373.32, 203.76, 424.08, 278.16, H_SDK),
    'SDK ceiling 3/2': (429.84, 209.52, 547.20, 313.92, H_SDK),
}.items():
    box(name, CEIL, CEILING, x0, y0, x1, y1, h, h + 0.05)

# ---------------------------------------------------------------- plan labels
def label(name, body, px, py, size):
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = body
    cu.size = size
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    cu.materials.append(INK)
    ob = bpy.data.objects.new(name, cu)
    ob.location = (X(px), Y(py), 0.003)
    NOTES.objects.link(ob)


for no, (px, py) in {'3/1': (520, 170), '3/2': (490, 255), '3/3': (430, 330), '3/4': (300, 220), '3/5': (176, 222)}.items():
    label(f'Room {no}', no, px, py, 0.32)

# ---------------------------------------------------------------- the PDF's plan under the slab
plan_png = os.path.join(HERE, 'plan-sheet.png')
if os.path.exists(plan_png):
    img = bpy.data.images.load(plan_png)
    img.pack()
    ref = bpy.data.materials.new('Reference plan')
    ref.use_nodes = True
    nt = ref.node_tree
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = img
    nt.links.new(tex.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color'])
    x0, y0, x1, y1 = SHEET
    me = bpy.data.meshes.new('Reference plan')
    me.from_pydata([(X(x0), Y(y1), 0), (X(x1), Y(y1), 0), (X(x1), Y(y0), 0), (X(x0), Y(y0), 0)],
                   [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new()
    for loop, co in zip(uv.data, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        loop.uv = co
    link('Reference plan', me, (0, 0, -0.32), REF, ref)

# ---------------------------------------------------------------- lights, world, cameras
world = bpy.data.worlds.new('World') if not scene.world else scene.world
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.62, 0.66, 0.72, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.9

sun = bpy.data.lights.new('Sun', 'SUN')
sun.energy = 3.5
sun.angle = math.radians(8)
sun_ob = bpy.data.objects.new('Sun', sun)
sun_ob.rotation_euler = (math.radians(30), math.radians(-10), math.radians(-120))
RIG.objects.link(sun_ob)


def camera(name, loc, target=None, lens=30, ortho=None):
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


# Top camera frames the flat (loggia to party wall) orthographically
cam_top = camera('Cam plan (top)', (X(353.0), Y(303.7), 20), ortho=M(430))
cam_sw = camera('Cam from south-west', (-7.5, -9.0, 10.5), (0.0, -0.2, 0.0), lens=34)
cam_ne = camera('Cam from north-east', (7.5, 8.0, 10.5), (-0.4, 0.0, 0.0), lens=34)

scene.camera = cam_sw
scene.render.engine = 'BLENDER_EEVEE_NEXT'
if hasattr(scene.eevee, 'taa_render_samples'):
    scene.eevee.taa_render_samples = 48
for flag in ('use_raytracing', 'use_shadows'):
    if hasattr(scene.eevee, flag):
        setattr(scene.eevee, flag, True)

for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'
                    space.clip_end = 200
                    space.region_3d.view_perspective = 'CAMERA'

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'e433-2p3.blend'))
print('SAVED', os.path.join(HERE, 'e433-2p3.blend'))

# ---------------------------------------------------------------- renders
if '--render' in ARGS:
    out = os.path.join(HERE, 'renders')
    os.makedirs(out, exist_ok=True)
    shots = [('plan-top.png', cam_top, (1600, 1400), True),
             ('view-south-west.png', cam_sw, (1600, 1100), False),
             ('view-north-east.png', cam_ne, (1600, 1100), False)]
    for fname, cam, (rx, ry), labels in shots:
        NOTES.hide_render = not labels
        scene.camera = cam
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
        scene.render.resolution_percentage = 100
        scene.render.filepath = os.path.join(out, fname)
        bpy.ops.render.render(write_still=True)
        print('RENDERED', scene.render.filepath)
