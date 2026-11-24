"""Headless renderer for HALCYON.

blender -b halcyon.blend -P render_frames.py -- --frames 1,60,120 --width 960 --samples 24 --out <dir>
blender -b halcyon.blend -P render_frames.py -- --shot arrival --step 2 --offset 0 --width 1600 --samples 48 --out <dir>
"""
import bpy, sys, os, time, json, argparse

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--frames', default='')
ap.add_argument('--shot', default='')
ap.add_argument('--step', type=int, default=1)
ap.add_argument('--offset', type=int, default=0)
ap.add_argument('--width', type=int, default=960)
ap.add_argument('--samples', type=int, default=24)
ap.add_argument('--threshold', type=float, default=0.04)
ap.add_argument('--out', required=True)
ap.add_argument('--skip-existing', action='store_true')
ap.add_argument('--fg', action='store_true', help='foreground pass: far scenery as holdout, transparent sky')
ap.add_argument('--fastgi', type=int, default=-1, help='fast GI AO bounces (enables fast GI)')
ap.add_argument('--bounces', default='', help='diffuse,glossy,transmission')
ap.add_argument('--guiding', action='store_true')
ap.add_argument('--tag', default='')
a = ap.parse_args(argv)

s = bpy.context.scene
cy = s.cycles
if a.fastgi >= 0:
    cy.use_fast_gi = True
    cy.fast_gi_method = 'REPLACE'
    cy.ao_bounces_render = a.fastgi
    if s.world:
        s.world.light_settings.distance = 6.0
if a.bounces:
    d, g, t = (int(x) for x in a.bounces.split(','))
    cy.diffuse_bounces, cy.glossy_bounces, cy.transmission_bounces = d, g, t
    cy.max_bounces = max(d, g, t) + 2
    cy.transparent_max_bounces = 8
if a.guiding:
    cy.use_guiding = True
    cy.use_surface_guiding = True
s.render.resolution_x = a.width
s.render.resolution_y = round(a.width * 9 / 16)
s.render.resolution_percentage = 100
s.cycles.samples = a.samples
s.cycles.adaptive_threshold = a.threshold
s.render.use_persistent_data = True
os.makedirs(a.out, exist_ok=True)

if a.fg:
    s.render.film_transparent = True
    s.render.image_settings.color_mode = 'RGBA'
    # walk collections directly: all_objects is stale for viewport-disabled collections
    def walk(c):
        for ob in c.objects:
            ob.is_holdout = True
        for ch in c.children:
            walk(ch)
    for name in ('Far', 'Forest', 'Terrain'):
        c = bpy.data.collections.get(name)
        if c:
            walk(c)

meta = {m.name: m.frame for m in s.timeline_markers}
order = sorted(meta.items(), key=lambda kv: kv[1])

def shot_of(fr):
    cur = None
    for name, f in order:
        if fr >= f:
            cur = name
    return cur

def cam_for(fr):
    best = None
    for m in s.timeline_markers:
        if m.frame <= fr and (best is None or m.frame > best.frame):
            best = m
    return best.camera if best else s.camera

if a.frames:
    frames = [int(x) for x in a.frames.split(',') if x]
elif a.shot:
    start = meta[a.shot]
    nxt = [f for n, f in order if f > start]
    end = (min(nxt) - 1) if nxt else s.frame_end
    frames = list(range(start + a.offset, end + 1, a.step))
    if end not in frames and a.offset == 0:
        frames.append(end)
else:
    frames = list(range(s.frame_start, s.frame_end + 1, a.step))

log = []
t_all = time.time()
for fr in frames:
    sh = shot_of(fr)
    local = fr - meta[sh] if sh else fr
    path = os.path.join(a.out, f"{sh}_{local:04d}{a.tag}.png" if a.shot or a.frames else f"{fr:04d}.png")
    if a.skip_existing and os.path.exists(path):
        continue
    s.frame_set(fr)
    s.camera = cam_for(fr)
    s.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    dt = time.time() - t
    log.append(dict(frame=fr, shot=sh, local=local, sec=round(dt, 1)))
    print(f"[HALCYON] frame {fr} ({sh} {local}) {dt:.1f}s", flush=True)
with open(os.path.join(a.out, '_log.json'), 'a') as fh:
    fh.write(json.dumps(dict(total=round(time.time() - t_all, 1), frames=log)) + '\n')
print('[HALCYON] done', round(time.time() - t_all, 1), flush=True)
