"""Export a .blend to <name>.json (embedded glTF) beside it, for the web viewers.

Run:  blender -b studio-plan/studio-plan.blend -P export_web.py
      blender -b house-d1-s14/house-d1-s14.blend -P export_web.py

Artifacts don't serve .glb, so the model ships as text glTF under a .json name;
three.js's GLTFLoader reads it either way.

Floors get world-space UVs in metres so the viewer can tile its own plank and
tile textures (the Blender brick shaders don't survive glTF). Labels, cameras,
the reference image and the SDK ceilings stay out of the export.
"""
import base64, bpy, json, os

SKIP = {'Plan labels', 'SDK ceilings 2.35 m', 'Reference plan', 'Cameras & Lights'}
TILED = {'Oak planks', 'Hall tiles', 'Bath floor tiles', 'Decking', 'Paving'}

bpy.ops.object.select_all(action='DESELECT')
for coll in bpy.data.collections:
    if coll.name in SKIP:
        continue
    for ob in coll.objects:
        if ob.type != 'MESH':
            continue
        me = ob.data
        if any(m and m.name in TILED for m in me.materials) and not me.uv_layers:
            uv = me.uv_layers.new(name='UVMap')
            for loop in me.loops:
                co = ob.matrix_world @ me.vertices[loop.vertex_index].co
                uv.data[loop.index].uv = (co.x, co.y)
        ob['group'] = coll.name  # build-up order in viewer-build.html (glTF extras)
        ob.select_set(True)

BASE = os.path.splitext(bpy.data.filepath)[0]
gltf = BASE + '.gltf'
bpy.ops.export_scene.gltf(filepath=gltf, export_format='GLTF_SEPARATE', use_selection=True,
                          export_apply=True, export_yup=True, export_extras=True, export_cameras=False, export_lights=False)
# Fold the .bin buffer into the JSON as a data URI so the model is one file
doc = json.load(open(gltf, encoding='utf-8'))
for buf in doc['buffers']:
    bin_path = os.path.join(os.path.dirname(gltf), buf['uri'])
    with open(bin_path, 'rb') as f:
        buf['uri'] = 'data:application/octet-stream;base64,' + base64.b64encode(f.read()).decode()
    os.remove(bin_path)
os.remove(gltf)
out = BASE + '.json'
with open(out, 'w', encoding='utf-8') as f:
    json.dump(doc, f, separators=(',', ':'))
print('EXPORTED', out, os.path.getsize(out))
