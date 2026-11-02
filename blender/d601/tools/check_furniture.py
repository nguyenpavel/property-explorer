"""Top-down check render by collection: walls blue, fitout and furniture orange, the rest grey.
Run:  blender -b d601.blend -P tools/check_furniture.py -- out.png"""
import bpy, sys, os
out = sys.argv[sys.argv.index('--') + 1]
scene = bpy.context.scene
scene.camera = bpy.data.objects['Cam plan (top)']
scene.render.engine = 'BLENDER_WORKBENCH'
sh = scene.display.shading
sh.light, sh.color_type = 'FLAT', 'OBJECT'
sh.show_shadows = sh.show_cavity = False
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 1866, 2130, 100
COL = {'Structure': (0.15, 0.35, 0.95, 1), 'Fitout': (1.0, 0.6, 0.1, 1), 'Furniture': (1.0, 0.6, 0.1, 1),
       'Doors & Windows': (0.35, 0.35, 0.35, 1), 'Floors': (0.85, 0.85, 0.85, 1)}
for c in bpy.data.collections:
    for ob in c.objects:
        ob.color = COL.get(c.name, (1, 1, 1, 1))
        if ob.name.endswith('glass'): ob.hide_render = True
bpy.data.collections['Roof'].hide_render = True
scene.render.filepath = os.path.abspath(out)
bpy.ops.render.render(write_still=True)
print('CHECK', out)
