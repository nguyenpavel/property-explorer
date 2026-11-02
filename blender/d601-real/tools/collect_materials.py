"""Read every material of the manifest's USD assets: MDL shader, constant inputs and resolved texture files.
Writes materials.json beside the manifest.
Run:  blender -b --factory-startup -P collect_materials.py -- manifest.json
"""
import json, os, sys
from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf

manifest_path = sys.argv[sys.argv.index('--') + 1]
man = json.load(open(manifest_path, encoding='utf-8'))
roots = man['roots']


def resolve(p):
    k, rest = p.split('/', 1)
    return os.path.join(roots[k], rest)


def plain(v):
    if isinstance(v, Sdf.AssetPath):
        return {'asset': (v.resolvedPath or v.path).replace('\\', '/')}
    if isinstance(v, (Gf.Vec2f, Gf.Vec3f, Gf.Vec4f, Gf.Vec2d, Gf.Vec3d)):
        return [float(x) for x in v]
    if isinstance(v, (bool, int, float, str)):
        return v
    return None


out = {}
for name, a in man['assets'].items():
    path = resolve(a['usd'])
    st = Usd.Stage.Open(path)
    mpu = UsdGeom.GetStageMetersPerUnit(st)
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ['default', 'render'])
    rng = cache.ComputeWorldBound(st.GetPseudoRoot()).ComputeAlignedRange()
    size = [(rng.GetMax()[i] - rng.GetMin()[i]) * mpu for i in range(3)]
    mats = {}
    for prim in st.Traverse(Usd.TraverseInstanceProxies()):
        if not prim.IsA(UsdShade.Material):
            continue
        info = {'shader': None, 'inputs': {}}
        for child in Usd.PrimRange(prim, Usd.TraverseInstanceProxies()):
            if not child.IsA(UsdShade.Shader):
                continue
            sh = UsdShade.Shader(child)
            sa = sh.GetSourceAsset('mdl')
            ident = sh.GetIdAttr().Get()
            info['shader'] = os.path.basename(sa.path) if sa else (ident or info['shader'])
            sub = sh.GetSourceAssetSubIdentifier('mdl') if sa else None
            if sub: info['sub'] = sub
            for inp in sh.GetInputs():
                v = plain(inp.Get())
                if v is not None:
                    info['inputs'][inp.GetBaseName()] = v
        mats[prim.GetName()] = info
    out[name] = {'usd': path.replace('\\', '/'), 'size_m': size, 'materials': mats}
    print('MATS', name, len(mats), [round(s, 3) for s in size])

dst = os.path.join(os.path.dirname(manifest_path), 'materials.json')
json.dump(out, open(dst, 'w', encoding='utf-8'), indent=1)
print('WROTE', dst)
