"""Export e433-2p3.blend to e433-2p3.json (embedded glTF) for the web viewer.

Run:  blender -b e433-2p3.blend -P export_web.py

Artifacts don't serve .glb, so the model ships as text glTF under a .json name;
three.js's GLTFLoader reads it either way.

Floors get world-space UVs in metres so the viewer can tile its own plank and
tile textures (the Blender brick shaders don't survive glTF). Labels, cameras,
the reference plan and the ceilings stay out of the export; the viewer builds
its own ceilings for walk mode.
"""
import base64, bpy, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP = {'Plan labels', 'Reference plan', 'Cameras & Lights', 'Ceilings'}
TILED = {'Oak planks', 'Bath floor tiles', 'Terrace tiles'}

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
        ob['group'] = coll.name  # build-up order in viewer.html (glTF extras)
        ob.select_set(True)

gltf = os.path.join(HERE, 'e433-2p3.gltf')
bpy.ops.export_scene.gltf(filepath=gltf, export_format='GLTF_SEPARATE', use_selection=True,
                          export_apply=True, export_yup=True, export_extras=True, export_cameras=False, export_lights=False)
# Fold the .bin buffer into the JSON as a data URI so the model is one file
doc = json.load(open(gltf, encoding='utf-8'))
for buf in doc['buffers']:
    bin_path = os.path.join(HERE, buf['uri'])
    with open(bin_path, 'rb') as f:
        buf['uri'] = 'data:application/octet-stream;base64,' + base64.b64encode(f.read()).decode()
    os.remove(bin_path)
os.remove(gltf)
out = os.path.join(HERE, 'e433-2p3.json')
with open(out, 'w', encoding='utf-8') as f:
    json.dump(doc, f, separators=(',', ':'))
print('EXPORTED', out, os.path.getsize(out))
