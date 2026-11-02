"""vbloku, Peroutkova 531/81, Praha 5: unit 3407 (4.NP, 1kk) rebuilt as a 3D scene.

Run:  blender -b --factory-startup -P build_unit.py -- [--render]

Plan positions are PDF points read from the vector linework of unit-3407.pdf
(AutoCAD export, 1:60 on A4), so 1 pt = 21.167 mm. Measured that way, room 01
comes to 18.45 m2 against the sheet's 18.4. The plan gives no heights: the 2.70 m
ceiling, 1.97 m door leaves and the 0.85-2.40 m windows are assumptions. The plan
shows no furniture or kitchen either; those collections are illustrative.
"""
import bpy, bmesh, math, os, sys
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []

K = 25.4 / 72 * 60 / 1000    # metres per PDF point at 1:60
CX, CY = 633.32, 252.92      # centre of the drawn unit -> world origin
H = 2.70                     # floor to ceiling (assumed)
DOOR_TOP = 2.04              # top of the frame over a 1 970 mm leaf (assumed)
SILL, HEAD = 0.85, 2.40      # window sill and head (assumed)
FLOOR = -0.02                # top of slab; floor finishes fill FLOOR..0
SHEET = (556.0, 33.0, 712.22, 492.213)  # plan-sheet.png edges in PDF points (make_sheet.py)


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
SHAFT = material('Shaft void', (0.05, 0.05, 0.05), 1.0)
OAK_FLOOR = tiled('Oak planks', (0.45, 0.30, 0.17), (0.50, 0.34, 0.20), (0.25, 0.16, 0.09), 1.2, 0.19)
HALL_TILE = tiled('Hall tiles', (0.70, 0.67, 0.62), (0.66, 0.63, 0.58), (0.45, 0.43, 0.40), 0.6, 0.6, offset=0.0, rough=0.3)
BATH_TILE = tiled('Bath floor tiles', (0.45, 0.45, 0.46), (0.42, 0.42, 0.43), (0.30, 0.30, 0.31), 0.3, 0.3, offset=0.0, rough=0.3)
WALL_TILE = material('Bath wall tiles', (0.88, 0.88, 0.86), 0.2)
WHITE = material('White lacquer', (0.88, 0.88, 0.88), 0.35)
CERAMIC = material('Ceramic', (0.95, 0.95, 0.95), 0.1)
OAK = material('Oak', (0.42, 0.28, 0.16), 0.5)
DARK = material('Anthracite', (0.06, 0.06, 0.07), 0.4)
BLACK_GLASS = material('Black glass', (0.01, 0.01, 0.01), 0.05)
STEEL = material('Steel', (0.75, 0.75, 0.77), 0.25, metal=1.0)
CHROME = material('Chrome', (0.90, 0.90, 0.90), 0.05, metal=1.0)
GLASS = material('Glass', (0.75, 0.85, 0.90), 0.0, alpha=0.18)
FABRIC = material('Bed fabric', (0.16, 0.20, 0.25), 0.9)
LINEN = material('Linen', (0.86, 0.84, 0.80), 0.9)
CUSHION = material('Cushion', (0.55, 0.45, 0.32), 0.9)
WARDROBE = material('Wardrobe', (0.78, 0.75, 0.70), 0.5)
RUG = material('Rug', (0.36, 0.38, 0.36), 1.0)
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


def cylinder(name, coll, mat, cx, cy, rx, ry, z0, z1, seg=48):
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


def wall(name, x0, y0, x1, y1, z0=FLOOR, z1=H):
    return box(name, STRUCT, WALL, x0, y0, x1, y1, z0, z1)


# ---------------------------------------------------------------- structure
# The drawing stops at x = 563.72 and 702.92; the right party wall is carried
# on to 705 so it is as thick as the left one.
box('Slab', STRUCT, CONCRETE, 563.72, 40.88, 705.0, 464.96, -0.25, FLOOR)

# Facade, 356 mm: two 1.10 m windows between a corner pier, a mullion pier and the right pier
wall('Facade pier left', 563.72, 40.88, 572.48, 57.68)
wall('Facade pier middle', 624.56, 40.88, 629.24, 57.68)
wall('Facade pier right', 681.32, 40.88, 705.0, 57.68)
for side, (a, b) in (('left', (572.48, 624.56)), ('right', (629.24, 681.32))):
    wall(f'Parapet {side}', a, 40.88, b, 57.68, FLOOR, SILL)
    wall(f'Lintel window {side}', a, 40.88, b, 57.68, HEAD)

# Party walls; the room-side lining (567.80..572.48) stops at the bathroom
wall('Wall left', 563.72, 57.68, 572.48, 314.48)
wall('Wall left bathroom', 563.72, 319.16, 567.80, 413.96)
wall('Wall right', 700.28, 57.68, 705.0, 459.80)
wall('Pier right', 684.68, 286.16, 700.28, 291.32)   # with the partition end, frames the 900 mm way into the room

# Bathroom walls and the hall partition (its end stands 600 mm proud of the bathroom)
wall('Bath wall top', 563.72, 314.48, 637.40, 319.16)
wall('Partition upper', 637.40, 286.16, 642.08, 371.12)
wall('Partition lower', 637.40, 408.92, 642.08, 459.80)
wall('Lintel bathroom', 637.40, 371.12, 642.08, 408.92, DOOR_TOP)

# Installation shaft in the bathroom corner: 100 mm walls round an open void
wall('Shaft wall left', 563.72, 413.96, 566.36, 459.80)
wall('Shaft wall top', 563.72, 413.96, 599.48, 418.64)
wall('Shaft wall right', 594.80, 418.64, 599.48, 459.80)

# Corridor wall with the entrance
wall('Wall entrance left', 563.72, 459.80, 648.20, 464.96)
wall('Wall entrance right', 695.48, 459.80, 705.0, 464.96)
wall('Lintel entrance', 648.20, 459.80, 695.48, 464.96, DOOR_TOP)

# ---------------------------------------------------------------- floors
box('Floor 01 Pokoj', FLOORS, OAK_FLOOR, 572.48, 57.68, 700.28, 286.16, FLOOR, 0)
box('Floor 01 Pokoj (by kitchen)', FLOORS, OAK_FLOOR, 572.48, 286.16, 637.40, 314.48, FLOOR, 0)
box('Floor 01 Zádveří', FLOORS, HALL_TILE, 642.08, 286.16, 700.28, 459.80, FLOOR, 0)
box('Floor 02 Koupelna s WC', FLOORS, BATH_TILE, 567.80, 319.16, 637.40, 459.80, FLOOR, 0)
box('Threshold bathroom', FLOORS, BATH_TILE, 637.40, 371.12, 642.08, 408.92, FLOOR, 0)
box('Threshold entrance', FLOORS, HALL_TILE, 648.20, 459.80, 695.48, 464.96, FLOOR, 0)
box('Shaft void', FLOORS, SHAFT, 566.36, 418.64, 594.80, 459.80, FLOOR, 0.002)
box('Window reveal left', FLOORS, CONCRETE, 572.48, 40.88, 624.56, 57.68, FLOOR, 0)
box('Window reveal right', FLOORS, CONCRETE, 629.24, 40.88, 681.32, 57.68, FLOOR, 0)

# ---------------------------------------------------------------- doors (drawn open, as on the plan)
LEAF_TOP = 1.975             # 1 970 mm leaf standing 5 mm off the floor


def frame(name, mat, jambs, head):
    for i, j in enumerate(jambs):
        box(f'{name} jamb {i + 1}', OPEN, mat, *j, FLOOR, DOOR_TOP)
    box(f'{name} head', OPEN, mat, *head, DOOR_TOP - 0.06, DOOR_TOP)


# Entrance: 900 mm, hinged at (693.2, 459.8), drawn open into the hall along x = 693.2
frame('Entrance frame', DARK, [(648.20, 459.80, 650.60, 464.96), (693.20, 459.80, 695.48, 464.96)],
      (650.60, 459.80, 693.20, 464.96))
box('Entrance door', OPEN, DARK, 691.30, 417.20, 693.20, 459.60, 0.005, LEAF_TOP, 0.003)
box('Entrance handle in', OPEN, CHROME, 693.20, 421.0, 694.60, 426.0, 1.00, 1.03)
box('Entrance handle out', OPEN, CHROME, 689.90, 421.0, 691.30, 426.0, 1.00, 1.03)

# Bathroom: 800 mm, hinged at (642.08, 408.92), drawn open into the hall along y = 408.92
frame('Bathroom frame', WHITE, [(636.44, 368.84, 643.04, 371.12), (636.44, 408.92, 643.04, 411.32)],
      (636.44, 371.12, 643.04, 408.92))
box('Bathroom door', OPEN, WHITE, 642.08, 407.02, 679.88, 408.92, 0.005, LEAF_TOP, 0.003)
box('Bathroom handle in', OPEN, CHROME, 672.0, 405.62, 677.0, 407.02, 1.00, 1.03)
box('Bathroom handle out', OPEN, CHROME, 672.0, 408.92, 677.0, 410.32, 1.00, 1.03)

# Windows: frame in the outer 150 mm of the wall (40.88..47.96), glass on the drawn middle line
for side, (a, b) in (('left', (572.48, 624.56)), ('right', (629.24, 681.32))):
    box(f'Window {side} frame bottom', OPEN, DARK, a, 40.88, b, 47.96, SILL, SILL + 0.07)
    box(f'Window {side} frame top', OPEN, DARK, a, 40.88, b, 47.96, HEAD - 0.07, HEAD)
    box(f'Window {side} frame jamb 1', OPEN, DARK, a, 40.88, a + 3.3, 47.96, SILL + 0.07, HEAD - 0.07)
    box(f'Window {side} frame jamb 2', OPEN, DARK, b - 3.3, 40.88, b, 47.96, SILL + 0.07, HEAD - 0.07)
    box(f'Window {side} glass', OPEN, GLASS, a + 3.3, 44.20, b - 3.3, 44.76, SILL + 0.07, HEAD - 0.07)
    box(f'Window {side} board', OPEN, WHITE, a, 47.96, b, 59.0, SILL, SILL + 0.02, 0.002)

# ---------------------------------------------------------------- kitchenette (illustrative), left wall
WORK_TOP = 0.90
KX0, KX1, KY0, KY1 = 572.48, 600.83, 238.9, 314.48   # 600 mm deep, 1 600 mm run against the bathroom wall
box('Kitchen plinth', KITCHEN, DARK, KX0, KY0 + 2, KX1 - 3, KY1, 0, 0.10)
box('Kitchen base cabinets', KITCHEN, WHITE, KX0, KY0, KX1 - 1.5, KY1, 0.10, WORK_TOP - 0.04)
for i, (a, b) in enumerate([(KY0, KY0 + 28.3), (KY0 + 28.4, KY0 + 56.6), (KY0 + 56.7, KY1)]):
    box(f'Kitchen front {i + 1}', KITCHEN, WHITE, KX1 - 1.5, a + 0.2, KX1 - 0.4, b - 0.2, 0.12, WORK_TOP - 0.06, 0.002)
box('Worktop', KITCHEN, OAK, KX0, KY0, KX1 + 0.5, KY1, WORK_TOP - 0.04, WORK_TOP)
box('Splashback', KITCHEN, WALL_TILE, KX0, KY0, KX0 + 0.6, KY1, WORK_TOP, 1.45)
# Sink by the bathroom wall, where the pipes are; two-zone hob towards the room
box('Sink', KITCHEN, STEEL, 576.0, 286.0, 597.0, 307.0, WORK_TOP, WORK_TOP + 0.003)
box('Sink bowl', KITCHEN, DARK, 578.0, 288.0, 595.0, 305.0, WORK_TOP + 0.003, WORK_TOP + 0.004)
cylinder('Tap', KITCHEN, CHROME, 575.0, 296.5, 0.8, 0.8, WORK_TOP, WORK_TOP + 0.26)
box('Tap spout', KITCHEN, CHROME, 574.4, 295.9, 584.0, 297.1, WORK_TOP + 0.23, WORK_TOP + 0.25)
box('Hob', KITCHEN, BLACK_GLASS, 576.5, 244.0, 595.0, 271.0, WORK_TOP, WORK_TOP + 0.006)
for i, cy in enumerate((251.0, 264.0)):
    cylinder(f'Hob ring {i + 1}', KITCHEN, DARK, 585.75, cy, 5.0, 5.0, WORK_TOP + 0.006, WORK_TOP + 0.007)
box('Wall cabinets', KITCHEN, WHITE, KX0, KY0, KX0 + 16.5, KY1, 1.50, 2.20, 0.003)
box('Cooker hood', KITCHEN, STEEL, KX0 + 16.5, 244.0, KX0 + 19.0, 271.0, 1.50, 1.56)

# ---------------------------------------------------------------- bathroom
TILE_TOP = 2.00
box('Wall tiles left', BATH, WALL_TILE, 567.80, 319.16, 568.0, 413.96, 0, TILE_TOP)
box('Wall tiles top', BATH, WALL_TILE, 567.80, 319.16, 637.40, 319.36, 0, TILE_TOP)
box('Wall tiles right upper', BATH, WALL_TILE, 637.20, 319.16, 637.40, 371.12, 0, TILE_TOP)
box('Wall tiles right lower', BATH, WALL_TILE, 637.20, 408.92, 637.40, 450.80, 0, TILE_TOP)

# Shower: 800 x 800 tray, a fixed glass screen on the drawn line y = 356
box('Shower tray', BATH, CERAMIC, 567.80, 319.16, 605.60, 356.96, 0, 0.05, 0.004)
cylinder('Shower drain', BATH, STEEL, 576.3, 348.5, 1.25, 1.25, 0.05, 0.052)
box('Shower glass', BATH, GLASS, 568.0, 355.62, 586.16, 356.38, 0.05, 2.00)
box('Shower glass profile', BATH, CHROME, 568.0, 355.4, 569.0, 356.6, 0.05, 2.00)
box('Shower mixer', BATH, CHROME, 568.0, 330.0, 569.2, 335.0, 1.00, 1.10)
box('Shower rail', BATH, CHROME, 568.0, 337.0, 569.0, 338.0, 1.10, 1.95)
cylinder('Shower head', BATH, CHROME, 570.5, 337.5, 2.5, 2.5, 1.90, 1.92)

# Washbasin on a 47 mm installation lining (the double line on the left wall)
box('Basin lining', BATH, WALL_TILE, 567.80, 357.0, 570.0, 414.0, 0, 1.20)
box('Washbasin', BATH, CERAMIC, 570.0, 373.0, 586.64, 396.8, 0.72, 0.85, 0.01)
cylinder('Washbasin bowl', BATH, WALL_TILE, 579.0, 384.9, 5.5, 8.5, 0.849, 0.851)
cylinder('Basin tap', BATH, CHROME, 572.4, 384.9, 0.7, 0.7, 0.85, 1.00)
box('Basin spout', BATH, CHROME, 571.9, 384.4, 576.5, 385.4, 0.98, 1.00)
box('Mirror', BATH, CHROME, 570.0, 371.0, 570.4, 398.8, 1.25, 1.95)

# Wall-hung WC on its 190 mm installation wall
box('WC installation wall', BATH, WALL_TILE, 599.48, 450.80, 637.40, 459.80, 0, 1.20)
box('Flush plate', BATH, CHROME, 614.7, 450.40, 622.2, 450.80, 1.00, 1.15)
box('WC mount', BATH, CERAMIC, 612.2, 444.0, 624.7, 450.80, 0.28, 0.42, 0.01)
cylinder('WC bowl', BATH, CERAMIC, 618.44, 436.0, 8.0, 10.5, 0.30, 0.40)
cylinder('WC seat', BATH, CERAMIC, 618.44, 437.0, 8.5, 11.5, 0.40, 0.43)

# The dashed rectangle is something overhead; drawn as a ceiling-hung box
box('Overhead unit (dashed on plan)', BATH, WHITE, 613.88, 322.76, 630.80, 345.44, H - 0.32, H, 0.004)

# ---------------------------------------------------------------- furniture (illustrative)
# Bed 1 400 x 2 000 along the left wall, head towards the window
BX0, BX1, BY0, BY1 = 572.48, 638.62, 112.0, 206.5
box('Bed frame', FURN, OAK, BX0, BY0, BX1, BY1, 0.08, 0.30, 0.004)
box('Mattress', FURN, LINEN, BX0 + 0.5, BY0 + 2.0, BX1 - 0.5, BY1 - 0.5, 0.30, 0.50, 0.03)
box('Duvet', FURN, FABRIC, BX0 + 0.3, BY0 + 30.0, BX1 - 0.3, BY1 - 0.3, 0.50, 0.54, 0.02)
box('Headboard', FURN, OAK, BX0, BY0 - 2.5, BX1, BY0, 0.08, 1.05, 0.004)
box('Pillow 1', FURN, LINEN, BX0 + 4.0, BY0 + 4.0, BX0 + 30.0, BY0 + 18.0, 0.50, 0.62, 0.03)
box('Pillow 2', FURN, LINEN, BX1 - 30.0, BY0 + 4.0, BX1 - 4.0, BY0 + 18.0, 0.50, 0.62, 0.03)
for i, (lx, ly) in enumerate([(BX0 + 1, BY0 + 1), (BX1 - 3, BY0 + 1), (BX0 + 1, BY1 - 3), (BX1 - 3, BY1 - 3)]):
    box(f'Bed leg {i + 1}', FURN, DARK, lx, ly, lx + 2, ly + 2, 0, 0.08)
box('Nightstand', FURN, OAK, 640.0, 112.0, 659.0, 131.0, 0, 0.50, 0.004)
cylinder('Lamp base', FURN, DARK, 649.5, 121.5, 3.0, 3.0, 0.50, 0.52)
cylinder('Lamp shade', FURN, LINEN, 649.5, 121.5, 4.5, 4.5, 0.72, 0.86)
box('Lamp stem', FURN, DARK, 649.2, 121.2, 649.8, 121.8, 0.52, 0.72)
box('Rug', FURN, RUG, 641.0, 140.0, 688.0, 210.0, 0, 0.012)

# Desk in the right window bay, with a chair
box('Desk top', FURN, OAK, 636.0, 59.0, 692.0, 87.0, 0.72, 0.75, 0.003)
for i, (lx, ly) in enumerate([(637.0, 60.0), (689.5, 60.0), (637.0, 84.5), (689.5, 84.5)]):
    box(f'Desk leg {i + 1}', FURN, DARK, lx, ly, lx + 1.6, ly + 1.6, 0, 0.72)
CHX, CHY, CHH = 664.0, 100.0, 10.4
box('Chair seat', FURN, DARK, CHX - CHH, CHY - CHH, CHX + CHH, CHY + CHH, 0.43, 0.47, 0.004)
for i, (sx, sy) in enumerate([(-1, -1), (1, -1), (-1, 1), (1, 1)]):
    lx, ly = CHX + sx * (CHH - 1.4), CHY + sy * (CHH - 1.4)
    box(f'Chair leg {i + 1}', FURN, DARK, lx - 0.7, ly - 0.7, lx + 0.7, ly + 0.7, 0, 0.43)
box('Chair back', FURN, DARK, CHX - CHH, CHY + CHH - 1.6, CHX + CHH, CHY + CHH, 0.47, 0.86, 0.004)

# Wardrobe on the right wall, clear of the way in from the hall
def wardrobe(name, y0, y1, doors, depth=28.35):
    box(f'{name} body', FURN, WARDROBE, 700.28 - depth + 1.4, y0, 700.28, y1, 0, 2.30)
    step = (y1 - y0) / doors
    for i in range(doors):
        box(f'{name} door {i + 1}', FURN, WARDROBE, 700.28 - depth, y0 + i * step + 0.2,
            700.28 - depth + 1.4, y0 + (i + 1) * step - 0.2, 0.02, 2.28, 0.002)


wardrobe('Wardrobe', 190.0, 260.9, 2)
box('Shoe cabinet', FURN, WHITE, 686.1, 296.0, 700.28, 340.0, 0, 1.00, 0.003)
box('Coat rail', FURN, CHROME, 698.6, 296.0, 699.6, 340.0, 1.75, 1.77)
box('Electrical panel', FURN, WHITE, 699.2, 349.0, 700.28, 370.6, 1.55, 1.95, 0.002)

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


label('Room 01', '01', 640.0, 134.0, 0.40)
label('Room 02', '02', 605.4, 390.5, 0.40)
me = bpy.data.meshes.new('Entrance arrow')
me.from_pydata([(X(652.64), Y(484.88), 0), (X(691.04), Y(484.88), 0), (X(671.84), Y(464.96), 0)], [], [(0, 1, 2)])
link('Entrance arrow', me, (0, 0, 0.003), NOTES, INK)

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
    link('Reference plan', me, (0, 0, -0.30), REF, ref)

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
sun_ob.rotation_euler = (math.radians(22), math.radians(-8), math.radians(150))
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


# Top camera frames exactly plan-sheet.png, so the render overlays the drawing 1:1
sx0, sy0, sx1, sy1 = SHEET
cam_top = camera('Cam plan (top)', (X((sx0 + sx1) / 2), Y((sy0 + sy1) / 2), 20), ortho=M(sy1 - sy0))
cam_entrance = camera('Cam from entrance', (3.2, -9.5, 11.0), (0.0, -0.4, 0.0), lens=38)
cam_window = camera('Cam from window', (-3.0, 9.8, 11.0), (0.0, 0.2, 0.0), lens=38)

scene.camera = cam_entrance
scene.render.engine = 'BLENDER_EEVEE_NEXT'
if hasattr(scene.eevee, 'taa_render_samples'):
    scene.eevee.taa_render_samples = 64
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

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'unit-3407.blend'))
print('SAVED', os.path.join(HERE, 'unit-3407.blend'))

# ---------------------------------------------------------------- renders
if '--render' in ARGS:
    out = os.path.join(HERE, 'renders')
    os.makedirs(out, exist_ok=True)
    sw, sh = 992, 2916
    shots = [('plan-top.png', cam_top, (sw, sh), True),
             ('view-entrance.png', cam_entrance, (1600, 1200), False),
             ('view-window.png', cam_window, (1600, 1200), False)]
    for fname, cam, (rx, ry), labels in shots:
        NOTES.hide_render = not labels
        scene.camera = cam
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
        scene.render.resolution_percentage = 100
        scene.render.filepath = os.path.join(out, fname)
        bpy.ops.render.render(write_still=True)
        print('RENDERED', scene.render.filepath)
