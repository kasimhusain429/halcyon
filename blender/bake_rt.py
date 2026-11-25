"""HALCYON real-time build: texture atlases and denoised light maps for the live walkthrough.

  1. blender -b blender/halcyon.blend --python blender/bake_rt.py -- prep
       joins each collection into a few objects, unwraps them, saves blender/rt/prepared.blend
  2. blender -b blender/rt/prepared.blend --python blender/bake_rt.py -- bake [--only A_Door,V_Far]
       per atlas object: colour (+ roughness in alpha), normal, light (Cycles) -> OIDN
       vertex-lit objects (terrain, rocks, grass, mountains) get their light per vertex
       everything lands in blender/rt/bake/; reruns skip what is already there
  3. blender -b blender/rt/prepared.blend --python blender/bake_rt.py -- export
       public/rt/halcyon.glb + scene.json (textures are encoded afterwards: encode_rt.py)
"""
import bpy, bmesh, json, math, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rtlib as R  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, '..'))
WORK = os.path.join(HERE, 'rt')
BAKE_DIR = os.path.join(WORK, 'bake')
OUT = os.path.join(ROOT, 'public', 'rt')
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
STAGE = ARGS[0] if ARGS else 'prep'

# drawn by their own materials in the browser, never baked into an atlas
SPECIAL = {'Glass_Window', 'Glass_Clear', 'Glass_Frosted', 'Black_Glass', 'Curtain_Sheer', 'Pool_Water',
           'Fire_Flames', 'Laptop_Screen', 'Lake_Water'}
# the shell's inside faces get the finer atlas
INTERIOR_SURF = {'Plaster_White', 'Plaster_Warm', 'Oak_Floor', 'Oak_Ceiling', 'Oak_Solid', 'Stone_Ledger_Int',
                 'Limestone_Floor', 'Walnut_Panel', 'Beam_Dark'}
# landscape: light per vertex is enough
VERTEX_GROUPS = {'Terrain', 'Rocks', 'Grasses', 'Shrubs', 'Far', 'Exterior_Fixtures'}
SKIP_COLLS = {'Forest', 'Cameras', 'RT'}
# metres per texel: (colour, light)
DENSITY = {'A_Architecture_int': (0.02, 0.04), 'A_Architecture_ext': (0.025, 0.09),
           'A_Arrival': (0.015, 0.03), 'A_Great_Room': (0.015, 0.03), 'A_Kitchen': (0.015, 0.03),
           'A_Study': (0.012, 0.03), 'A_Upper': (0.015, 0.03), 'A_Hardscape': (0.03, 0.06), 'A_Door': (0.01, 0.03)}
MAX_ATLAS = 4096
LIGHT_SPP = 96
VERTEX_SPP = 64
LIGHT_SCALE = 4.0  # light stored as sqrt(light / 4): headroom above 1, finer steps in the dark
MARGIN_PX = 4      # bake margin (dilation) in pixels
PACK_MARGIN_PX = 2  # gap between UV islands at light-map resolution
# objects smaller than this (m^2) or denser than this (faces per m^2) take their colour and light
# per vertex instead of from an atlas: books, rings, stools and leaves would only waste atlas space
ATLAS_MIN_AREA = 0.5
ATLAS_MAX_DENSITY = 400

# kitchen/study partition: an open bay between mullions 4 and 5 (the camera walks through)
PX, PY0, PY1, PZ1 = 14.1, 0.35, 12.64, 3.3
NM = max(1, round((PY1 - PY0) / 0.9))
GAP = (PY0 + (PY1 - PY0) * 4 / NM + 0.02, PY0 + (PY1 - PY0) * 5 / NM - 0.02)

def partition_glass(o):
    if o.name != 'C_partition_glass':
        return None
    me = bpy.data.meshes.new('partition_split')
    v = [(PX, PY0, 0), (PX, GAP[0], 0), (PX, GAP[0], PZ1), (PX, PY0, PZ1),
         (PX, GAP[1], 0), (PX, PY1, 0), (PX, PY1, PZ1), (PX, GAP[1], PZ1),
         (PX, GAP[0], 2.35), (PX, GAP[1], 2.35)]
    me.from_pydata(v, [], [(0, 1, 2, 3), (4, 5, 6, 7), (8, 9, 7, 2)])
    return me

def log(*a):
    print('[rt]', time.strftime('%H:%M:%S'), *a, flush=True)

def size_for(area, coverage, density):
    px = math.sqrt(area / (density * density) / max(coverage, 0.05))
    return int(min(MAX_ATLAS, max(256, math.ceil(px / 128) * 128)))

def uv_coverage(ob):
    me = ob.data
    uv = me.uv_layers.active.data
    co = np.empty(len(uv) * 2, dtype=np.float64)
    uv.foreach_get('uv', co)
    co = co.reshape(-1, 2)
    total = 0.0
    for p in me.polygons:
        i0 = p.loop_start
        pts = co[i0:i0 + p.loop_total]
        x, y = pts[:, 0], pts[:, 1]
        total += 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
    return total

def unwrap(ob, margin, fallback=False):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    while ob.data.uv_layers:
        ob.data.uv_layers.remove(ob.data.uv_layers[0])
    ob.data.uv_layers.new(name='Atlas')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    if fallback:
        bpy.ops.uv.lightmap_pack(PREF_CONTEXT='ALL_FACES', PREF_PACK_IN_ONE=True, PREF_NEW_UVLAYER=False,
                                 PREF_BOX_DIV=12, PREF_MARGIN_DIV=0.1)
    else:
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.0, area_weight=0.0,
                                 correct_aspect=True, scale_to_bounds=False)
        bpy.ops.uv.pack_islands(rotate=True, scale=True, margin_method='FRACTION', margin=margin, shape_method='AABB')
    bpy.ops.object.mode_set(mode='OBJECT')
    ob.select_set(False)

# ================================================================ 1. prep
def stage_prep():
    s = bpy.context.scene
    s.frame_set(1)  # pivot door closed; the browser swings it
    R.fix_world(s)
    dg = bpy.context.evaluated_depsgraph_get()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(BAKE_DIR, exist_ok=True)

    used = {}
    for o in s.objects:
        if o.type == 'MESH':
            for sl in o.material_slots:
                if sl.material:
                    used[sl.material.name] = sl.material
    mats = {n: R.describe(m, OUT) for n, m in sorted(used.items())}
    metal = {n for n, d in mats.items() if d['metal'] > 0.5}

    def special(m):
        n = m.name if m else ''
        return n in SPECIAL or n.startswith('Emit_') or n in metal

    rand = R.random_to_attribute(used.values())
    lights = R.collect_lights(s)
    rt = bpy.data.collections.new('RT')
    s.collection.children.link(rt)

    groups, water, door = {}, [], []
    for o in s.objects:
        if o.type not in ('MESH', 'CURVE') or o.hide_render or not getattr(o, 'visible_camera', True):
            continue
        c = R.coll_of(o)
        if c in SKIP_COLLS:
            continue
        if c == 'Water':
            water.append(o)
        elif c == 'Door':
            door.append(o)
        else:
            groups.setdefault(c, []).append(o)
    sources = [o for obs in groups.values() for o in obs] + water + door

    made = {}

    def build(name, obs, rel=None, replace=None):
        return R.join([R.temp_copy(o, dg, rt, rel=rel, rand_mats=rand, replace=replace) for o in obs], name)

    def split(whole, parts):
        for name, keep, kind in parts:
            o = R.split_faces(whole, keep, name)
            if o:
                made[name] = kind
        me = whole.data
        bpy.data.objects.remove(whole)
        bpy.data.meshes.remove(me)

    def big(t):
        area = R.mesh_area(t)
        return area >= ATLAS_MIN_AREA and len(t.data.polygons) / max(area, 1e-6) <= ATLAS_MAX_DENSITY

    for c, obs in sorted(groups.items()):
        temps = [R.temp_copy(o, dg, rt, rand_mats=rand, replace=partition_glass) for o in obs]
        if c in VERTEX_GROUPS:
            whole = R.join(temps, f'J_{c}')
            if whole:
                split(whole, [(f'V_{c}', lambda m: not special(m), 'vertex'), (f'S_{c}', special, 'special')])
            log('join', c, len(obs), 'vertex')
            continue
        large = [t for t in temps if big(t)]
        small = [t for t in temps if not big(t)]
        log('join', c, len(obs), f'atlas {len(large)} / detail {len(small)}')
        whole = R.join(large, f'J_{c}')
        if whole:
            if c == 'Architecture':
                parts = [('A_Architecture_int', lambda m: not special(m) and bool(m) and m.name in INTERIOR_SURF, 'atlas'),
                         ('A_Architecture_ext', lambda m: not special(m) and not (m and m.name in INTERIOR_SURF), 'atlas')]
            else:
                parts = [(f'A_{c}', lambda m: not special(m), 'atlas')]
            split(whole, parts + [(f'S_{c}', special, 'special')])
        detail = R.join(small, f'J_{c}_detail')
        if detail:
            split(detail, [(f'V_{c}_detail', lambda m: not special(m), 'vertex'), (f'S_{c}_detail', special, 'special')])
    pivot = bpy.data.objects.get('Door_Pivot')
    if door and pivot:
        whole = build('J_Door', door, rel=pivot)
        whole.matrix_world = R.world(pivot)
        split(whole, [('A_Door', lambda m: not special(m), 'atlas'), ('S_Door', special, 'special')])
    for o in water:
        w = build(f'W_{o.name}', [o])
        if w:
            made[w.name] = 'water'
    # the joined copies stand in for their sources from here on (no double geometry in the bake)
    for o in sources:
        o.hide_render = True

    # forest: two decimated levels of detail per conifer, plus every instance's matrix
    forest = [o for o in s.objects if o.type == 'MESH' and R.coll_of(o) == 'Forest']
    meshes = sorted({o.data.name for o in forest})
    for mname in meshes:
        src = bpy.data.meshes[mname]
        for tag, ratio in (('N', 0.22), ('F', 0.035)):
            tmp = bpy.data.objects.new('tmp', src)
            rt.objects.link(tmp)
            mod = tmp.modifiers.new('dec', 'DECIMATE')
            mod.ratio = ratio
            d2 = bpy.context.evaluated_depsgraph_get()
            me = bpy.data.meshes.new_from_object(tmp.evaluated_get(d2), depsgraph=d2)
            bpy.data.objects.remove(tmp)
            ob = bpy.data.objects.new(f'LOD{tag}_{mname}', me)
            rt.objects.link(ob)
            ob.hide_render = True  # export helpers at the origin, not part of the scene
            made[ob.name] = 'lod'
    trees = []
    for o in forest:
        m = R.world(o)
        trees.append([meshes.index(o.data.name)] + [round(m[r][c], 3) for r in range(3) for c in range(4)])

    # unwrap the atlas objects and size their maps from area and texel density
    atlases = {}
    for name, kind in sorted(made.items()):
        if kind != 'atlas':
            continue
        ob = bpy.data.objects[name]
        area = R.mesh_area(ob)
        dc, dl = DENSITY.get(name, (0.03, 0.06))
        est = size_for(area, 0.55, dl)
        t0 = time.time()
        unwrap(ob, PACK_MARGIN_PX / est)
        cov = uv_coverage(ob)
        if cov < 0.25:
            log('unwrap', name, f'coverage {cov:.3f}: falling back to lightmap pack')
            unwrap(ob, PACK_MARGIN_PX / est, fallback=True)
            cov = uv_coverage(ob)
        sc, sl = size_for(area, cov, dc), size_for(area, cov, dl)
        atlases[name] = dict(area=round(area, 1), faces=len(ob.data.polygons), coverage=round(cov, 3),
                             color=sc, light=sl,
                             density_cm=[round(100 * math.sqrt(area / (cov * sc * sc)), 2),
                                         round(100 * math.sqrt(area / (cov * sl * sl)), 2)])
        log('unwrap', name, atlases[name], f'{time.time() - t0:.0f}s')

    meta = dict(materials=mats, lights=[L for L in lights if L['type'] != 'SUN'],
                sun=next((L for L in lights if L['type'] == 'SUN'), None),
                objects=made, atlases=atlases, forest=dict(meshes=meshes, trees=trees),
                door=dict(open_deg=84.0), partition_gap=[round(GAP[0], 3), round(GAP[1], 3)],
                world=dict(sun_elev=1.6, sun_azim=246.0), light_scale=LIGHT_SCALE)
    with open(os.path.join(WORK, 'prep.json'), 'w') as fh:
        json.dump(meta, fh, separators=(',', ':'))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(WORK, 'prepared.blend'), compress=True)
    log('PREP_DONE', json.dumps(dict(objects=len(made), atlases=atlases)))

# ================================================================ 2. bake
def select_only(ob):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob

def point_bake_at(ob, img):
    for sl in ob.material_slots:
        m = sl.material
        if not m or not m.node_tree:
            continue
        nt = m.node_tree
        n = nt.nodes.get('RT_BAKE') or nt.nodes.new('ShaderNodeTexImage')
        n.name = 'RT_BAKE'
        n.image = img
        for k in nt.nodes:
            k.select = False
        n.select = True
        nt.nodes.active = n

def bake_image(ob, name, size, kind, spp, float_buffer, colorspace, alpha=False, **kw):
    img = bpy.data.images.new(name, size, size, alpha=alpha, float_buffer=float_buffer)
    img.colorspace_settings.name = colorspace
    point_bake_at(ob, img)
    select_only(ob)
    s = bpy.context.scene
    s.cycles.samples = spp
    s.render.bake.target = 'IMAGE_TEXTURES'
    t0 = time.time()
    bpy.ops.object.bake(type=kind, margin=MARGIN_PX, margin_type='EXTEND', use_clear=True,
                        target='IMAGE_TEXTURES', **kw)
    log(f'  {name} {size}px {spp}spp {time.time() - t0:.0f}s')
    return img

def pixels(img):
    a = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(img.size[1], img.size[0], 4)

def save_png(name, arr, path, colorspace):
    h, w, _ = arr.shape
    img = bpy.data.images.new(name, w, h, alpha=True, float_buffer=False)
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(np.ascontiguousarray(arr, dtype=np.float32).ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)

def bake_atlas(name, info):
    ob = bpy.data.objects[name]
    color_path = os.path.join(BAKE_DIR, f'{name}_color.png')
    light_path = os.path.join(BAKE_DIR, f'{name}_light.png')
    if not os.path.exists(color_path):
        c = bake_image(ob, f'{name}_c', info['color'], 'DIFFUSE', 4, False, 'sRGB', alpha=True,
                       pass_filter={'COLOR'})
        r = bake_image(ob, f'{name}_r', info['color'], 'ROUGHNESS', 1, False, 'Non-Color')
        cp, rp = pixels(c), pixels(r)
        cp[:, :, 3] = rp[:, :, 0]  # roughness rides in the colour map's alpha
        save_png(f'{name}_cs', cp, color_path, 'sRGB')
        bpy.data.images.remove(c)
        bpy.data.images.remove(r)
    if not os.path.exists(light_path):
        n = bake_image(ob, f'{name}_n', info['light'], 'NORMAL', 1, True, 'Non-Color', normal_space='OBJECT')
        npx = pixels(n)[:, :, :3] * 2 - 1
        bpy.data.images.remove(n)
        L = bake_image(ob, f'{name}_l', info['light'], 'DIFFUSE', LIGHT_SPP, True, 'Non-Color',
                       pass_filter={'DIRECT', 'INDIRECT'})
        lp = pixels(L)[:, :, :3]
        bpy.data.images.remove(L)
        t0 = time.time()
        den = R.denoise(np.nan_to_num(lp), normal=npx, albedo=np.ones_like(lp))
        log(f'  {name} denoised {time.time() - t0:.0f}s, median {float(np.median(den)):.3f} p99 {float(np.percentile(den, 99)):.2f}')
        enc = np.ones(den.shape[:2] + (4,), dtype=np.float32)
        enc[:, :, :3] = np.sqrt(np.clip(den / LIGHT_SCALE, 0, 1))
        save_png(f'{name}_ls', enc, light_path, 'Non-Color')
        # keep the raw (noisy) bake too, for comparisons
        raw = np.ones_like(enc)
        raw[:, :, :3] = np.sqrt(np.clip(np.nan_to_num(lp) / LIGHT_SCALE, 0, 1))
        save_png(f'{name}_lr', raw, os.path.join(BAKE_DIR, f'{name}_light_raw.png'), 'Non-Color')

def smooth_colors(me, arr, k=0.5):
    ev = np.empty(len(me.edges) * 2, dtype=np.int64)
    me.edges.foreach_get('vertices', ev)
    ev = ev.reshape(-1, 2)
    acc = np.zeros_like(arr)
    cnt = np.zeros(len(arr))
    np.add.at(acc, ev[:, 0], arr[ev[:, 1]])
    np.add.at(acc, ev[:, 1], arr[ev[:, 0]])
    np.add.at(cnt, ev[:, 0], 1)
    np.add.at(cnt, ev[:, 1], 1)
    nb = acc / np.maximum(cnt, 1)[:, None]
    return np.where(cnt[:, None] > 0, arr * (1 - k) + nb * k, arr)

def bake_vertex(name):
    path = os.path.join(BAKE_DIR, f'{name}_vlight.npy')
    if os.path.exists(path):
        return
    ob = bpy.data.objects[name]
    ca = ob.data.color_attributes.new('Light', 'FLOAT_COLOR', 'POINT')
    ob.data.color_attributes.active_color = ca
    select_only(ob)
    s = bpy.context.scene
    s.cycles.samples = VERTEX_SPP
    s.render.bake.target = 'VERTEX_COLORS'
    t0 = time.time()
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR', 'DIRECT', 'INDIRECT'}, target='VERTEX_COLORS', use_clear=True)
    a = np.empty(len(ca.data) * 4, dtype=np.float32)
    ca.data.foreach_get('color', a)
    rgb = smooth_colors(ob.data, np.nan_to_num(a.reshape(-1, 4)[:, :3].astype(np.float64)))
    np.save(path, np.sqrt(np.clip(rgb / LIGHT_SCALE, 0, 1)).astype(np.float32))
    log(f'  {name} vertex colour x light {len(ob.data.vertices)} verts {time.time() - t0:.0f}s')

def stage_bake():
    meta = json.load(open(os.path.join(WORK, 'prep.json')))
    s = bpy.context.scene
    s.render.engine = 'CYCLES'
    s.cycles.device = 'CPU'
    s.cycles.use_denoising = False
    only = set(ARGS[ARGS.index('--only') + 1].split(',')) if '--only' in ARGS else None
    atl = meta['atlases']
    for name in sorted(atl, key=lambda n: atl[n]['light'] ** 2):
        if only and name not in only:
            continue
        log('atlas', name, atl[name])
        bake_atlas(name, atl[name])
    for name, kind in sorted(meta['objects'].items()):
        if kind == 'vertex' and (not only or name in only):
            log('vertex', name)
            bake_vertex(name)
    log('BAKE_DONE')

# ================================================================ 3. export
def stage_export():
    meta = json.load(open(os.path.join(WORK, 'prep.json')))
    s = bpy.context.scene
    os.makedirs(OUT, exist_ok=True)
    made = meta['objects']
    for name, kind in made.items():
        ob = bpy.data.objects.get(name)
        if not ob:
            continue
        me = ob.data
        # only the baked light travels as a vertex colour
        for ca in list(me.color_attributes):
            me.color_attributes.remove(ca)
        if kind == 'vertex':
            path = os.path.join(BAKE_DIR, f'{name}_vlight.npy')
            if os.path.exists(path):
                rgb = np.load(path)
                ca = me.color_attributes.new('Light', 'FLOAT_COLOR', 'POINT')
                a = np.ones((len(rgb), 4), dtype=np.float32)
                a[:, :3] = rgb
                ca.data.foreach_set('color', a.ravel())
                me.color_attributes.active_color = ca
        if kind != 'atlas':
            while me.uv_layers:
                me.uv_layers.remove(me.uv_layers[0])
    for o in s.objects:
        o.select_set(False)
    for name in made:
        ob = bpy.data.objects.get(name)
        if ob:
            ob.hide_set(False)
            ob.select_set(True)
    props = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
    want = dict(filepath=os.path.join(OUT, 'halcyon.glb'), export_format='GLB', use_selection=True,
                export_apply=False, export_cameras=False, export_lights=False, export_animations=False,
                export_materials='EXPORT', export_image_format='NONE', export_texcoords=True,
                export_vertex_color='ACTIVE', export_extras=False, export_yup=True,
                export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
                export_draco_position_quantization=16, export_draco_normal_quantization=10,
                export_draco_texcoord_quantization=16, export_draco_color_quantization=12)
    bpy.ops.export_scene.gltf(**{k: v for k, v in want.items() if k in props})
    scene = {k: meta[k] for k in ('materials', 'lights', 'sun', 'forest', 'door', 'partition_gap', 'world', 'light_scale')}
    scene['atlases'] = {n: dict(color=f'{n}_color.webp', light=f'{n}_light.webp', size=[a['color'], a['light']])
                        for n, a in meta['atlases'].items()}
    scene['objects'] = made
    # the browser requests the model and every texture with this stamp: a new export never meets
    # cached files from an older one (their UVs differ after every prep)
    scene['build'] = time.strftime('%Y%m%d%H%M%S')
    with open(os.path.join(OUT, 'scene.json'), 'w') as fh:
        json.dump(scene, fh, separators=(',', ':'))
    log('EXPORT_DONE', round(os.path.getsize(os.path.join(OUT, 'halcyon.glb')) / 1e6, 2), 'MB')

if __name__ == '__main__':  # check_route.py imports partition_glass from here
    {'prep': stage_prep, 'bake': stage_bake, 'export': stage_export}[STAGE]()
