"""Measure USD assets: metres bbox (x, y, z with z up), triangles, materials and their texture inputs.
Run:  blender -b --factory-startup -P usd_probe.py -- list.txt   (one .usd path per line)"""
import sys, os
from pxr import Usd, UsdGeom, UsdShade, Sdf
paths = [l.strip() for l in open(sys.argv[sys.argv.index('--') + 1], encoding='utf-8') if l.strip()]
for p in paths:
    try:
        st = Usd.Stage.Open(p)
    except Exception as e:
        print('FAIL', p, e); continue
    mpu = UsdGeom.GetStageMetersPerUnit(st); up = UsdGeom.GetStageUpAxis(st)
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ['default', 'render'])
    rng = cache.ComputeWorldBound(st.GetPseudoRoot()).ComputeAlignedRange()
    mn, mx = rng.GetMin(), rng.GetMax()
    size = [(mx[i] - mn[i]) * mpu for i in range(3)]
    if up == 'Y': size = [size[0], size[2], size[1]]
    tris = 0; meshes = 0; mats = set(); tex = set()
    for prim in st.Traverse():
        if prim.IsA(UsdGeom.Mesh):
            meshes += 1
            fvc = UsdGeom.Mesh(prim).GetFaceVertexCountsAttr().Get() or []
            tris += sum(max(0, c - 2) for c in fvc)
        if prim.IsA(UsdShade.Material):
            mats.add(prim.GetName())
        if prim.IsA(UsdShade.Shader):
            sh = UsdShade.Shader(prim)
            for inp in sh.GetInputs():
                v = inp.Get()
                if isinstance(v, Sdf.AssetPath) and v.path: tex.add(inp.GetBaseName() + '=' + os.path.basename(v.path))
            sa = sh.GetSourceAsset('mdl') if hasattr(sh, 'GetSourceAsset') else None
            if sa: tex.add('MDL=' + os.path.basename(sa.path))
    print(f'ASSET {os.path.basename(p)} | {size[0]:.2f} x {size[1]:.2f} x {size[2]:.2f} m | up {up} mpu {mpu} | meshes {meshes} tris {tris} | mats {len(mats)}')
    print('   TEX', ' '.join(sorted(tex))[:600])
