"""Render all prepared assets on a grid (front = -Y towards the camera) to check materials, scale and facing.
Run:  blender -b --factory-startup -P contact_sheet.py -- out.png"""
import bpy, glob, math, os, sys
from mathutils import Vector
out = sys.argv[sys.argv.index('--') + 1]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
files = sorted(glob.glob(os.path.join(ROOT, 'assets', '*.blend')))
x = 0.0
for i, f in enumerate(files):
    with bpy.data.libraries.load(f, link=False) as (src, dst):
        dst.objects = src.objects
    for ob in dst.objects:
        scene.collection.objects.link(ob)
        vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
        lo = [min(v[k] for v in vs) for k in range(3)]; hi = [max(v[k] for v in vs) for k in range(3)]
        w = hi[0] - lo[0]
        row = i % 2
        ob.location = (x + w / 2, row * 4.0, 0)
        print('SIZE', ob.name, [round(hi[k] - lo[k], 3) for k in range(3)], 'tris', sum(len(p.vertices) - 2 for p in ob.data.polygons))
        t = bpy.data.curves.new(ob.name, 'FONT'); t.body = ob.name; t.size = 0.22
        to = bpy.data.objects.new(ob.name + '_label', t); to.location = (x, row * 4.0 - 1.0, 0); scene.collection.objects.link(to)
        if row == 1: x += max(w, 1.3) + 0.4
floor = bpy.data.meshes.new('floor'); floor.from_pydata([(-2, -3, 0), (x + 2, -3, 0), (x + 2, 7, 0), (-2, 7, 0)], [], [(0, 1, 2, 3)])
scene.collection.objects.link(bpy.data.objects.new('floor', floor))
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 3; sun.rotation_euler = (math.radians(50), 0, math.radians(20)); scene.collection.objects.link(sun)
w = scene.world = bpy.data.worlds.new('w'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); cam.data.type = 'ORTHO'; cam.data.ortho_scale = x + 3
cam.location = (x / 2, -14, 9); cam.rotation_euler = (Vector((x / 2, 2, 0.6)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
scene.collection.objects.link(cam); scene.camera = cam
scene.render.engine = 'BLENDER_EEVEE_NEXT'; scene.eevee.taa_render_samples = 16
scene.render.resolution_x, scene.render.resolution_y = 2400, 1100
scene.render.filepath = os.path.abspath(out)
bpy.ops.render.render(write_still=True)
