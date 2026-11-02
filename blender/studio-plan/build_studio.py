"""Metropolis Tower, building A, unit 10 (2.NP, 1+kk) rebuilt as a 3D scene.

Run:  blender -b --factory-startup -P build_studio.py -- [--render]

Plan positions are pixels of plan-reference.png (1200x2280), measured from the
image's wall and floor colour runs; S converts them to metres. The developer's
1:50 PDF (Central Group, 18.09.2026) confirms the scale and supplies the heights:
interior 1 960 + 1 690 mm wide, window 2 300 x 1 500 on an 870 mm sill, doors
900/700/800 x 2 100, drywall ceiling (SDK) at 2 350 mm in hall and bathroom.
Room areas from the model: 18.05 / 3.86 / 4.30 m2 against the PDF's 18.0 / 3.9 / 4.5.
"""
import bpy, bmesh, math, os, sys
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []

S = 220.0                # px per metre: 60 cm washer = 132 px, 60 cm worktop = 136 px, 70 cm door = 152 px
CX, CY = 600, 1140       # image centre -> world origin
H = 2.70                 # living room floor to ceiling (not on the PDF; assumed)
SDK_CEILING = 2.35       # drywall ceiling in hall and bathroom (PDF: s.v. 2 350 mm)
DOOR_TOP = 2.16          # 2 100 mm door leaf plus frame head
SILL, HEAD = 0.87, 2.37  # window 1 500 mm high on an 870 mm sill (PDF: 1500 (870))
FLOOR = -0.02            # top of slab; floor finishes fill FLOOR..0


def X(px): return (px - CX) / S
def Y(py): return (CY - py) / S
def M(px): return px / S


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
CEIL = collection('SDK ceilings 2.35 m', hide_render=True)
CEIL.hide_viewport = True  # cutaway by default; switch on to see the lowered ceilings
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
OAK_FLOOR = tiled('Oak planks', (0.45, 0.30, 0.17), (0.50, 0.34, 0.20), (0.25, 0.16, 0.09), 1.2, 0.19, turn=True)
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
FABRIC = material('Sofa fabric', (0.16, 0.20, 0.25), 0.9)
CUSHION = material('Cushion', (0.55, 0.45, 0.32), 0.9)
WARDROBE = material('Wardrobe', (0.78, 0.75, 0.70), 0.5)
INK = material('Plan ink', (0.01, 0.01, 0.01), 0.9)


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


def cylinder(name, coll, mat, cx, cy, rx, ry, z0, z1, seg=48):
    """Vertical elliptic cylinder; centre and radii in plan pixels."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=1.0, radius2=1.0, depth=1.0,
                          matrix=Matrix.Diagonal((M(rx), M(ry), z1 - z0, 1)))
    for f in bm.faces:
        f.smooth = len(f.verts) == 4
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return link(name, me, (X(cx), Y(cy), (z0 + z1) / 2), coll, mat)


def disc_facing_y(name, coll, mat, cx, y0, y1, zc, radius, seg=48):
    """Round panel whose axis runs along plan y (e.g. a washer door)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=radius, radius2=radius,
                          depth=M(abs(y1 - y0)), matrix=Matrix.Rotation(math.pi / 2, 4, 'X'))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return link(name, me, (X(cx), Y((y0 + y1) / 2), zc), coll, mat)


def wall(name, x0, y0, x1, y1, z0=FLOOR, z1=H):
    return box(name, STRUCT, WALL, x0, y0, x1, y1, z0, z1)


# ---------------------------------------------------------------- structure
box('Slab', STRUCT, CONCRETE, 110, 255, 1088, 2169, -0.25, FLOOR)

# Party walls. The window wall is twice as thick; both side walls thicken
# outwards between the bathroom's top and bottom walls.
wall('Wall top left', 143, 255, 651, 309)
wall('Wall top right', 878, 255, 1056, 309)
wall('Lintel entrance', 651, 255, 878, 309, DOOR_TOP)
wall('Wall left', 146, 309, 200, 2071)
wall('Wall right', 999, 309, 1053, 2071)
wall('Pier left', 110, 474, 146, 1053)
wall('Pier right', 1053, 474, 1088, 1053)
wall('Wall window left', 143, 2071, 357, 2169)
wall('Wall window right', 859, 2071, 1056, 2169)
wall('Wall under window', 357, 2071, 859, 2169, FLOOR, SILL)
wall('Wall over window', 357, 2071, 859, 2169, HEAD)

# Service shafts (the two unnumbered white areas behind the bathroom)
wall('Shaft partition', 558, 309, 579, 474)
wall('Shaft lining', 626, 309, 630, 474)

# Bathroom walls
wall('Bath wall top', 200, 474, 629, 506)
wall('Bath wall left', 200, 506, 233, 1012)
wall('Bath wall right upper', 602, 506, 629, 652)
wall('Bath wall right lower', 602, 825, 629, 1012)
wall('Lintel bathroom', 602, 652, 629, 825, DOOR_TOP)
wall('Bath wall bottom', 200, 1012, 629, 1044)

# Hall / living room partition
wall('Partition left', 629, 873, 648, 900)
wall('Partition right', 842, 873, 999, 900)
wall('Lintel living room', 648, 873, 842, 900, DOOR_TOP)

# ---------------------------------------------------------------- floors
box('Floor 10.1 Obývací pokoj + KK', FLOORS, OAK_FLOOR, 200, 1044, 999, 2071, FLOOR, 0)
box('Floor 10.1 Obývací pokoj + KK (by door)', FLOORS, OAK_FLOOR, 629, 900, 999, 1044, FLOOR, 0)
box('Threshold living', FLOORS, OAK_FLOOR, 648, 873, 842, 900, FLOOR, 0)
box('Floor 10.2 Koupelna + WC', FLOORS, BATH_TILE, 233, 506, 602, 1012, FLOOR, 0)
box('Threshold bathroom', FLOORS, BATH_TILE, 602, 652, 629, 825, FLOOR, 0)
box('Floor 10.3 Předsíň', FLOORS, HALL_TILE, 630, 309, 999, 873, FLOOR, 0)
box('Threshold entrance', FLOORS, HALL_TILE, 651, 255, 878, 309, FLOOR, 0)
box('Shaft floor A', FLOORS, CONCRETE, 200, 309, 558, 474, FLOOR, 0)
box('Shaft floor B', FLOORS, CONCRETE, 579, 309, 626, 474, FLOOR, 0)

box('SDK ceiling hall', CEIL, WALL, 630, 309, 999, 873, SDK_CEILING, SDK_CEILING + 0.05)
box('SDK ceiling bathroom', CEIL, WALL, 233, 506, 602, 1012, SDK_CEILING, SDK_CEILING + 0.05)

# ---------------------------------------------------------------- doors (drawn open, as on the plan)
LEAF_TOP = DOOR_TOP - 0.065


def frame(name, mat, jambs, head):
    for i, j in enumerate(jambs):
        box(f'{name} jamb {i + 1}', OPEN, mat, *j, FLOOR, DOOR_TOP)
    box(f'{name} head', OPEN, mat, *head, DOOR_TOP - 0.06, DOOR_TOP)


# Entrance: 90 cm leaf hinged at (666, 310), open along x = 666
frame('Entrance frame', DARK, [(651, 255, 663, 309), (866, 255, 878, 309)], (663, 255, 866, 309))
box('Entrance door', OPEN, DARK, 663, 310, 672, 505, 0.005, LEAF_TOP, 0.003)
box('Entrance handle in', OPEN, CHROME, 672, 478, 678, 498, 1.00, 1.03)
box('Entrance handle out', OPEN, CHROME, 657, 478, 663, 498, 1.00, 1.03)

# Bathroom: 70 cm leaf hinged at (629, 662), opening into the hall
frame('Bathroom frame', WHITE, [(600, 652, 631, 664), (600, 813, 631, 825)], (600, 664, 631, 813))
box('Bathroom door', OPEN, WHITE, 631, 662, 781, 671, 0.005, LEAF_TOP, 0.003)
box('Bathroom handle', OPEN, CHROME, 755, 655, 772, 678, 1.00, 1.03)

# Living room: 80 cm leaf hinged at (832, 900), opening into the room
frame('Living room frame', WHITE, [(648, 871, 660, 902), (830, 871, 842, 902)], (660, 871, 830, 902))
box('Living room door', OPEN, WHITE, 826, 902, 835, 1075, 0.005, LEAF_TOP, 0.003)
box('Living room handle', OPEN, CHROME, 819, 1045, 842, 1062, 1.00, 1.03)

# Window: two panes either side of a mullion, frame set in the middle of the wall
box('Window frame left', OPEN, DARK, 357, 2104, 372, 2130, SILL, HEAD)
box('Window frame right', OPEN, DARK, 844, 2104, 859, 2130, SILL, HEAD)
box('Window frame bottom', OPEN, DARK, 372, 2104, 844, 2130, SILL, SILL + 0.07)
box('Window frame top', OPEN, DARK, 372, 2104, 844, 2130, HEAD - 0.07, HEAD)
box('Window mullion', OPEN, DARK, 600, 2104, 618, 2130, SILL + 0.07, HEAD - 0.07)
box('Window glass', OPEN, GLASS, 372, 2115, 844, 2119, SILL + 0.07, HEAD - 0.07)
box('Window board', OPEN, WHITE, 350, 2060, 866, 2104, SILL, SILL + 0.02, 0.002)

# ---------------------------------------------------------------- kitchen (L along bathroom wall and left wall)
WORK_TOP = 0.90
box('Kitchen plinth', KITCHEN, DARK, 202, 1045, 629, 1165, 0, 0.10)
box('Kitchen plinth return', KITCHEN, DARK, 202, 1165, 325, 1400, 0, 0.10)
box('Kitchen base cabinets', KITCHEN, WHITE, 202, 1045, 629, 1175, 0.10, WORK_TOP - 0.04)
box('Kitchen base return', KITCHEN, WHITE, 202, 1175, 335, 1400, 0.10, WORK_TOP - 0.04)
for i, (a, b) in enumerate([(337, 432), (434, 530), (532, 627)]):
    box(f'Kitchen front {i + 1}', KITCHEN, WHITE, a, 1175, b, 1179, 0.12, WORK_TOP - 0.06, 0.002)
for i, (a, b) in enumerate([(1181, 1289), (1291, 1398)]):
    box(f'Kitchen front return {i + 1}', KITCHEN, WHITE, 335, a, 339, b, 0.12, WORK_TOP - 0.06, 0.002)
box('Worktop', KITCHEN, OAK, 202, 1045, 629, 1183, WORK_TOP - 0.04, WORK_TOP)
box('Worktop return', KITCHEN, OAK, 202, 1183, 341, 1400, WORK_TOP - 0.04, WORK_TOP)

box('Sink', KITCHEN, STEEL, 353, 1066, 452, 1165, WORK_TOP, WORK_TOP + 0.003)
box('Sink bowl', KITCHEN, DARK, 362, 1075, 443, 1156, WORK_TOP + 0.003, WORK_TOP + 0.004)
cylinder('Tap', KITCHEN, CHROME, 402, 1056, 3.5, 3.5, WORK_TOP, WORK_TOP + 0.26)
box('Tap spout', KITCHEN, CHROME, 399, 1054, 405, 1098, WORK_TOP + 0.23, WORK_TOP + 0.25)

box('Hob', KITCHEN, BLACK_GLASS, 497, 1053, 564, 1180, WORK_TOP, WORK_TOP + 0.006)
for i, cy in enumerate((1085, 1150)):
    cylinder(f'Hob ring {i + 1}', KITCHEN, DARK, 530, cy, 24, 24, WORK_TOP + 0.006, WORK_TOP + 0.007)

# The asterisk box at the end of the L is the fridge
box('Fridge', KITCHEN, WHITE, 204, 1402, 337, 1531, 0, 1.85, 0.004)
box('Fridge handle', KITCHEN, CHROME, 337, 1505, 341, 1515, 0.95, 1.55)

# ---------------------------------------------------------------- bathroom
TILE_TOP = 2.20
box('Wall tiles left', BATH, WALL_TILE, 233, 506, 236, 1012, 0, TILE_TOP)
box('Wall tiles top', BATH, WALL_TILE, 236, 506, 602, 509, 0, TILE_TOP)
box('Wall tiles right upper', BATH, WALL_TILE, 599, 509, 602, 652, 0, TILE_TOP)
box('Wall tiles right lower', BATH, WALL_TILE, 599, 825, 602, 1009, 0, TILE_TOP)
box('Wall tiles bottom', BATH, WALL_TILE, 236, 1009, 599, 1012, 0, TILE_TOP)

# Wall-hung WC in front of the cistern niche
box('WC mount', BATH, CERAMIC, 315, 509, 363, 545, 0.28, 0.42, 0.01)
cylinder('WC bowl', BATH, CERAMIC, 339, 575, 33, 48, 0.30, 0.40)
cylinder('WC seat', BATH, CERAMIC, 339, 577, 35, 50, 0.40, 0.43)
box('Flush plate', BATH, CHROME, 322, 509, 356, 511, 1.00, 1.16)

box('Washbasin', BATH, CERAMIC, 441, 509, 562, 615, 0.70, 0.85, 0.02)
cylinder('Washbasin bowl', BATH, WALL_TILE, 501, 568, 46, 36, 0.849, 0.851)
cylinder('Basin tap', BATH, CHROME, 501, 524, 2.6, 2.6, 0.85, 1.00)
box('Basin spout', BATH, CHROME, 498, 524, 504, 548, 0.98, 1.00)
box('Mirror', BATH, CHROME, 445, 509, 558, 511, 1.05, 1.85)

# Tray sits on a tiled masonry base (PDF: "podezděno")
TRAY = 0.15
box('Shower tray base', BATH, WALL_TILE, 236, 812, 432, 1009, 0, TRAY - 0.04)
box('Shower tray', BATH, CERAMIC, 236, 812, 432, 1009, TRAY - 0.04, TRAY, 0.005)
cylinder('Shower drain', BATH, STEEL, 268, 846, 9, 9, TRAY, TRAY + 0.002)
box('Shower glass door', BATH, GLASS, 236, 810, 432, 813, TRAY, 2.00)
box('Shower glass side', BATH, GLASS, 430, 813, 433, 1009, TRAY, 2.00)
box('Shower arm', BATH, CHROME, 236, 898, 275, 902, 2.00, 2.02)
cylinder('Shower head', BATH, CHROME, 275, 900, 22, 22, 1.98, 2.00)
box('Shower mixer', BATH, CHROME, 236, 890, 242, 910, 1.00, 1.10)

box('Washing machine', BATH, WHITE, 459, 857, 591, 989, 0, 0.85, 0.01)
box('Washer controls', BATH, DARK, 465, 855, 585, 857, 0.74, 0.82)
disc_facing_y('Washer door', BATH, CHROME, 525, 852, 857, 0.42, 0.17)
disc_facing_y('Washer glass', BATH, BLACK_GLASS, 525, 850, 852, 0.42, 0.13)

# ---------------------------------------------------------------- furniture
# Built-in wardrobes (hall and living room)
def wardrobe(name, y0, y1, doors):
    box(f'{name} body', FURN, WARDROBE, 862, y0, 998, y1, 0, 2.40)
    step = (y1 - y0) / doors
    for i in range(doors):
        box(f'{name} door {i + 1}', FURN, WARDROBE,
            856, y0 + i * step + 1, 862, y0 + (i + 1) * step - 1, 0.02, 2.38, 0.002)


wardrobe('Hall wardrobe', 545, 872, 3)
wardrobe('Room wardrobe', 902, 1117, 2)

# Dining table against the right wall, four chairs
box('Dining table top', FURN, OAK, 715, 1338, 996, 1513, 0.72, 0.75, 0.003)
for i, (lx, ly) in enumerate([(719, 1342), (983, 1342), (719, 1500), (983, 1500)]):
    box(f'Dining table leg {i + 1}', FURN, DARK, lx, ly, lx + 9, ly + 9, 0, 0.72)


def chair(name, cx, cy, back_north):
    half = 46
    box(f'{name} seat', FURN, DARK, cx - half, cy - half, cx + half, cy + half, 0.43, 0.47, 0.004)
    for i, (sx, sy) in enumerate([(-1, -1), (1, -1), (-1, 1), (1, 1)]):
        lx, ly = cx + sx * (half - 6), cy + sy * (half - 6)
        box(f'{name} leg {i + 1}', FURN, DARK, lx - 3, ly - 3, lx + 3, ly + 3, 0, 0.43)
    by = cy - half if back_north else cy + half - 7
    box(f'{name} back', FURN, DARK, cx - half, by, cx + half, by + 7, 0.47, 0.86, 0.004)


chair('Chair 1', 783, 1326, True)
chair('Chair 2', 929, 1326, True)
chair('Chair 3', 783, 1525, False)
chair('Chair 4', 929, 1525, False)

# Sofa bed along the left wall, backrest drawn as the inner line at x = 255
box('Sofa base', FURN, FABRIC, 205, 1600, 419, 2038, 0.02, 0.25, 0.01)
box('Sofa back', FURN, FABRIC, 205, 1600, 255, 2038, 0.25, 0.80, 0.02)
box('Sofa cushion 1', FURN, FABRIC, 255, 1602, 417, 1818, 0.25, 0.44, 0.03)
box('Sofa cushion 2', FURN, FABRIC, 255, 1820, 417, 2036, 0.25, 0.44, 0.03)
box('Pillow 1', FURN, CUSHION, 257, 1650, 287, 1750, 0.44, 0.72, 0.03)
box('Pillow 2', FURN, CUSHION, 257, 1890, 287, 1990, 0.44, 0.72, 0.03)

box('Coffee table top', FURN, OAK, 554, 1716, 664, 1935, 0.38, 0.42, 0.003)
for i, (lx, ly) in enumerate([(558, 1720), (651, 1720), (558, 1922), (651, 1922)]):
    box(f'Coffee table leg {i + 1}', FURN, DARK, lx, ly, lx + 9, ly + 9, 0, 0.38)

box('TV unit', FURN, WHITE, 902, 1690, 997, 2068, 0.05, 0.45, 0.003)
box('TV unit plinth', FURN, DARK, 910, 1700, 990, 2058, 0, 0.05)
box('TV stand foot', FURN, DARK, 945, 1780, 985, 1840, 0.45, 0.46)
box('TV stand neck', FURN, DARK, 962, 1802, 972, 1818, 0.46, 0.58)
box('TV', FURN, BLACK_GLASS, 955, 1730, 965, 1890, 0.56, 1.00, 0.002)

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


label('Room 1', '1', 539, 1419, 0.34)
label('Room 2', '2', 419, 697, 0.34)
label('Room 3', '3', 750, 575, 0.34)
label('Entrance number', '10', 766, 137, 0.36)
me = bpy.data.meshes.new('Entrance arrow')
me.from_pydata([(X(721), Y(188), 0), (X(765), Y(234), 0), (X(809), Y(188), 0)], [], [(0, 1, 2)])
link('Entrance arrow', me, (0, 0, 0.003), NOTES, INK)

# ---------------------------------------------------------------- reference image under the slab
plan_png = os.path.join(HERE, 'plan-reference.png')
if os.path.exists(plan_png):
    img = bpy.data.images.load(plan_png)
    img.pack()
    ref = bpy.data.materials.new('Reference plan')
    ref.use_nodes = True
    nt = ref.node_tree
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = img
    nt.links.new(tex.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color'])
    me = bpy.data.meshes.new('Reference plan')
    me.from_pydata([(X(0), Y(2280), 0), (X(1200), Y(2280), 0), (X(1200), Y(0), 0), (X(0), Y(0), 0)],
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
sun_ob.rotation_euler = (math.radians(22), math.radians(-8), math.radians(-30))
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


# Top camera frames exactly the source image, so renders overlay the plan 1:1
cam_top = camera('Cam plan (top)', (0, 0, 20), ortho=2280 / S)
cam_living = camera('Cam living room', (-2.6, -7.5, 12.5), (0.2, -0.6, 0.0), lens=38)
cam_hall = camera('Cam from entrance', (2.6, 6.8, 12.5), (-0.1, -1.2, 0.0), lens=38)

scene.camera = cam_living
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

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'studio-plan.blend'))
print('SAVED', os.path.join(HERE, 'studio-plan.blend'))

# ---------------------------------------------------------------- renders
if '--render' in ARGS:
    out = os.path.join(HERE, 'renders')
    os.makedirs(out, exist_ok=True)
    shots = [('plan-top.png', cam_top, (1200, 2280), True),
             ('view-living.png', cam_living, (1600, 1200), False),
             ('view-entrance.png', cam_hall, (1600, 1200), False)]
    for fname, cam, (rx, ry), labels in shots:
        NOTES.hide_render = not labels
        scene.camera = cam
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
        scene.render.resolution_percentage = 100
        scene.render.filepath = os.path.join(out, fname)
        bpy.ops.render.render(write_still=True)
        print('RENDERED', scene.render.filepath)
