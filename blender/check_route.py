"""Check the walkthrough route against the model: the camera may only pass through real openings.

    node blender/route_samples.mjs
    blender -b blender/halcyon.blend -P blender/check_route.py

The browser's camera is a scripted path (components/walkthrough/path.ts), not a physics walk:
nothing stops it entering a wall, so every key has to sit in open space. This samples the path
every few centimetres (route_samples.json) and tests it against every mesh the browser draws:

  * passing through: does any step between two samples cross a surface (wall, glass,
    furniture, curtain)? The pivot door is open and the kitchen/study partition has its open
    bay, as in the browser.
  * clearance: indoors the camera keeps MIN_CLEAR from every surface (the final move onto the
    laptop screen may come closer: END_CLEAR, still beyond the 0.06 m near plane).
  * walking: the eye stays at least EYE_MIN above the floor or tread underneath, and nothing
    but floor lies within BODY_R of the line under it (no walking over sofas or beds).

Exits with status 1 if anything fails. Run it after editing the route and after a rebuild:
the browser draws public/rt/halcyon.glb, so re-export after changing the model.
"""
import bpy, json, math, os, sys
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rtlib as R  # noqa: E402
from bake_rt import partition_glass  # noqa: E402

SAMPLES = os.path.join(HERE, 'rt', 'route_samples.json')
INSIDE_U = 9.0       # keys from here on are indoors (the pivot door is at key 9)
END_KEYS = 4.0       # the last four keys: sitting down at the study desk, leaning in to the laptop
MIN_CLEAR = 0.30     # metres from any surface while walking indoors
END_CLEAR = 0.10
EYE_MIN = 1.52       # eye above the floor or tread underneath while walking
BODY_R = 0.25        # the walker's half-width: furniture this close to the line under the eye is in the way
STEP = 0.25          # anything rising more than this above the floor underfoot is an obstacle, not floor
DOOR_OPEN_DEG = 84.0  # as the browser swings it (scene.json door.open_deg)
SKIP_COLLS = {'Cameras', 'RT'}


def build_bvh():
    s = bpy.context.scene
    s.frame_set(1)
    door = bpy.data.objects.get('Door_Pivot')
    if door:
        door.rotation_euler.z = math.radians(DOOR_OPEN_DEG)
    R.fix_world(s)
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys, owner = [], [], []

    def add(name, mw, me):
        base = len(verts)
        verts.extend(mw @ v.co for v in me.vertices)
        for p in me.polygons:
            polys.append(tuple(base + i for i in p.vertices))
            owner.append(name)

    for ob in s.objects:
        if ob.type not in ('MESH', 'CURVE') or ob.hide_render or not getattr(ob, 'visible_camera', True):
            continue
        if R.coll_of(ob) in SKIP_COLLS:
            continue
        split = partition_glass(ob)
        if split:  # world coordinates, with the open bay the camera walks through
            add(ob.name, Matrix.Identity(4), split)
            bpy.data.meshes.remove(split)
            continue
        ev = ob.evaluated_get(dg)
        try:
            me = ev.to_mesh()
        except RuntimeError:
            continue
        if me is not None and me.polygons:
            add(ob.name, R.world(ob), me)
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys, all_triangles=False), owner, len(polys)


def runs_of(flags):
    """[(u, value, where, what)] for flagged samples -> contiguous stretches, worst value kept."""
    out, cur = [], None
    for f in flags:
        if f is None:
            if cur:
                out.append(cur)
            cur = None
            continue
        u, val, at, what = f
        if cur is None:
            cur = dict(u0=u, u1=u, worst=val, at=at, what=what)
        cur['u1'] = u
        if val < cur['worst']:
            cur.update(worst=val, at=at, what=what)
    if cur:
        out.append(cur)
    return out


def main():
    data = json.load(open(SAMPLES))
    pts = data['pts']
    end_u = len(data['keys']) - 1 - END_KEYS
    bvh, owner, npoly = build_bvh()
    probe = next(p for p in pts if p[3] >= INSIDE_U + 1)
    if bvh.find_nearest(Vector(probe[:3]), 5.0)[0] is None:
        print('[ROUTE] FAIL: no surface within 5 m of the hall; the model did not load into the test')
        sys.exit(1)
    print(f'[ROUTE] {len(pts)} samples, {npoly} polygons')

    crossings, close, low = [], [], []
    for i, (x, y, z, u) in enumerate(pts):
        p = Vector((x, y, z))
        at = [round(x, 2), round(y, 2), round(z, 2)]
        if i + 1 < len(pts):
            d = Vector(pts[i + 1][:3]) - p
            if d.length > 1e-6:
                hit = bvh.ray_cast(p, d.normalized(), d.length)
                if hit[0] is not None:
                    crossings.append((u, owner[hit[2]], [round(c, 2) for c in hit[0]]))
        if u < INSIDE_U:
            close.append(None)
            low.append(None)
            continue
        limit = END_CLEAR if u >= end_u else MIN_CLEAR
        near = bvh.find_nearest(p, limit)
        close.append((u, round(near[3], 3), at, owner[near[2]]) if near[0] is not None else None)
        if u < end_u:
            down = bvh.ray_cast(p, Vector((0, 0, -1)), 10.0)
            h = down[3] if down[0] is not None else 99.0
            flag = (u, round(h, 3), at, owner[down[2]] if down[0] is not None else None) if h < EYE_MIN else None
            # the walker's body: nothing but floor (or the next stair tread) within BODY_R of the
            # line under the eye; furniture there means the route walks over it
            if flag is None and down[0] is not None:
                for k in range(8):
                    a = k * math.pi / 4
                    o = p + Vector((BODY_R * math.cos(a), BODY_R * math.sin(a), 0))
                    hit = bvh.ray_cast(o, Vector((0, 0, -1)), 10.0)
                    if hit[0] is None or owner[hit[2]].startswith('B_tread'):
                        continue
                    rise = hit[0].z - down[0].z
                    if rise > STEP:
                        flag = (u, round(z - hit[0].z, 3), at, owner[hit[2]])
                        break
            low.append(flag)
        else:
            low.append(None)

    close_runs, low_runs = runs_of(close), runs_of(low)
    for u, what, at in crossings:
        print(f'[ROUTE] FAIL passes through {what} at {at} (key {u:.2f})')
    for r in close_runs:
        print(f"[ROUTE] FAIL within {r['worst']:.3f} m of {r['what']} at {r['at']} (keys {r['u0']:.2f}-{r['u1']:.2f})")
    for r in low_runs:
        print(f"[ROUTE] FAIL walks over {r['what']} (eye {r['worst']:.2f} m above it) at {r['at']} (keys {r['u0']:.2f}-{r['u1']:.2f})")
    ok = not (crossings or close_runs or low_runs)
    print(f'[ROUTE] {"PASS" if ok else "FAIL"}: {len(crossings)} pass-throughs, {len(close_runs)} tight spots, '
          f'{len(low_runs)} walking problems (clearance {MIN_CLEAR} m indoors, eye >= {EYE_MIN} m, body {BODY_R} m)')
    if not ok:
        sys.exit(1)


main()
