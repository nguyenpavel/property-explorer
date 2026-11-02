"""Flat top-down check render: walls blue, glass hidden, everything else by material colour.
Run:  blender -b d601.blend -P tools/check_top.py -- out.png"""
import bpy, sys, os
out = sys.argv[sys.argv.index('--') + 1]
scene = bpy.context.scene
scene.camera = bpy.data.objects['Cam plan (top)']
scene.render.engine = 'BLENDER_WORKBENCH'
sh = scene.display.shading
sh.light, sh.color_type = 'FLAT', 'MATERIAL'
sh.show_shadows = sh.show_cavity = False
scene.render.film_transparent = False
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 1866, 2130, 100
bpy.data.materials['Plaster'].diffuse_color = (0.15, 0.35, 0.95, 1)
for m in bpy.data.materials:
    if m.name not in ('Plaster',):
        c = m.diffuse_color
        g = 0.55 + 0.4 * (0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2])
        m.diffuse_color = (g, g, g, 1 if m.name != 'Glass' else 0)
bpy.data.collections['Roof'].hide_render = True
scene.render.filepath = os.path.abspath(out)
bpy.ops.render.render(write_still=True)
print('CHECK', out)
