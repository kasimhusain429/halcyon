"""Encode the v2 bakes for the browser (system Python with Pillow, after bake_rt.py export).

    python blender/encode_rt.py

blender/rt/bake/<A_name>_color.png (RGB colour, roughness in alpha)  -> public/rt/<A_name>_color.webp
blender/rt/bake/<A_name>_light.png (sqrt(light / 4), denoised)        -> public/rt/<A_name>_light.webp
plus half-size copies (*_h.webp) for phones, where texture memory is tight.
"""
import glob
import json
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'rt', 'bake')
OUT = os.path.normpath(os.path.join(HERE, '..', 'public', 'rt'))


def save(im, path, quality, alpha):
    im.save(path, 'WEBP', quality=quality, alpha_quality=90 if alpha else 100, method=5)
    return os.path.getsize(path)


def main():
    os.makedirs(OUT, exist_ok=True)
    total = {'full': 0, 'half': 0}
    for path in sorted(glob.glob(os.path.join(SRC, 'A_*_color.png')) + glob.glob(os.path.join(SRC, 'A_*_light.png'))):
        name = os.path.splitext(os.path.basename(path))[0]
        im = Image.open(path)
        alpha = name.endswith('_color')
        im = im.convert('RGBA' if alpha else 'RGB')
        q = 86 if alpha else 92
        total['full'] += save(im, os.path.join(OUT, f'{name}.webp'), q, alpha)
        half = im.resize((max(1, im.width // 2), max(1, im.height // 2)), Image.LANCZOS)
        total['half'] += save(half, os.path.join(OUT, f'{name}_h.webp'), q, alpha)
    print(json.dumps({k: round(v / 1e6, 2) for k, v in total.items()}))


if __name__ == '__main__':
    main()
