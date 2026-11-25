"""Build the HALCYON scene from scratch inside a running Blender.

Usage (Blender Python console / MCP):
    exec(open(r"<repo>/blender/build.py").read())
or headless:
    blender -b -P blender/build.py
"""
import os, sys, importlib, bpy

# exec() leaves __file__ unset: fall back to the repo's blender folder
ROOT = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else r"C:\Users\Admin\Desktop\Project\halcyon\blender"
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
