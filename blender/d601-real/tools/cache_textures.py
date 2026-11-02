"""Downscale every texture the materials use into cache/tex (JPEG, PNG only where alpha is real).
Writes texcache.json: source path -> {role: cached file}. Run with system Python (PIL)."""
import hashlib, json, os, sys
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
here = os.path.dirname(os.path.abspath(__file__))
mats = json.load(open(os.path.join(here, 'materials.json'), encoding='utf-8'))
man = json.load(open(os.path.join(here, 'manifest.json'), encoding='utf-8'))
out_dir = os.path.join(here, '..', 'cache', 'tex'); os.makedirs(out_dir, exist_ok=True)
ROLE = {'diffuse_texture': 'color', 'diffuse_reflection_color_image': 'color', 'glass_color_texture': 'color',
        'normalmap_texture': 'normal', 'coat_normal_image': None,
        'reflectionroughness_texture': 'data', 'metallic_texture': 'data', 'ORM_texture': 'data',
        'specular_reflection_roughness_image': 'data', 'emissive_mask_texture': None, 'reflection_color_texture': None}
cache = {}
total = 0
for asset, a in mats.items():
    big = man['assets'][asset]['tex']
    for mname, m in a['materials'].items():
        for key, v in m['inputs'].items():
            if not isinstance(v, dict) or key not in ROLE or ROLE[key] is None:
                continue
            src = v['asset']; role = ROLE[key]
            if not os.path.exists(src):
                print('MISSING', asset, mname, key, src); continue
            limit = big if role == 'color' else min(512, big)
            tag = hashlib.md5(src.lower().encode()).hexdigest()[:6]
            base = os.path.splitext(os.path.basename(src))[0]
            im = Image.open(src)
            alpha = False
            if role == 'color' and im.mode in ('RGBA', 'LA', 'P'):
                im = im.convert('RGBA'); alpha = im.getchannel('A').getextrema()[0] < 250
            ext = '.png' if alpha else '.jpg'
            name = f'{base}_{tag}_{limit}{ext}'
            dst = os.path.join(out_dir, name)
            if not os.path.exists(dst):
                if im.mode in ('I;16', 'I', 'F'):
                    im = im.point(lambda x: x / 256).convert('L')
                im.thumbnail((limit, limit), Image.LANCZOS)
                if alpha: im.save(dst, optimize=True)
                else:
                    im = im.convert('L') if (role == 'data' and key != 'ORM_texture') else im.convert('RGB')
                    im.save(dst, quality=88 if role != 'normal' else 92, optimize=True)
            cache.setdefault(src, {})[role] = name
            total += 1
json.dump(cache, open(os.path.join(here, 'texcache.json'), 'w', encoding='utf-8'), indent=1)
size = sum(os.path.getsize(os.path.join(out_dir, f)) for f in os.listdir(out_dir))
print('cached', len(os.listdir(out_dir)), 'files', round(size / 1e6, 2), 'MB from', total, 'references')
