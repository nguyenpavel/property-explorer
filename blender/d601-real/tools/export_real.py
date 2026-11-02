"""Export d601-real.blend to d601-real.json (glTF, buffer folded in as base64) with its textures as files in tex/.

Run:  blender -b d601-real.blend -P tools/export_real.py

Like ../export_web.py, but the pack textures stay separate JPEG/PNG files, fetched by the
viewer from the artifact; floors get world-space UVs for the viewer's own plank and tile maps.
"""
import base64, bpy, json, os, shutil

SKIP = {'Plan labels', 'Reference plan', 'Cameras & Lights'}
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
        ob['group'] = coll.name
        ob.select_set(True)

BASE = os.path.splitext(bpy.data.filepath)[0]
DIR = os.path.dirname(BASE)
shutil.rmtree(os.path.join(DIR, 'tex'), ignore_errors=True)
gltf = BASE + '.gltf'
bpy.ops.export_scene.gltf(filepath=gltf, export_format='GLTF_SEPARATE', use_selection=True, export_apply=True,
                          export_yup=True, export_extras=True, export_cameras=False, export_lights=False,
                          export_texture_dir='tex', export_image_format='AUTO', export_jpeg_quality=85)
doc = json.load(open(gltf, encoding='utf-8'))
for buf in doc['buffers']:
    bin_path = os.path.join(DIR, buf['uri'])
    with open(bin_path, 'rb') as f:
        buf['uri'] = 'data:application/octet-stream;base64,' + base64.b64encode(f.read()).decode()
    os.remove(bin_path)
os.remove(gltf)
out = BASE + '.json'
with open(out, 'w', encoding='utf-8') as f:
    json.dump(doc, f, separators=(',', ':'))
tex = os.path.join(DIR, 'tex')
n = len(os.listdir(tex)); size = sum(os.path.getsize(os.path.join(tex, x)) for x in os.listdir(tex))
print('EXPORTED', out, os.path.getsize(out), '| images', len(doc.get('images', [])), 'files', n, size)
