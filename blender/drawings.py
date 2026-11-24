"""Generate the drawing set from the HALCYON model (run headless).

blender -b halcyon.blend -P drawings.py -- --what plan,section,site,axo,swatches
Outputs: lib/plan.json, lib/section.json, public/drawings/site.svg,
         public/drawings/axonometric.png, public/drawings/materials/*.webp(png)
"""
import bpy, bmesh, math, json, os, sys, argparse
from mathutils import Vector, Matrix

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--what', default='plan,section,site,axo,swatches')
a = ap.parse_args(argv)
WHAT = set(a.what.split(','))

PUB = os.path.join(REPO, 'public', 'drawings')
LIB = os.path.join(REPO, 'lib')
os.makedirs(PUB, exist_ok=True)
os.makedirs(os.path.join(PUB, 'materials'), exist_ok=True)

def coll_objects(name):
    c = bpy.data.collections.get(name)
    return list(c.all_objects) if c else []

def world_bbox(ob):
    return [ob.matrix_world @ Vector(c) for c in ob.bound_box]

def r(v, n=3):
    return round(v, n)

def hull(pts):
    pts = sorted(set((r(p[0]), r(p[1])) for p in pts))
    if len(pts) < 3:
        return pts
    def cross(o, a_, b):
        return (a_[0] - o[0]) * (b[1] - o[1]) - (a_[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]

def is_glass(ob):
    return any(m and 'Glass' in m.name for m in getattr(ob.data, 'materials', []))

# ---------------------------------------------------------------- plan
def plan():
    Z = 1.1
    cut, glass, furn = [], [], []
    for ob in coll_objects('Architecture'):
        if ob.type != 'MESH':
            continue
        bb = world_bbox(ob)
        zs = [p.z for p in bb]
        if not (min(zs) <= Z <= max(zs)):
            continue
        xs = [p.x for p in bb]; ys = [p.y for p in bb]
        if is_glass(ob):
            if max(xs) - min(xs) > max(ys) - min(ys):
                glass.append([r(min(xs)), r((min(ys) + max(ys)) / 2), r(max(xs)), r((min(ys) + max(ys)) / 2)])
            else:
                glass.append([r((min(xs) + max(xs)) / 2), r(min(ys)), r((min(xs) + max(xs)) / 2), r(max(ys))])
            continue
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        if w * h < 0.0004:
            continue
        cut.append([r(min(xs)), r(min(ys)), r(w), r(h), 1 if any(m and m.name.startswith('Metal') for m in ob.data.materials) else 0])
    skip = ('led', 'light', 'Lamp', 'bulb', 'cable', 'wire', 'cord', 'flames', 'embers', 'trim', 'seam', 'leaves', 'wood')
    for ob in coll_objects('Interior'):
        if ob.type not in ('MESH', 'CURVE'):
            continue
        if any(k.lower() in ob.name.lower() for k in skip):
            continue
        bb = world_bbox(ob)
        zs = [p.z for p in bb]
        if min(zs) > Z + 0.3 or max(zs) < 0.01:
            continue
        hpoly = hull([(p.x, p.y) for p in bb])
        if len(hpoly) < 3:
            continue
        area = 0.0
        for i in range(len(hpoly)):
            x1, y1 = hpoly[i]; x2, y2 = hpoly[(i + 1) % len(hpoly)]
            area += x1 * y2 - x2 * y1
        if abs(area) / 2 < 0.004 or abs(area) / 2 > 40:
            continue
        furn.append(hpoly)
    site = []
    for name in ('S_terrace', 'S_entrycourt', 'S_eastdeck', 'S_deckN', 'S_deckS', 'S_deckW', 'S_deckE', 'S_firedeck'):
        ob = bpy.data.objects.get(name)
        if ob:
            bb = world_bbox(ob); xs = [p.x for p in bb]; ys = [p.y for p in bb]
            site.append([r(min(xs)), r(min(ys)), r(max(xs) - min(xs)), r(max(ys) - min(ys))])
    pool = [5.6, -11.8, 13.6, 4.6]
    rooms = [
        dict(id='great', name='Great room', area='152 m²', rect=[-14.64, 0.25, 11.34, 13.39]),
        dict(id='arrival', name='Arrival hall', area='65 m²', rect=[-3.0, 2.34, 5.7, 11.36]),
        dict(id='kitchen', name='Kitchen and dining', area='138 m²', rect=[3.0, 0.15, 11.07, 12.49]),
        dict(id='study', name='Study', area='55 m²', rect=[14.13, 0.31, 4.51, 12.33]),
    ]
    data = dict(bounds=[-20.0, -15.0, 42.0, 31.0], cut=cut, glass=glass, furniture=furn, site=site, pool=pool, rooms=rooms,
                dock=[-1.8, -31.0, 3.6, 13.9 - 0.0], wall=[-26.0, -13.7, 53.0, 0.7])
    with open(os.path.join(LIB, 'plan.json'), 'w') as fh:
        json.dump(data, fh, separators=(',', ':'))
    print('[DRAW] plan', len(cut), len(glass), len(furn))

# ---------------------------------------------------------------- sections
def cut_loops(plane_co, plane_no, uv):
    """Bisect architecture + hardscape meshes; return closed loops in drawing coords uv(Vector)->(u, z)."""
    loops = []
    pc, pn = Vector(plane_co), Vector(plane_no)
    for cname in ('Architecture', 'Hardscape', 'Interior'):
        for ob in coll_objects(cname):
            if ob.type != 'MESH':
                continue
            if cname == 'Interior' and not ob.name.startswith(('GR_breast', 'GR_hearth', 'KT_tall', 'KT_island', 'KT_base', 'ST_lib', 'UP_bed')):
                continue
            bb = world_bbox(ob)
            ds = [(p - pc).dot(pn) for p in bb]
            if not (min(ds) < 0 < max(ds)):
                continue
            bm = bmesh.new()
            bm.from_mesh(ob.data)
            bm.transform(ob.matrix_world)
            res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5, plane_co=pc, plane_no=pn)
            segs = []
            for e in res['geom_cut']:
                if isinstance(e, bmesh.types.BMEdge):
                    v1, v2 = e.verts
                    a_, b_ = uv(v1.co), uv(v2.co)
                    segs.append(((r(a_[0]), r(a_[1])), (r(b_[0]), r(b_[1]))))
            bm.free()
            adj = {}
            for p, q in segs:
                adj.setdefault(p, []).append(q)
                adj.setdefault(q, []).append(p)
            seen = set()
            for start in list(adj):
                if start in seen:
                    continue
                loop = [start]
                seen.add(start)
                cur = start
                while True:
                    nxt = [n for n in adj[cur] if n not in seen]
                    if not nxt:
                        break
                    cur = nxt[0]
                    seen.add(cur)
                    loop.append(cur)
                if len(loop) >= 3:
                    loops.append(dict(pts=loop, glass=is_glass(ob), metal=any(m and m.name.startswith('Metal') for m in ob.data.materials)))
    return loops

def section():
    ew = cut_loops((0, 7.0, 0), (0, 1, 0), lambda v: (v.x, v.z))
    ns = cut_loops((8.5, 0, 0), (1, 0, 0), lambda v: (v.y, v.z))
    data = dict(ew=dict(loops=ew, water=-2.2, bounds=[-19.5, -3.2, 43.0, 15.6]),
                ns=dict(loops=ns, water=-2.2, bounds=[-16.0, -3.2, 31.0, 11.6]))
    with open(os.path.join(LIB, 'section.json'), 'w') as fh:
        json.dump(data, fh, separators=(',', ':'))
    print('[DRAW] section loops', len(ew), len(ns))

# ---------------------------------------------------------------- site plan (SVG)
def site():
    import hsite
    X0, X1, Y0, Y1 = -140.0, 140.0, -80.0, 120.0
    S = 3.2  # px per metre
    W, H = (X1 - X0) * S, (Y1 - Y0) * S
    def P(x, y):
        return (x - X0) * S, (Y1 - y) * S
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}">',
           '<defs><pattern id="water" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(0)">'
           '<path d="M0 4 H8" stroke="#5e7286" stroke-width="0.6" stroke-opacity="0.55"/></pattern></defs>',
           '<rect width="100%" height="100%" fill="none"/>']
    # lake polygon from the shoreline
    xs = [X0 + i * 1.0 for i in range(int(X1 - X0) + 1)]
    pts = [P(x, max(Y0, min(Y1, hsite.shore_y(x)))) for x in xs]
    d = 'M' + ' L'.join(f'{px:.1f} {py:.1f}' for px, py in pts) + f' L{W:.0f} {H:.0f} L0 {H:.0f} Z'
    out.append(f'<path d="{d}" fill="url(#water)" stroke="#0d1820" stroke-width="1.6"/>')
    # contours (marching squares, 2 m interval)
    step = 2.0
    nx, ny = int((X1 - X0) / step) + 1, int((Y1 - Y0) / step) + 1
    grid = [[hsite.height(X0 + i * step, Y0 + j * step) for i in range(nx)] for j in range(ny)]
    lines = []
    for lvl in range(0, 40, 2):
        for j in range(ny - 1):
            for i in range(nx - 1):
                v = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
                c = [(X0 + i * step, Y0 + j * step), (X0 + (i + 1) * step, Y0 + j * step),
                     (X0 + (i + 1) * step, Y0 + (j + 1) * step), (X0 + i * step, Y0 + (j + 1) * step)]
                cr = []
                for k in range(4):
                    a_, b_ = v[k], v[(k + 1) % 4]
                    if (a_ - lvl) * (b_ - lvl) < 0:
                        t = (lvl - a_) / (b_ - a_)
                        cr.append((c[k][0] + (c[(k + 1) % 4][0] - c[k][0]) * t, c[k][1] + (c[(k + 1) % 4][1] - c[k][1]) * t))
                if len(cr) >= 2:
                    (ax, ay), (bx, by) = P(*cr[0]), P(*cr[1])
                    major = lvl % 10 == 0
                    lines.append(f'<path d="M{ax:.1f} {ay:.1f}L{bx:.1f} {by:.1f}" stroke="#3f2c21" stroke-opacity="{0.55 if major else 0.25}" stroke-width="{0.9 if major else 0.5}"/>')
    out.append('<g fill="none">' + ''.join(lines) + '</g>')
    # trees
    trees = []
    for ob in coll_objects('Forest'):
        x, y = ob.location.x, ob.location.y
        if X0 < x < X1 and Y0 < y < Y1:
            px, py = P(x, y)
            rad = 3.2 * ob.scale.x * S
            trees.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{rad:.1f}"/>')
    out.append('<g fill="#5e7286" fill-opacity="0.08" stroke="#5e7286" stroke-opacity="0.45" stroke-width="0.6">' + ''.join(trees) + '</g>')
    # hardscape + house footprints
    def rect(x0, y0, x1, y1, fill, sw=1.2, op=1):
        (ax, ay), (bx, by) = P(x0, y1), P(x1, y0)
        return f'<rect x="{ax:.1f}" y="{ay:.1f}" width="{bx - ax:.1f}" height="{by - ay:.1f}" fill="{fill}" fill-opacity="{op}" stroke="#0d1820" stroke-width="{sw}"/>'
    out.append(rect(-17.5, -6.4, 21.0, 0, '#d8d0c2', 0.8))
    out.append(rect(3.4, -13.0, 21.0, -6.4, '#d8d0c2', 0.8))
    out.append(rect(5.6, -11.8, 19.2, -7.2, '#9aabbb', 0.8))
    out.append(rect(-26.0, -13.7, 27.0, -13.0, '#3f2c21', 0.6))
    out.append(rect(-1.8, -31.0, 1.8, -17.1, '#d8d0c2', 0.8))
    for (x0, y0, x1, y1) in ((-15, 0, -3, 14), (-3, 2, 3, 14), (3, 0, 19, 13), (2.6, -2.2, 20.5, 13.4)):
        out.append(rect(x0, y0, x1, y1, '#0d1820', 0.0, 0.88))
    # north arrow + scale bar
    nx_, ny_ = W - 70, 70
    out.append(f'<g transform="translate({nx_:.0f},{ny_:.0f})" stroke="#0d1820" fill="none"><circle r="26" stroke-width="1"/>'
               f'<path d="M0 -22 L8 14 L0 6 L-8 14 Z" fill="#0d1820"/></g>')
    sx, sy = 40, H - 40
    out.append(f'<g stroke="#0d1820" stroke-width="1.2"><path d="M{sx} {sy} H{sx + 50 * S}"/>'
               f'<path d="M{sx} {sy - 6} V{sy + 6} M{sx + 25 * S} {sy - 4} V{sy + 4} M{sx + 50 * S} {sy - 6} V{sy + 6}"/></g>')
    out.append('</svg>')
    with open(os.path.join(PUB, 'site.svg'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out))
    print('[DRAW] site svg', len(lines), len(trees))

# ---------------------------------------------------------------- axonometric (Freestyle hidden-line)
def axo():
    s = bpy.context.scene
    keep = set(o.name for o in coll_objects('Architecture'))
    keep |= set(o.name for o in coll_objects('Hardscape') if not o.name.startswith(('S_lounger', 'S_firesofa', 'S_flame', 'S_bollard', 'S_lantern', 'S_post', 'S_pool')))
    keep.discard('S_poolwater')
    for ob in list(bpy.data.objects):
        if ob.type in ('MESH', 'CURVE') and ob.name not in keep:
            ob.hide_render = True
        if ob.type == 'LIGHT':
            ob.hide_render = True
    white = bpy.data.materials.new('AxoWhite')
    white.use_nodes = True
    nt = white.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    o = nt.nodes.new('ShaderNodeOutputMaterial')
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = (0.79, 0.81, 0.81, 1)
    e.inputs['Strength'].default_value = 1.0
    nt.links.new(e.outputs[0], o.inputs[0])
    glassm = bpy.data.materials.new('AxoGlass')
    glassm.use_nodes = True
    gnt = glassm.node_tree
    for n in list(gnt.nodes):
        gnt.nodes.remove(n)
    go = gnt.nodes.new('ShaderNodeOutputMaterial')
    ge = gnt.nodes.new('ShaderNodeEmission')
    ge.inputs['Color'].default_value = (0.55, 0.62, 0.68, 1)
    gnt.links.new(ge.outputs[0], go.inputs[0])
    for name in keep:
        ob = bpy.data.objects.get(name)
        if ob and ob.type == 'MESH':
            g = is_glass(ob)
            for i in range(len(ob.material_slots)):
                ob.material_slots[i].link = 'OBJECT'
                ob.material_slots[i].material = glassm if g else white
            for m in list(ob.modifiers):
                if m.type == 'BEVEL':
                    m.show_render = False
    cam = bpy.data.cameras.new('AxoCam')
    cam.type = 'ORTHO'
    cam.ortho_scale = 58
    co = bpy.data.objects.new('AxoCam', cam)
    s.collection.objects.link(co)
    ctr = Vector((2.0, 2.0, 3.0))
    d = Vector((math.cos(math.radians(-128)), math.sin(math.radians(-128)), 0.0))
    d = (d.normalized() * math.cos(math.radians(32)) + Vector((0, 0, math.sin(math.radians(32))))).normalized()
    co.location = ctr + d * 120
    co.rotation_euler = (ctr - co.location).to_track_quat('-Z', 'Y').to_euler()
    cam.clip_end = 1000
    s.camera = co
    s.timeline_markers.clear()
    w = s.world
    if w and w.node_tree:
        for n in w.node_tree.nodes:
            if n.type == 'BACKGROUND':
                n.inputs['Strength'].default_value = 0.0
    s.render.engine = 'CYCLES'
    s.cycles.samples = 4
    s.cycles.use_denoising = False
    s.cycles.use_fast_gi = False
    s.render.film_transparent = True
    s.render.resolution_x, s.render.resolution_y = 2400, 1700
    s.view_settings.view_transform = 'Standard'
    s.view_settings.look = 'None'
    s.view_settings.exposure = 0
    s.render.use_freestyle = True
    s.render.line_thickness_mode = 'ABSOLUTE'
    s.render.line_thickness = 1.4
    vl = s.view_layers[0]
    vl.use_freestyle = True
    fs = vl.freestyle_settings
    fs.crease_angle = math.radians(140)
    ls = fs.linesets[0] if fs.linesets else fs.linesets.new('Lines')
    ls.select_by_visibility = True
    ls.visibility = 'VISIBLE'
    ls.select_silhouette = True
    ls.select_border = True
    ls.select_crease = True
    ls.linestyle.color = (0.05, 0.09, 0.125)
    ls.linestyle.thickness = 1.4
    s.render.image_settings.file_format = 'PNG'
    s.render.image_settings.color_mode = 'RGBA'
    s.render.filepath = os.path.join(PUB, 'axonometric.png')
    bpy.ops.render.render(write_still=True)
    print('[DRAW] axo done')

# ---------------------------------------------------------------- material swatches
def swatches():
    import hlib
    s = bpy.context.scene
    for ob in s.objects:
        ob.hide_render = True
    sc = bpy.data.collections.new('Swatch')
    s.collection.children.link(sc)
    # tile: thick slab, bevelled, seen at a raking angle
    tile = hlib.box('SwatchTile', -0.5, 0.5, -0.5, 0.5, -0.06, 0.0, None, sc, 0.012, 3)
    cam = bpy.data.cameras.new('SwCam'); cam.lens = 62
    co = bpy.data.objects.new('SwCam', cam); sc.objects.link(co)
    co.location = (0.0, -1.55, 1.25)
    co.rotation_euler = (Vector((0, 0.02, -0.03)) - co.location).to_track_quat('-Z', 'Y').to_euler()
    s.camera = co
    s.timeline_markers.clear()
    ld = bpy.data.lights.new('SwKey', 'AREA'); ld.size = 1.6; ld.energy = 140
    ld.color = (1.0, 0.93, 0.85)
    key = bpy.data.objects.new('SwKey', ld); sc.objects.link(key)
    key.location = (-1.6, -0.6, 1.4)
    key.rotation_euler = (Vector((0, 0, 0)) - key.location).to_track_quat('-Z', 'Y').to_euler()
    ld2 = bpy.data.lights.new('SwRim', 'AREA'); ld2.size = 2.0; ld2.energy = 40
    rim = bpy.data.objects.new('SwRim', ld2); sc.objects.link(rim)
    rim.location = (1.4, 1.2, 1.0)
    rim.rotation_euler = (Vector((0, 0, 0)) - rim.location).to_track_quat('-Z', 'Y').to_euler()
    s.render.engine = 'CYCLES'
    s.cycles.samples = 24
    s.cycles.use_denoising = True
    s.render.film_transparent = True
    s.render.resolution_x = s.render.resolution_y = 520
    s.render.image_settings.color_mode = 'RGBA'
    w = s.world
    if w and w.node_tree:
        for n in w.node_tree.nodes:
            if n.type == 'BACKGROUND':
                n.inputs['Strength'].default_value = 0.08
    names = {'stone_ext': 'Stone_Ledger_Ext', 'limestone_floor': 'Limestone_Floor', 'oak_floor': 'Oak_Floor', 'walnut': 'Walnut',
             'marble': 'Marble_Calacatta', 'metal_dark': 'Metal_Bronze_Dark', 'charred': 'Timber_Dark', 'zinc': 'Roof_Zinc'}
    for key_, mname in names.items():
        mat = bpy.data.materials.get(mname)
        if not mat:
            continue
        tile.data.materials.clear()
        tile.data.materials.append(mat)
        # world-space materials: move the tile so the pattern sits naturally
        tile.location = (3.3, 4.1, 0.0) if key_ in ('stone_ext', 'charred') else (0, 0, 0)
        tile.rotation_euler = (math.radians(90), 0, 0) if key_ in ('stone_ext', 'charred') else (0, 0, 0)
        if key_ in ('stone_ext', 'charred'):
            tile.location = (0, 0, 0)
            co.location = (0.0, -1.95, 0.25)
            co.rotation_euler = (Vector((0, 0, 0.0)) - co.location).to_track_quat('-Z', 'Y').to_euler()
        else:
            co.location = (0.0, -1.55, 1.25)
            co.rotation_euler = (Vector((0, 0.02, -0.03)) - co.location).to_track_quat('-Z', 'Y').to_euler()
        s.render.filepath = os.path.join(PUB, 'materials', f'{key_}.png')
        bpy.ops.render.render(write_still=True)
        print('[DRAW] swatch', key_, flush=True)

if 'plan' in WHAT:
    plan()
if 'section' in WHAT:
    section()
if 'site' in WHAT:
    site()
if 'swatches' in WHAT:
    swatches()
if 'axo' in WHAT:
    axo()
