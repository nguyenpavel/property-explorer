"""Export d601-2.blend for 3ds Max and the other archviz renderers, as FBX (and OBJ).

Run:  blender -b d601-2/d601-2.blend --factory-startup -P d601-2/export_max.py [-- --expect out.json]

Writes export/D601_Mocca_flat.fbx: Z up, centimetres, the axis system 3ds Max uses itself,
textures embedded and also copied to export/D601_Mocca_flat.fbm/. export/obj/ holds the
same model as OBJ + MTL (Y up, metres) for tools that don't read FBX. The model is the one
the web viewer shows, at true size: the 1.15x widening is a walk-mode effect, not geometry.

The build's 280 boxes become named objects under one parent per category: the walls as
one solid (exact boolean union), each room's floor, each door as a frame and a leaf whose
pivot is the hinge (its custom property close_angle_deg is the Z rotation that shuts it),
and each window, fixture and piece of furniture as one multi-material object with its pivot
at the bottom centre. Every face gets box-projected UVs in metres; the floors carry the
viewer's plank and tile maps, with UVs scaled to each map's repeat.
"""
import bpy, bmesh, json, math, os, re, shutil, sys
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = os.path.join(HERE, 'export')
MAPS = os.path.join(HERE, 'maps')
NAME = 'D601_Mocca_flat'
S, CX, CY = 41.797, 752.8, 416.2          # as build_flat.py: pt per metre, plan point at the origin
CROP = (520, 114, 1010, 676)              # plan-sheet.png, in plan pt
os.makedirs(os.path.join(OUT, 'obj'), exist_ok=True)
os.makedirs(MAPS, exist_ok=True)


def X(px): return (px - CX) / S
def Y(py): return (CY - py) / S


vl = bpy.context.view_layer
scene = bpy.context.scene


def select(objs, active=None):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    vl.objects.active = active or objs[0]


# ---------------------------------------------------------------- floor maps, as the viewer draws them
def rgb(h): return [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]


def save_map(name, a):
    """a: H x W x 3 sRGB, row 0 at the top."""
    h, w, _ = a.shape
    px = np.ones((h, w, 4), np.float32)
    px[..., :3] = a[::-1]
    img = bpy.data.images.new(name, w, h)
    img.pixels.foreach_set(px.ravel())
    path = os.path.join(MAPS, name + '.png')
    img.filepath_raw, img.file_format = path, 'PNG'
    img.save()
    bpy.data.images.remove(img)
    return bpy.data.images.load(path)


def planks(w=640, h=1616, j=3):
    """Five 190 mm planks across, 1.2 m long, staggered: one repeat is 0.95 x 2.4 m."""
    shades = [rgb(c) for c in ('#b59877', '#ad8f6d', '#b99c7a', '#b29470', '#ae9170')]
    a = np.zeros((h, w, 3))
    pw = w // 5
    for i, off in enumerate((0, .5, .25, .75, .4)):
        x0, x1 = i * pw, (i + 1) * pw
        for k in (0, 1):
            y0 = int(round(off * h + k * h / 2))
            a[np.arange(y0, y0 + h // 2) % h, x0:x1] = shades[(i + k) % 5]
            a[np.arange(y0, y0 + j) % h, x0:x1] = rgb('#86694c')
        a[:, x0:x0 + j] = rgb('#86694c')
    return a


def tiles(face, grout, px=512, j=4):
    a = np.empty((px, px, 3))
    a[:] = rgb(grout)
    a[j:px - j, j:px - j] = rgb(face)
    return a


PERIOD = {'Oak planks': (0.95, 2.4), 'Loggia tiles': (0.6, 0.6), 'Bath floor tiles': (0.6, 0.6)}
bpy.data.materials['Hall tiles'].name = 'Loggia tiles'        # it only ever covered the loggia
for mname, img in (('Oak planks', save_map('Oak_planks', planks())),
                   ('Loggia tiles', save_map('Loggia_tiles', tiles('#b9b6b0', '#94918b'))),
                   ('Bath floor tiles', save_map('Bath_floor_tiles', tiles('#c9c9cc', '#a3a3a8')))):
    nt = bpy.data.materials[mname].node_tree
    for n in [n for n in nt.nodes if n.type not in ('BSDF_PRINCIPLED', 'OUTPUT_MATERIAL')]:
        nt.nodes.remove(n)
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = img
    nt.links.new(tex.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color'])

# ---------------------------------------------------------------- bake the build: modifiers and transforms
for o in [o for o in bpy.data.objects if o.type != 'MESH']:
    bpy.data.objects.remove(o)
src = list(bpy.data.objects)
select(src)
bpy.ops.object.convert(target='MESH')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# ---------------------------------------------------------------- group the boxes into named objects
RULES = [
    (r'^(.*) threshold floor$', 'Floor thresholds'),
    (r'^(Floor \d\d .*)$', r'\1'),
    (r'^(Loggia door, .*) transom (frame \w+|glass)$', r'\1 frame'),
    (r'^(.*door.*) (jamb \d|head)$', r'\1 frame'),
    (r'^(Loggia railing \w+) (base|rail|glass)$', r'\1'),
    (r'^Loggia glazing post$', 'Loggia glazing posts'),
    (r'^(.*window) (frame \w+|mullion \d+|glass)$', r'\1'),
    (r'^(Kitchen base|Kitchen plinth|Kitchen unit joint|Worktop)( \d)?$', 'Kitchen units'),
    (r'^(Sink|Sink bowl|Kitchen tap)$', 'Kitchen sink'),
    (r'^Hob( ring \d)?$', 'Hob'),
    (r'^Bathtub( inside)?$', 'Bathtub'),
    (r'^(WC \d\d) (bowl|mount|seat)$', r'\1'),
    (r'^(.*[Bb]asin \d\d.*?)( bowl)?$', r'\1'),
    (r'^Washing machine( door)?$', 'Washing machine'),
    (r'^(Bed \d\d) .*$', r'\1'),
    (r'^(.*[Cc]hair \d+) (seat|back|leg \d)$', r'\1'),
    (r'^(Coffee table|Dining table|Desk \d\d) (top|leg \d|side \d)$', r'\1'),
    (r'^(Monitor \d\d)( stand)?$', r'\1'),
    (r'^(Sofa .*|Pillow \d)$', 'Sofa'),
]
CATEGORY = {'Site': 'Structure', 'Structure': 'Structure', 'Ceiling': 'Structure', 'Floors': 'Floors',
            'Fitout': 'Kitchen and bathrooms', 'Furniture': 'Furniture'}
DOORS = {o['door_id']: {'label': o['door_label'], 'close': o['close_angle'],
                        'hinge': Vector((o['hinge_x'], -o['hinge_z'], 0.0))} for o in src if 'door_id' in o}
groups, leaves = {}, {}
for o in src:
    coll = o.users_collection[0].name
    base = re.sub(r'\.\d{3}$', '', o.name)
    if coll == 'Structure':
        g = 'Walls'
    elif coll == 'Site':
        g = 'Floor slab'
    elif coll == 'Ceiling':
        g = 'Ceiling'
    elif 'door_id' in o or 'door_part' in o:
        did = o.get('door_id') or o.get('door_part')
        g = f"{DOORS[did]['label']} leaf"
        if 'door_id' in o:
            leaves[g] = did
    else:
        g = next((re.sub(p, r, base) for p, r in RULES if re.match(p, base)), base)
    cat = CATEGORY.get(coll) or ('Doors' if 'door' in g.lower() else 'Windows and loggia')
    groups.setdefault((cat, g), []).append(o)


def clean(ob, dissolve):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    if dissolve:
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.5), verts=bm.verts[:], edges=bm.edges[:],
                                 delimit={'MATERIAL'})
    bad = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    vol = bm.calc_volume()
    bm.to_mesh(ob.data)
    bm.free()
    return bad, vol


def volume(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    v = bm.calc_volume()
    bm.free()
    return v


def union(objs):
    """Exact boolean union: one closed solid, no faces buried inside it."""
    base, rest = objs[0], objs[1:]
    # Snap to 0.1 mm first: boxes built about their own centres meet 1e-7 m apart in float32,
    # and the exact solver would keep both faces of every such joint
    for o in objs:
        for v in o.data.vertices:
            v.co = [round(c, 4) for c in v.co]
    before = sum(volume(o) for o in objs)
    if rest:
        tmp = bpy.data.collections.new('_union')
        scene.collection.children.link(tmp)
        for o in rest:
            tmp.objects.link(o)
        mod = base.modifiers.new('Union', 'BOOLEAN')
        mod.operation, mod.solver, mod.operand_type, mod.collection = 'UNION', 'EXACT', 'COLLECTION', tmp
        select([base])
        bpy.ops.object.modifier_apply(modifier=mod.name)
        for o in rest:
            bpy.data.objects.remove(o)
        bpy.data.collections.remove(tmp)
    bad, after = clean(base, dissolve=True)
    return base, before, after, bad


final = []
for (cat, g), objs in groups.items():
    if g == 'Walls' or g.startswith('Floor 0'):
        ob, before, after, bad = union(objs)
        print(f'UNION {g:28s} {len(objs):3d} boxes  volume {before:8.4f} -> {after:8.4f} m3  '
              f'{len(ob.data.polygons)} faces  non-manifold edges {bad}')
    else:
        ob = next((o for o in objs if 'door_id' in o), objs[0])
        if len(objs) > 1:
            select(objs, ob)
            bpy.ops.object.join()
    final.append((cat, g, ob))

# The sales sheet as a reference plane under the slab, where the viewer lays it
me = bpy.data.meshes.new('Reference plan')
x0, y0, x1, y1 = X(CROP[0]), Y(CROP[1]), X(CROP[2]), Y(CROP[3])
me.from_pydata([(x0, y1, -0.26), (x1, y1, -0.26), (x1, y0, -0.26), (x0, y0, -0.26)], [], [(0, 1, 2, 3)])
uv = me.uv_layers.new(name='UVMap')
for loop, co in zip(uv.data, ((0, 0), (1, 0), (1, 1), (0, 1))):
    loop.uv = co
ref_mat = bpy.data.materials.new('Reference plan')
ref_mat.use_nodes = True
p = ref_mat.node_tree.nodes['Principled BSDF']
p.inputs['Roughness'].default_value = 1.0
tex = ref_mat.node_tree.nodes.new('ShaderNodeTexImage')
tex.image = bpy.data.images.load(os.path.join(HERE, 'plan-sheet.png'))
ref_mat.node_tree.links.new(tex.outputs['Color'], p.inputs['Base Color'])
me.materials.append(ref_mat)
ref = bpy.data.objects.new('Reference plan', me)
scene.collection.objects.link(ref)
final.append(('Reference', 'Reference plan (hide for renders)', ref))


# ---------------------------------------------------------------- UVs, pivots, names, hierarchy
def box_uvs(ob):
    """World-space box mapping in metres, unmirrored on every side; floor maps at their repeat."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    layer = bm.loops.layers.uv.verify()
    mats = [m.name if m else '' for m in ob.data.materials]
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        su, sv = PERIOD.get(mats[f.material_index] if f.material_index < len(mats) else '', (1.0, 1.0))
        for loop in f.loops:
            c = loop.vert.co
            if ax == 2:
                u, v = c.x, (c.y if n.z > 0 else -c.y)
            elif ax == 0:
                u, v = (c.y if n.x > 0 else -c.y), c.z
            else:
                u, v = (-c.x if n.y > 0 else c.x), c.z
            loop[layer].uv = (u / su, v / sv)
    bm.to_mesh(ob.data)
    bm.free()


def pivot(ob, at):
    ob.data.transform(Matrix.Translation(-at))
    ob.location = at


parents = {}
for cat in ('Structure', 'Floors', 'Doors', 'Windows and loggia', 'Kitchen and bathrooms', 'Furniture', 'Reference'):
    e = bpy.data.objects.new(cat, None)
    scene.collection.objects.link(e)
    parents[cat] = e

bounds = {}
for cat, g, ob in final:
    if ob is not ref:
        box_uvs(ob)
    vs = [v.co for v in ob.data.vertices]
    bounds[g] = (Vector([min(v[i] for v in vs) for i in range(3)]), Vector([max(v[i] for v in vs) for i in range(3)]))

expect = {}
for cat, g, ob in final:
    lo, hi = bounds[g]
    for k in list(ob.keys()):
        del ob[k]
    did = leaves.get(g)
    if did:
        d = DOORS[did]
        # check: the open leaf turned by close_angle about the hinge lands in its frame's opening
        c = (lo + hi) / 2 - d['hinge']
        a = d['close']
        shut = d['hinge'] + Vector((c.x * math.cos(a) - c.y * math.sin(a), c.x * math.sin(a) + c.y * math.cos(a), 0))
        flo, fhi = bounds[g[:-len(' leaf')] + ' frame']
        ok = flo.x - 0.01 <= shut.x <= fhi.x + 0.01 and flo.y - 0.01 <= shut.y <= fhi.y + 0.01
        print(f'DOOR {did:9s} hinge {d["hinge"].x:7.3f} {d["hinge"].y:7.3f}  close {math.degrees(a):7.1f} deg  '
              f'shut centre {"in" if ok else "OUTSIDE"} its frame')
        pivot(ob, d['hinge'])
        ob['close_angle_deg'] = round(math.degrees(a), 1)
    elif ob is not ref:
        pivot(ob, Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z)))
    name = g.replace('Loggia door, ', 'Loggia door ')
    ob.name = ob.data.name = name
    ob.parent = parents[cat]
    expect[name] = {'min': list(lo), 'max': list(hi), 'verts': len(ob.data.vertices), 'faces': len(ob.data.polygons),
                    'materials': [m.name for m in ob.data.materials], 'parent': cat}
for o in list(bpy.data.objects):
    if o.type == 'MESH' and o.parent is None:
        print('STRAY', o.name)
print('OBJECTS', len(final), 'MATERIALS', sorted({m for e in expect.values() for m in e['materials']}))

# ---------------------------------------------------------------- write
fbx = os.path.join(OUT, NAME + '.fbx')
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=False, object_types={'EMPTY', 'MESH'},
                         use_mesh_modifiers=True, mesh_smooth_type='FACE', use_custom_props=True,
                         add_leaf_bones=False, bake_anim=False, path_mode='COPY', embed_textures=True,
                         axis_forward='Y', axis_up='Z', apply_unit_scale=True,
                         apply_scale_options='FBX_SCALE_NONE', bake_space_transform=True)
print('EXPORTED', fbx, os.path.getsize(fbx))
# The maps are embedded; loose copies where the FBX points, for importers set not to extract media
fbm = os.path.join(OUT, NAME + '.fbm')
os.makedirs(fbm, exist_ok=True)
for img in bpy.data.images:
    if img.filepath:
        shutil.copy(bpy.path.abspath(img.filepath), fbm)
obj = os.path.join(OUT, 'obj', NAME + '.obj')
bpy.ops.wm.obj_export(filepath=obj, export_selected_objects=False, forward_axis='NEGATIVE_Z', up_axis='Y',
                      apply_modifiers=True, export_uv=True, export_normals=True, export_materials=True,
                      path_mode='COPY', export_object_groups=False)
print('EXPORTED', obj, os.path.getsize(obj))
if '--expect' in ARGS:
    with open(ARGS[ARGS.index('--expect') + 1], 'w') as f:
        json.dump(expect, f, indent=1)
