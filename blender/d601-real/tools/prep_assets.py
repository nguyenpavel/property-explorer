"""Turn each manifest asset into a light, glTF-ready Blender asset: assets/<name>.blend.

Imports the USD, scales it to metres, rebuilds every OmniPBR/OmniSurface/OmniGlass/SimPBR
material as a Principled BSDF with the downscaled textures from cache/tex, decimates to the
manifest's triangle budget, joins the meshes into one object and puts its origin at the
middle of its footprint, on the floor.

Run:  blender -b --factory-startup -P prep_assets.py -- [asset ...]
"""
import bpy, json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
man = json.load(open(os.path.join(HERE, 'manifest.json'), encoding='utf-8'))
mats = json.load(open(os.path.join(HERE, 'materials.json'), encoding='utf-8'))
texcache = json.load(open(os.path.join(HERE, 'texcache.json'), encoding='utf-8'))
TEX = os.path.join(ROOT, 'cache', 'tex')
OUT = os.path.join(ROOT, 'assets')
os.makedirs(OUT, exist_ok=True)
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def cached(inp, role):
    if not isinstance(inp, dict) or not inp.get('asset'):
        return None
    name = texcache.get(inp['asset'], {}).get(role)
    return os.path.join(TEX, name) if name else None


def image_node(nt, path, non_color, x, y):
    n = nt.nodes.new('ShaderNodeTexImage')
    img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = 'Non-Color' if non_color else 'sRGB'
    n.image = img
    n.location = (x, y)
    return n


def build_material(asset, mname, info):
    m = bpy.data.materials.new(f'{asset}:{mname}')
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes['Principled BSDF']
    i = info.get('inputs', {})
    shader = (info.get('sub') or info.get('shader') or '').replace('.mdl', '')
    uv = None
    ts = i.get('texture_scale')
    if isinstance(ts, list) and (abs(ts[0] - 1) > 1e-3 or abs(ts[1] - 1) > 1e-3):
        tc = nt.nodes.new('ShaderNodeTexCoord')
        uv = nt.nodes.new('ShaderNodeMapping')
        uv.inputs['Scale'].default_value = (1 / ts[0], 1 / ts[1], 1)
        nt.links.new(tc.outputs['UV'], uv.inputs['Vector'])

    def tex(path, non_color, y):
        n = image_node(nt, path, non_color, -700, y)
        if uv:
            nt.links.new(uv.outputs['Vector'], n.inputs['Vector'])
        return n

    if shader == 'OmniGlass':
        c = i.get('glass_color', [0.9, 0.95, 1.0])
        p.inputs['Base Color'].default_value = (*c[:3], 1)
        p.inputs['Roughness'].default_value = i.get('frosting_roughness', 0.05)
        p.inputs['Alpha'].default_value = 0.25
        m.surface_render_method = 'BLENDED'
        return m
    if shader == 'OmniSurface':
        col = cached(i.get('diffuse_reflection_color_image'), 'color')
        if col:
            nt.links.new(tex(col, False, 300).outputs['Color'], p.inputs['Base Color'])
        else:
            c = i.get('diffuse_reflection_color', [0.8, 0.8, 0.8])
            p.inputs['Base Color'].default_value = (*c[:3], 1)
        rough = cached(i.get('specular_reflection_roughness_image'), 'data')
        if rough:
            nt.links.new(tex(rough, True, 0).outputs['Color'], p.inputs['Roughness'])
        else:
            p.inputs['Roughness'].default_value = i.get('specular_reflection_roughness', 0.5)
        p.inputs['Metallic'].default_value = i.get('metalness', 0.0)
        return m
    # OmniPBR and SimPBR share their inputs
    col = cached(i.get('diffuse_texture'), 'color')
    if col:
        t = tex(col, False, 300)
        tint = i.get('diffuse_tint')
        if isinstance(tint, list) and min(tint[:3]) < 0.99:
            mix = nt.nodes.new('ShaderNodeMix')
            mix.data_type, mix.blend_type = 'RGBA', 'MULTIPLY'
            mix.inputs['Factor'].default_value = 1.0
            nt.links.new(t.outputs['Color'], mix.inputs[6])
            mix.inputs[7].default_value = (*tint[:3], 1)
            nt.links.new(mix.outputs[2], p.inputs['Base Color'])
        else:
            nt.links.new(t.outputs['Color'], p.inputs['Base Color'])
    else:
        c = i.get('diffuse_color_constant', [0.2, 0.2, 0.2])
        p.inputs['Base Color'].default_value = (*c[:3], 1)
    orm = cached(i.get('ORM_texture'), 'data') if i.get('enable_ORM_texture', True) else None
    rough = cached(i.get('reflectionroughness_texture'), 'data')
    metal = cached(i.get('metallic_texture'), 'data')
    if orm:
        t = tex(orm, True, 0)
        sep = nt.nodes.new('ShaderNodeSeparateColor')
        sep.location = (-350, 0)
        nt.links.new(t.outputs['Color'], sep.inputs['Color'])
        nt.links.new(sep.outputs['Green'], p.inputs['Roughness'])
        nt.links.new(sep.outputs['Blue'], p.inputs['Metallic'])
    else:
        if rough and i.get('reflection_roughness_texture_influence', 1.0) >= 0.5:
            nt.links.new(tex(rough, True, 0).outputs['Color'], p.inputs['Roughness'])
        else:
            p.inputs['Roughness'].default_value = i.get('reflection_roughness_constant', 0.5)
        if metal and i.get('metallic_texture_influence', 1.0) >= 0.5:
            nt.links.new(tex(metal, True, -250).outputs['Color'], p.inputs['Metallic'])
        else:
            p.inputs['Metallic'].default_value = i.get('metallic_constant', 0.0)
    nrm = cached(i.get('normalmap_texture'), 'normal')
    if nrm:
        t = tex(nrm, True, -500)
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nm.location = (-350, -500)
        nm.inputs['Strength'].default_value = min(1.0, i.get('bump_factor', 1.0))
        nt.links.new(t.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], p.inputs['Normal'])
    return m


def prep(asset):
    a = man['assets'][asset]
    info = mats[asset]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.usd_import(filepath=info['usd'], import_cameras=False, import_lights=False, import_curves=False,
                          support_scene_instancing=False, import_usd_preview=False, import_visible_only=True,
                          import_guide=False, import_proxy=False, import_render=True)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    for o in list(bpy.data.objects):
        if o.type != 'MESH':
            continue
        o.data = o.data.copy() if o.data.users > 1 else o.data
    # bake world transforms into the meshes, drop the empties
    for o in meshes:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
    for o in list(bpy.data.objects):
        if o.type != 'MESH':
            bpy.data.objects.remove(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # materials: replace each imported (MDL-less) material with a rebuilt one
    built = {}
    for o in meshes:
        for slot in o.material_slots:
            if not slot.material:
                continue
            key = re.sub(r'\.\d{3}$', '', slot.material.name)
            src = info['materials'].get(key) or next((v for k, v in info['materials'].items() if k.lower() == key.lower()), None)
            if src is None:
                print('  no USD material for', key)
                continue
            if key not in built:
                built[key] = build_material(asset, key, src)
            slot.material = built[key]
    # decimate to the budget
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes)
    ratio = a['tris'] / tris if tris else 1
    if ratio < 0.98:
        for o in meshes:
            mod = o.modifiers.new('Decimate', 'DECIMATE')
            mod.decimate_type, mod.ratio, mod.use_collapse_triangulate = 'COLLAPSE', ratio, True
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.modifier_apply(modifier=mod.name)
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = ob.data.name = asset
    if ratio < 0.98:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    # metres, origin at the footprint centre on the floor
    vs = [v.co for v in ob.data.vertices]
    lo = [min(v[k] for v in vs) for k in range(3)]
    hi = [max(v[k] for v in vs) for k in range(3)]
    k = info['size_m'][2] / (hi[2] - lo[2]) if hi[2] > lo[2] else 0.01
    k = 0.01 if abs(k - 0.01) < 0.002 else (1.0 if abs(k - 1) < 0.2 else k)
    c = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2])
    for v in ob.data.vertices:
        v.co = ((v.co[0] - c[0]) * k, (v.co[1] - c[1]) * k, (v.co[2] - c[2]) * k)
    ob.data.update()
    dims = [round(d, 3) for d in ob.dimensions]
    nt = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    ob['asset_size'] = dims
    dst = os.path.join(OUT, f'{asset}.blend')
    bpy.data.libraries.write(dst, {ob}, fake_user=True, path_remap='ABSOLUTE')
    print(f'ASSET {asset}: {tris} -> {nt} tris, {dims} m, {len(built)} materials -> {os.path.basename(dst)}')


todo = ARGS or [k for k, v in man['assets'].items() if not v.get('materials_only')]
for asset in todo:
    try:
        prep(asset)
    except Exception as e:
        import traceback; traceback.print_exc()
        print('FAILED', asset, e)
