"""Build the HALCYON scene from scratch inside a running Blender.

Usage (Blender Python console / MCP):
    exec(open(r"<repo>/blender/build.py").read())
"""
import sys, importlib, bpy

ROOT = r"C:\Users\Admin\Desktop\Project\construction\blender"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import hlib, arch
importlib.reload(hlib)
importlib.reload(arch)
mods = {}
for name in ('interior', 'hsite', 'lighting', 'cams'):
    try:
        mods[name] = importlib.reload(importlib.import_module(name))
    except ModuleNotFoundError:
        mods[name] = None

STAGES = globals().get('STAGES', ('arch', 'interior', 'site', 'lighting', 'cams'))

hlib.wipe_scene()
hlib.build_materials()
door = arch.build() if 'arch' in STAGES else None
if mods.get('interior') and 'interior' in STAGES:
    mods['interior'].build()
if mods.get('hsite') and 'site' in STAGES:
    mods['hsite'].build()
if mods.get('lighting') and 'lighting' in STAGES:
    mods['lighting'].build()
if mods.get('cams') and 'cams' in STAGES:
    mods['cams'].build(door)
