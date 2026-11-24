"""HALCYON residence — camera choreography.

Each shot is a Catmull-Rom path for the camera position and its look-at target,
re-parameterised by arc length with a per-control-point "density" (frames per metre
weighting) so the walkthrough slows where the scene changes fastest.
Shots are laid out back-to-back on one timeline; markers bind the active camera.
"""
import bpy, math, json, os
from mathutils import Vector
from hlib import coll

FPS = 24

SHOTS = [
    dict(name='arrival', frames=176,
         # hero view -> crane up and arc over the lake (aerial three-quarter of pool,
         # cantilever and gable) -> low sweep across the water to the dock -> up the
         # steps -> through the pivot door -> turn towards the great room
         pts=[(3.0, -58.0, 6.2), (12.0, -52.0, 12.0), (30.0, -36.0, 19.0), (28.0, -18.0, 12.0),
              (16.0, -22.0, 5.0), (3.0, -20.0, 2.6), (0.4, -12.0, 1.85), (0.22, -5.0, 1.72),
              (0.2, -1.0, 1.68), (0.2, 2.2, 1.66), (0.1, 4.6, 1.66), (-0.4, 6.3, 1.64)],
         tgt=[(2.0, 8.0, 6.6), (3.0, 5.0, 5.0), (5.0, 2.0, 2.0), (4.0, 0.0, 2.5),
              (1.5, 2.0, 2.4), (0.5, 4.0, 2.4), (0.3, 4.0, 2.4), (0.2, 4.0, 1.95),
              (0.2, 6.0, 1.9), (0.1, 8.0, 2.4), (-0.6, 10.0, 3.0), (-4.5, 8.6, 2.5)],
         lens=[32, 30, 28, 28, 28, 28, 26, 26, 24, 22, 22, 22],
         dens=[1.5, 0.7, 0.55, 0.6, 0.8, 1.0, 1.2, 1.8, 3.4, 5.5, 5.0, 5.0],
         title='The Arrival'),
    dict(name='great', frames=60,
         pts=[(-2.3, 7.4, 1.62), (-3.9, 7.0, 1.64), (-5.6, 6.3, 1.72), (-7.0, 5.4, 1.86)],
         tgt=[(-12.0, 7.6, 2.0), (-13.6, 6.6, 2.2), (-13.4, 3.4, 2.6), (-10.6, -1.2, 3.0)],
         lens=[22, 21, 20, 20],
         dens=[1, 1, 1, 1],
         title='The Great Room'),
    dict(name='kitchen', frames=52,
         pts=[(3.7, 4.0, 1.62), (5.6, 4.9, 1.64), (7.8, 5.3, 1.66), (10.2, 5.4, 1.7)],
         tgt=[(8.6, 9.4, 1.1), (9.6, 9.8, 1.15), (11.6, 10.0, 1.3), (13.8, 9.6, 1.5)],
         lens=[22, 22, 22, 22],
         dens=[1, 1, 1, 1],
         title='The Kitchen'),
    dict(name='study', frames=72,
         pts=[(15.0, 4.6, 1.62), (15.9, 6.8, 1.52), (16.4, 8.7, 1.3), (16.45, 9.9, 1.05), (16.45, 10.42, 0.95)],
         tgt=[(16.9, 12.6, 1.6), (16.6, 12.4, 1.35), (16.47, 11.2, 0.95), (16.45, 10.92, 0.89), (16.45, 10.917, 0.887)],
         lens=[22, 24, 28, 34, 40],
         dens=[1, 1, 1.2, 2.2, 3.0],
         title='The Study'),
]

def catmull(ps, u):
    """Uniform Catmull-Rom through points ps, u in [0,1]."""
    n = len(ps) - 1
    x = min(max(u, 0.0), 1.0) * n
    i = min(int(x), n - 1)
    t = x - i
    p0 = ps[max(i - 1, 0)]; p1 = ps[i]; p2 = ps[i + 1]; p3 = ps[min(i + 2, n)]
    t2, t3 = t * t, t * t * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)

def lerp_list(vals, u):
    n = len(vals) - 1
    x = min(max(u, 0.0), 1.0) * n
    i = min(int(x), n - 1)
    t = x - i
    t = t * t * (3 - 2 * t)
    return vals[i] * (1 - t) + vals[i + 1] * t

def bake_shot(shot, start_frame, c):
    P = [Vector(p) for p in shot['pts']]
    T = [Vector(p) for p in shot['tgt']]
    # dense sampling for arc length weighted by density
    S = 2000
    acc = [0.0]
    prev = catmull(P, 0.0)
    for k in range(1, S + 1):
        u = k / S
        cur = catmull(P, u)
        acc.append(acc[-1] + (cur - prev).length * lerp_list(shot['dens'], u))
        prev = cur
    total = acc[-1]
    nf = shot['frames']
    cam = bpy.data.cameras.new(f"CAM_{shot['name']}")
    cam.sensor_width = 36
    cam.clip_start = 0.03
    cam.clip_end = 20000
    ob = bpy.data.objects.new(f"CAM_{shot['name']}", cam)
    c.objects.link(ob)
    keys = []
    j = 0
    prev_eul = None
    for f in range(nf):
        # ease in/out on the weighted length
        g = f / (nf - 1)
        g = 0.5 - 0.5 * math.cos(math.pi * g) if shot.get('ease', True) else g
        target_len = g * total
        while j < S and acc[j + 1] < target_len:
            j += 1
        seg = acc[j + 1] - acc[j] if j < S else 1
        u = (j + (target_len - acc[j]) / seg) / S if seg > 0 else j / S
        pos = catmull(P, u)
        tgt = catmull(T, u)
        lens = lerp_list(shot['lens'], u)
        fr = start_frame + f
        ob.location = pos
        q = (tgt - pos).to_track_quat('-Z', 'Y')
        eul = q.to_euler('XYZ', prev_eul) if prev_eul is not None else q.to_euler('XYZ')
        prev_eul = eul
        ob.rotation_euler = eul
        cam.lens = lens
        ob.keyframe_insert('location', frame=fr)
        ob.keyframe_insert('rotation_euler', frame=fr)
        cam.keyframe_insert('lens', frame=fr)
        keys.append(dict(f=fr, pos=tuple(round(v, 3) for v in pos), u=round(u, 4)))
    return ob, keys

def animate_door(door, arrival_keys):
    """Pivot door swings in as the camera approaches (y from -5.5 to -0.8)."""
    def frame_at(y):
        for k in arrival_keys:
            if k['pos'][1] >= y:
                return k['f']
        return arrival_keys[-1]['f']
    f0, f1 = frame_at(-9.0), frame_at(-1.4)
    door.rotation_euler = (0, 0, 0)
    door.keyframe_insert('rotation_euler', index=2, frame=f0)
    door.rotation_euler = (0, 0, math.radians(84))
    door.keyframe_insert('rotation_euler', index=2, frame=f1)
    return f0, f1

EXPOSURE = dict(arrival_out=0.35, arrival_in=0.95, great=0.55, kitchen=1.0, study=0.85)

def key_exposure(s, frame, value):
    s.view_settings.exposure = value
    s.view_settings.keyframe_insert('exposure', frame=frame)

def build(door=None):
    s = bpy.context.scene
    c = coll('Cameras')
    s.render.fps = FPS
    s.timeline_markers.clear()
    start = 1
    meta = []
    arrival_keys = None
    for shot in SHOTS:
        ob, keys = bake_shot(shot, start, c)
        m = s.timeline_markers.new(shot['name'], frame=start)
        m.camera = ob
        meta.append(dict(name=shot['name'], title=shot['title'], start=start, end=start + shot['frames'] - 1, frames=shot['frames']))
        if shot['name'] == 'arrival':
            arrival_keys = keys
        start += shot['frames']
    s.frame_start = 1
    s.frame_end = start - 1
    s.camera = bpy.data.objects['CAM_arrival']
    if door is None:
        door = bpy.data.objects.get('Door_Pivot')
    if door is not None and arrival_keys:
        meta.append(dict(door=animate_door(door, arrival_keys)))
    # exposure: the eye adapts through the door; each room holds its own key
    if arrival_keys:
        def frame_at(y):
            for k in arrival_keys:
                if k['pos'][1] >= y:
                    return k['f']
            return arrival_keys[-1]['f']
        key_exposure(s, 1, EXPOSURE['arrival_out'])
        key_exposure(s, frame_at(-1.0), EXPOSURE['arrival_out'])
        key_exposure(s, frame_at(3.2), EXPOSURE['arrival_in'])
        key_exposure(s, arrival_keys[-1]['f'], EXPOSURE['arrival_in'])
    for m_ in meta:
        if m_.get('name') in ('great', 'kitchen', 'study'):
            key_exposure(s, m_['start'], EXPOSURE[m_['name']])
            key_exposure(s, m_['end'], EXPOSURE[m_['name']])
    out = os.path.join(os.path.dirname(__file__), 'shots.json')
    with open(out, 'w') as fh:
        json.dump(meta, fh, indent=1)
    return meta
