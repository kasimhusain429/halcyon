"""HALCYON residence — site: terraces, pool, fire pit, dock, lake, terrain, forest, mountains."""
import bpy, bmesh, math, random
from mathutils import Vector
import mathutils.noise as mnoise
from hlib import *
import interior as I

RS = random.Random(42)
WATER_Z = -2.2

# ---------------------------------------------------------------- terrain function
def fbm(x, y, octaves=5, lac=2.0, gain=0.5, seed=0.0):
    a, f, s = 1.0, 1.0, 0.0
    for _ in range(octaves):
        s += a * mnoise.noise(Vector((x * f + seed, y * f - seed, seed * 0.37)))
        a *= gain
        f *= lac
    return s

def smooth(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)

def shore_y(x):
    ax = abs(x)
    base = -13.3 if ax < 24 else -13.3 + 0.0042 * (ax - 24) ** 2
    return base + (fbm(x / 40.0, 3.1, 3) * 4.0 if ax > 30 else 0.0)

def plateau_mask(x, y):
    mx = 1 - smooth(27, 40, abs(x - 1.0))
    my = (1 - smooth(26, 40, y)) if y >= 0 else (1 - smooth(-13.0, -13.4, y))
    return mx * max(0.0, min(1.0, my))

def height(x, y):
    d = y - shore_y(x)
    if d < 0:
        z = -2.9 - min(5.0, -d * 0.25) + fbm(x / 9, y / 9, 3) * 0.4
    else:
        bank = -2.7 + 3.1 * smooth(0, 7, d)
        rise = max(0.0, y - 28) * 0.11 + max(0.0, abs(x) - 70) * 0.06
        amp = 1.5 + 0.07 * max(0.0, y - 15) + 0.03 * max(0.0, abs(x) - 40)
        z = bank + rise + fbm(x / 70.0, y / 70.0, 5, seed=1.7) * amp + fbm(x / 7.0, y / 7.0, 3, seed=5.1) * 0.25
    pm = plateau_mask(x, y)
    return z * (1 - pm) + (-0.06) * pm

def axis_samples(lo, hi, center, s0=0.8, k=0.04):
    pts = [center]
    p = center
    while p < hi:
        p += s0 + k * (p - center)
        pts.append(min(p, hi))
    p = center
    while p > lo:
        p -= s0 + k * (center - p)
        pts.insert(0, max(p, lo))
    return pts

# ---------------------------------------------------------------- materials
def haze_mix(nt, shader_out, k=2600.0, col='#9fb0c4', strength=1.0, maxf=0.92):
    cd = N(nt, 'ShaderNodeCameraData')
    f = math_node(nt, 'MULTIPLY', cd.outputs['View Distance'], -1.0 / k)
    f = math_node(nt, 'EXPONENT', f)
    f = math_node(nt, 'SUBTRACT', 1.0, f)
    f = math_node(nt, 'MULTIPLY', f, maxf, clamp=True)
    em = N(nt, 'ShaderNodeEmission')
    em.inputs['Color'].default_value = srgb(col)
    em.inputs['Strength'].default_value = strength
    mx = N(nt, 'ShaderNodeMixShader')
    L(nt, f, mx.inputs[0]); L(nt, shader_out, mx.inputs[1]); L(nt, em.outputs[0], mx.inputs[2])
    return mx

HAZE = {'col': '#7f93ad', 'strength': 0.35}

def m_terrain():
    m, nt, out = new_mat('Terrain_Meadow')
    v = pos_vec(nt)
    geo = N(nt, 'ShaderNodeNewGeometry')
    sep = N(nt, 'ShaderNodeSeparateXYZ'); L(nt, geo.outputs['Normal'], sep.inputs[0])
    n1 = noise(nt, v, 0.06, 6, 0.6)
    n2 = noise(nt, v, 1.3, 8, 0.65)
    grass = ramp(nt, n1.outputs['Fac'], [(0.3, srgb('#22281a')), (0.5, srgb('#2f3620')), (0.7, srgb('#3d3b2a'))]).outputs['Color']
    grass = mix_rgb(nt, 0.25, grass, n2.outputs['Color'], 'OVERLAY')
    rock = ramp(nt, n2.outputs['Fac'], [(0.3, srgb('#4c4943')), (0.7, srgb('#7b766c'))]).outputs['Color']
    floor_ = srgb('#2c2a1d')
    steep = ramp(nt, sep.outputs['Z'], [(0.72, (1, 1, 1, 1)), (0.86, (0, 0, 0, 1))]).outputs['Color']
    c1 = mix_rgb(nt, math_node(nt, 'MULTIPLY', n1.outputs['Fac'], 0.6), grass, floor_)
    col = mix_rgb(nt, steep, c1, rock)
    # wet dark bank near the water line
    pz = N(nt, 'ShaderNodeSeparateXYZ'); L(nt, v, pz.inputs[0])
    col = mix_rgb(nt, math_node(nt, 'LESS_THAN', pz.outputs['Z'], -1.6), col, srgb('#24221d'))
    p = principled(nt, col, 0.92)
    L(nt, bump(nt, n2.outputs['Fac'], 0.4, 0.05), p.inputs['Normal'])
    mx = haze_mix(nt, p.outputs[0], 2200, HAZE['col'], HAZE['strength'])
    finish(nt, out, mx)
    return m

def m_mountain():
    m, nt, out = new_mat('Mountain_Snow')
    v = pos_vec(nt)
    geo = N(nt, 'ShaderNodeNewGeometry')
    sepn = N(nt, 'ShaderNodeSeparateXYZ'); L(nt, geo.outputs['Normal'], sepn.inputs[0])
    sepp = N(nt, 'ShaderNodeSeparateXYZ'); L(nt, v, sepp.inputs[0])
    n1 = noise(nt, scale_vec(nt, v, (0.004, 0.004, 0.012)), 1.0, 10, 0.62)
    n2 = noise(nt, v, 0.05, 8, 0.7)
    # snow where high and not too steep (+ noisy edges, streaks down gullies)
    hfac = math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', sepp.outputs['Z'], 1 / 420.0), math_node(nt, 'MULTIPLY', n1.outputs['Fac'], 0.9))
    flat = math_node(nt, 'ADD', sepn.outputs['Z'], math_node(nt, 'MULTIPLY', n2.outputs['Fac'], 0.35))
    snow = math_node(nt, 'MULTIPLY', ramp(nt, hfac, [(0.95, (0, 0, 0, 1)), (1.15, (1, 1, 1, 1))]).outputs['Color'],
                     ramp(nt, flat, [(0.58, (0, 0, 0, 1)), (0.72, (1, 1, 1, 1))]).outputs['Color'])
    rock = ramp(nt, n2.outputs['Fac'], [(0.35, srgb('#3e3b38')), (0.65, srgb('#6d675e'))]).outputs['Color']
    forest = mix_rgb(nt, n2.outputs['Fac'], srgb('#16201a'), srgb('#24301f'))
    low = ramp(nt, math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', sepp.outputs['Z'], 1 / 380.0), math_node(nt, 'MULTIPLY', n1.outputs['Fac'], 0.5)),
               [(0.55, (1, 1, 1, 1)), (0.75, (0, 0, 0, 1))]).outputs['Color']
    base = mix_rgb(nt, math_node(nt, 'MULTIPLY', low, ramp(nt, sepn.outputs['Z'], [(0.55, (0, 0, 0, 1)), (0.7, (1, 1, 1, 1))]).outputs['Color']), rock, forest)
    col = mix_rgb(nt, snow, base, srgb('#d9dee6'))
    rgh = math_node(nt, 'ADD', 0.75, math_node(nt, 'MULTIPLY', snow, -0.35))
    p = principled(nt, col, rgh)
    L(nt, bump(nt, n2.outputs['Fac'], 0.35, 2.0), p.inputs['Normal'])
    mx = haze_mix(nt, p.outputs[0], 2900, HAZE['col'], HAZE['strength'], 0.8)
    finish(nt, out, mx)
    return m

def m_hills():
    m, nt, out = new_mat('Hills_Forest')
    v = pos_vec(nt)
    n1 = noise(nt, v, 0.08, 6, 0.7)
    n2 = noise(nt, v, 0.9, 4, 0.6)
    col = ramp(nt, math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', n1.outputs['Fac'], 0.7), math_node(nt, 'MULTIPLY', n2.outputs['Fac'], 0.3)),
               [(0.35, srgb('#121a14')), (0.55, srgb('#1e2a1d')), (0.72, srgb('#33402a'))]).outputs['Color']
    p = principled(nt, col, 0.9)
    L(nt, bump(nt, n2.outputs['Fac'], 0.8, 1.5), p.inputs['Normal'])
    mx = haze_mix(nt, p.outputs[0], 3000, HAZE['col'], HAZE['strength'], 0.9)
    finish(nt, out, mx)
    return m

def m_conifer():
    m, nt, out = new_mat('Conifer_Foliage')
    oi = N(nt, 'ShaderNodeObjectInfo')
    v = pos_vec(nt)
    n = noise(nt, v, 3.0, 5, 0.6)
    base = ramp(nt, oi.outputs['Random'], [(0.0, srgb('#1b2a1c')), (0.35, srgb('#22331f')), (0.7, srgb('#2b3a25')), (1.0, srgb('#1f2b22'))]).outputs['Color']
    col = mix_rgb(nt, math_node(nt, 'MULTIPLY', n.outputs['Fac'], 0.5), base, srgb('#0f170f'))
    p = principled(nt, col, 0.62)
    L(nt, bump(nt, n.outputs['Fac'], 0.6, 0.1), p.inputs['Normal'])
    tl = N(nt, 'ShaderNodeBsdfTranslucent'); tl.inputs['Color'].default_value = srgb('#3a4a22')
    mx0 = N(nt, 'ShaderNodeMixShader'); mx0.inputs[0].default_value = 0.12
    L(nt, p.outputs[0], mx0.inputs[1]); L(nt, tl.outputs[0], mx0.inputs[2])
    mx = haze_mix(nt, mx0.outputs[0], 2200, HAZE['col'], HAZE['strength'])
    finish(nt, out, mx)
    return m

def m_rock():
    m, nt, out = new_mat('Rock_Granite')
    v = pos_vec(nt, 'object')
    n1 = noise(nt, v, 2.0, 10, 0.65)
    vor = N(nt, 'ShaderNodeTexVoronoi', feature='F1'); L(nt, v, vor.inputs['Vector']); vor.inputs['Scale'].default_value = 6
    n3 = noise(nt, v, 0.7, 4, 0.5)
    col = ramp(nt, n1.outputs['Fac'], [(0.35, srgb('#3f3d39')), (0.6, srgb('#625e57')), (0.8, srgb('#77726a'))]).outputs['Color']
    lich = ramp(nt, n3.outputs['Fac'], [(0.62, (0, 0, 0, 1)), (0.7, (1, 1, 1, 1))]).outputs['Color']
    col = mix_rgb(nt, math_node(nt, 'MULTIPLY', lich, 0.6), col, srgb('#7b7a55'))
    p = principled(nt, col, 0.82)
    h = math_node(nt, 'ADD', n1.outputs['Fac'], math_node(nt, 'MULTIPLY', vor.outputs['Distance'], 0.6))
    L(nt, bump(nt, h, 0.7, 0.08), p.inputs['Normal'])
    finish(nt, out, p)
    return m

def m_lake():
    m, nt, out = new_mat('Lake_Water')
    v = pos_vec(nt)
    n1 = noise(nt, scale_vec(nt, v, (0.05, 0.9, 1.0)), 1.0, 6, 0.55)
    n2 = noise(nt, scale_vec(nt, v, (0.6, 6.0, 1.0)), 1.0, 4, 0.5)
    h = math_node(nt, 'ADD', n1.outputs['Fac'], math_node(nt, 'MULTIPLY', n2.outputs['Fac'], 0.3))
    p = principled(nt, srgb('#081419'), 0.035, **{'IOR': 1.333, 'Specular IOR Level': 0.5})
    L(nt, bump(nt, h, 0.12, 0.1), p.inputs['Normal'])
    finish(nt, out, p)
    return m

def m_pool_water():
    m, nt, out = new_mat('Pool_Water')
    v = pos_vec(nt)
    n = noise(nt, scale_vec(nt, v, (1.5, 1.5, 1.0)), 1.0, 4, 0.5)
    p = principled(nt, srgb('#d8f3f2'), 0.02, **{'Transmission Weight': 1.0, 'IOR': 1.333})
    L(nt, bump(nt, n.outputs['Fac'], 0.08, 0.05), p.inputs['Normal'])
    finish(nt, out, p)
    return m

def m_pool_tile():
    m, nt, out = new_mat('Pool_Mosaic')
    v = pos_vec(nt)
    vv = swizzle(nt, v, ('X+Y', 'Z', None))
    br = N(nt, 'ShaderNodeTexBrick', offset=0.0, offset_frequency=1, squash=1, squash_frequency=1)
    for k, val in {'Color1': srgb('#7fa6aa'), 'Color2': srgb('#a9c7c8'), 'Mortar': srgb('#dfe7e5'), 'Scale': 1.0, 'Mortar Size': 0.003,
                   'Bias': 0.0, 'Brick Width': 0.05, 'Row Height': 0.05}.items():
        br.inputs[k].default_value = val
    L(nt, vv, br.inputs['Vector'])
    p = principled(nt, None, 0.2, **{'Emission Color': srgb('#5fd3d0'), 'Emission Strength': 0.9})
    L(nt, br.outputs['Color'], p.inputs['Base Color'])
    finish(nt, out, p)
    return m

def m_grass_blade():
    m, nt, out = new_mat('Grass_Blade')
    oi = N(nt, 'ShaderNodeObjectInfo')
    col = ramp(nt, oi.outputs['Random'], [(0.0, srgb('#6b6a3a')), (0.5, srgb('#8a7f4c')), (1.0, srgb('#56623a'))]).outputs['Color']
    p = principled(nt, col, 0.6)
    tl = N(nt, 'ShaderNodeBsdfTranslucent'); tl.inputs['Color'].default_value = srgb('#b0a05a')
    mx = N(nt, 'ShaderNodeMixShader'); mx.inputs[0].default_value = 0.25
    L(nt, p.outputs[0], mx.inputs[1]); L(nt, tl.outputs[0], mx.inputs[2])
    finish(nt, out, mx)
    return m

def m_lawn_hair():
    m, nt, out = new_mat('Lawn_Hair')
    hi = N(nt, 'ShaderNodeHairInfo')
    col = mix_rgb(nt, hi.outputs['Random'], srgb('#3f4a24'), srgb('#5f6a33'))
    col = mix_rgb(nt, hi.outputs['Intercept'], srgb('#2a3018'), col)
    p = principled(nt, col, 0.6)
    finish(nt, out, p)
    return m

def m_boxwood():
    m, nt, out = new_mat('Boxwood')
    v = pos_vec(nt)
    vor = N(nt, 'ShaderNodeTexVoronoi', feature='F1'); L(nt, v, vor.inputs['Vector']); vor.inputs['Scale'].default_value = 60
    n = noise(nt, v, 4, 5, 0.6)
    col = ramp(nt, n.outputs['Fac'], [(0.35, srgb('#1f2d17')), (0.65, srgb('#3a4d26'))]).outputs['Color']
    p = principled(nt, col, 0.55)
    L(nt, bump(nt, vor.outputs['Distance'], 0.8, 0.02), p.inputs['Normal'])
    finish(nt, out, p)
    return m

# ---------------------------------------------------------------- generators
def make_conifer_mesh(name, H=18.0, R0=3.6, tiers=34, seed=0):
    rr = random.Random(seed)
    bm = bmesh.new()
    trunk_h = H * 0.12
    for t in range(tiers):
        u = t / (tiers - 1)
        z = trunk_h + (H - trunk_h) * (u ** 0.92)
        rad = R0 * (1 - u) ** 0.95 * rr.uniform(0.85, 1.12) + 0.15
        nb = max(5, int(11 * (1 - u) + 4))
        a0 = rr.uniform(0, 6.28)
        for b in range(nb):
            a = a0 + 2 * math.pi * b / nb + rr.uniform(-0.25, 0.25)
            ln = rad * rr.uniform(0.75, 1.1)
            d = Vector((math.cos(a), math.sin(a), 0))
            side = Vector((-d.y, d.x, 0))
            base = Vector((0, 0, z + rr.uniform(-0.3, 0.3)))
            droop = ln * rr.uniform(0.18, 0.42)
            tip = base + d * ln + Vector((0, 0, -droop))
            mid = base + d * ln * 0.55 + Vector((0, 0, -droop * 0.35))
            w = ln * rr.uniform(0.28, 0.4)
            L_ = mid + side * w
            Rr = mid - side * w
            top = mid + Vector((0, 0, ln * 0.12))
            bot = mid + Vector((0, 0, -ln * 0.1))
            vs = [bm.verts.new(p) for p in (base, L_, tip, Rr, top, bot)]
            for f in ((0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (0, 5, 1), (1, 5, 2), (2, 5, 3), (3, 5, 0)):
                try:
                    bm.faces.new([vs[i] for i in f])
                except ValueError:
                    pass
            # sub-fronds: ragged needle clusters along the branch
            for sfi in range(3):
                tt = rr.uniform(0.35, 0.9)
                sp_ = base.lerp(tip, tt) + Vector((0, 0, rr.uniform(-0.15, 0.1)))
                sd = (d * rr.uniform(0.4, 0.8) + side * rr.choice((-1, 1)) * rr.uniform(0.5, 1.0)).normalized()
                sl = ln * rr.uniform(0.25, 0.4)
                st_ = sp_ + sd * sl + Vector((0, 0, -sl * 0.3))
                sw = Vector((-sd.y, sd.x, 0)) * sl * 0.3
                sm = sp_.lerp(st_, 0.5) + Vector((0, 0, sl * 0.12))
                try:
                    bm.faces.new([bm.verts.new(q) for q in (sp_, sm + sw, st_, sm - sw)])
                except ValueError:
                    pass
    # crown tip
    tipv = [bm.verts.new((0.18 * math.cos(a), 0.18 * math.sin(a), H - 1.2)) for a in (0, 2.1, 4.2)]
    apex = bm.verts.new((0, 0, H + 0.6))
    for i in range(3):
        bm.faces.new((tipv[i], tipv[(i + 1) % 3], apex))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(M('conifer'))
    # trunk as second material
    tr = bmesh.new()
    bmesh.ops.create_cone(tr, cap_ends=False, segments=8, radius1=0.35, radius2=0.08, depth=H * 0.9)
    bmesh.ops.translate(tr, verts=tr.verts, vec=(0, 0, H * 0.45))
    tme = bpy.data.meshes.new(name + '_trunk')
    tr.to_mesh(tme)
    tr.free()
    tob = bpy.data.objects.new('tmp_trunk', tme)
    fob = bpy.data.objects.new('tmp_fol', me)
    c = coll('_tmp')
    c.objects.link(tob); c.objects.link(fob)
    tme.materials.append(M('bark'))
    j = join([fob, tob], name)
    data = j.data
    for ob in list(c.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.collections.remove(c)
    return data

def make_rock_mesh(name, seed):
    rr = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=4, radius=1.0)
    off = Vector((rr.uniform(0, 100), rr.uniform(0, 100), rr.uniform(0, 100)))
    for v in bm.verts:
        p = v.co
        d = 1 + 0.35 * mnoise.noise(p * 0.9 + off) + 0.12 * mnoise.noise(p * 2.7 + off) + 0.04 * mnoise.noise(p * 7 + off)
        v.co = p * d
        v.co.z *= rr.uniform(0.55, 0.75)
        # flatten facets for a granite look
        if v.co.z < -0.2:
            v.co.z = -0.2 + (v.co.z + 0.2) * 0.3
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    me.materials.append(M('rock'))
    return me

def make_grass_clump(name, seed, blades=70, h=0.7):
    rr = random.Random(seed)
    bm = bmesh.new()
    for b in range(blades):
        a = rr.uniform(0, 6.28)
        r0 = rr.uniform(0, 0.12)
        base = Vector((r0 * math.cos(a), r0 * math.sin(a), 0))
        lean = Vector((math.cos(a), math.sin(a), 0)) * rr.uniform(0.15, 0.45)
        hh = h * rr.uniform(0.6, 1.1)
        side = Vector((-math.sin(a + 1.2), math.cos(a + 1.2), 0)) * 0.006
        prev = None
        segs = 4
        for s in range(segs + 1):
            t = s / segs
            p = base + lean * (t * t) * hh + Vector((0, 0, hh * t * (1 - 0.25 * t)))
            w = 1 - t
            l = bm.verts.new(p + side * w)
            r = bm.verts.new(p - side * w)
            if prev:
                bm.faces.new((prev[0], prev[1], r, l))
            prev = (l, r)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(M('grass_blade'))
    return me

def instance(name, mesh, c, loc, rotz=0.0, scale=1.0, sxyz=None):
    ob = bpy.data.objects.new(name, mesh)
    c.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (0, 0, rotz)
    ob.scale = sxyz or (scale, scale, scale)
    return ob

# ---------------------------------------------------------------- build parts
def build_hardscape(c):
    P, CP = M('paver'), M('coping')
    # main terrace (house front) and entry court
    box('S_terrace', -17.5, 3.4, -6.4, 0.0, -0.35, 0.0, P, c, 0.004)
    box('S_entrycourt', -3.0, 3.0, 0.0, 2.0, -0.35, 0.0, P, c, 0.004)
    box('S_eastdeck', 3.4, 21.0, -2.6, 0.0, -0.35, 0.0, P, c, 0.004)
    # pool deck + pool
    px0, px1, py0, py1 = 5.6, 19.2, -11.8, -7.2
    box('S_deckN', 3.4, 21.0, -6.8, -2.6, -0.35, 0.0, P, c, 0.004)
    box('S_deckS', 3.4, 21.0, -13.0, -12.2, -0.35, 0.0, P, c, 0.004)
    box('S_deckW', 3.4, px0 - 0.4, -12.2, -6.8, -0.35, 0.0, P, c, 0.004)
    box('S_deckE', px1 + 0.4, 21.0, -12.2, -6.8, -0.35, 0.0, P, c, 0.004)
    box('S_copN', px0 - 0.4, px1 + 0.4, py1, py1 + 0.4, -0.3, 0.03, CP, c, 0.006)
    box('S_copS', px0 - 0.4, px1 + 0.4, py0 - 0.4, py0, -0.3, 0.03, CP, c, 0.006)
    box('S_copW', px0 - 0.4, px0, py0, py1, -0.3, 0.03, CP, c, 0.006)
    box('S_copE', px1, px1 + 0.4, py0, py1, -0.3, 0.03, CP, c, 0.006)
    T = M('pool_tile')
    box('S_poolfloor', px0, px1, py0, py1, -1.6, -1.5, T, c, 0)
    box('S_poolwN', px0, px1, py1 - 0.02, py1, -1.6, 0.0, T, c, 0)
    box('S_poolwS', px0, px1, py0, py0 + 0.02, -1.6, 0.0, T, c, 0)
    box('S_poolwW', px0, px0 + 0.02, py0, py1, -1.6, 0.0, T, c, 0)
    box('S_poolwE', px1 - 0.02, px1, py0, py1, -1.6, 0.0, T, c, 0)
    plane('S_poolwater', px0, px1, py0, py1, -0.09, M('pool_water'), c)
    # sun loungers on the deck (south side, facing the lake)
    for k, x in enumerate((7.0, 9.0, 11.0)):
        g = I.grp(f'S_lounger{k}', (x, -5.0, 0), 0, c)
        I.par(box(f'S_loungerFrame{k}', -0.36, 0.36, -1.0, 1.0, 0.0, 0.3, M('oak'), c, 0.01), g)
        I.par(box(f'S_loungerPad{k}', -0.33, 0.33, -0.97, 0.45, 0.3, 0.38, M('fabric_cream'), c, 0.03, 3), g)
        bk = box(f'S_loungerBack{k}', -0.33, 0.33, 0.0, 0.62, 0.0, 0.08, M('fabric_cream'), c, 0.03, 3)
        bk.location = (0, 0.42, 0.34); bk.rotation_euler = (math.radians(38), 0, 0)
        I.par(bk, g)
    # retaining wall to the lake + steps + dock
    S = M('stone_ext')
    box('S_retain', -26.0, 27.0, -13.7, -13.0, WATER_Z - 0.8, 0.05, S, c, 0.01)
    box('S_retaincap', -26.0, 27.0, -13.78, -12.95, 0.05, 0.12, CP, c, 0.006)
    for side, x0 in (('W', -26.6), ('E', 27.0)):
        box(f'S_retainRet{side}', x0, x0 + 0.6, -13.7, -4.0, WATER_Z - 0.8, 0.05, S, c, 0.01)
    nsteps = 9
    for i in range(nsteps):
        z1 = -0.0 - (i + 1) * (1.75 / nsteps)
        box(f'S_step{i}', -1.7, 1.7, -13.7 - (i + 1) * 0.38, -13.7 - i * 0.38, WATER_Z - 0.8, z1 + 0.05, CP, c, 0.006)
    dy0, dy1 = -13.7 - nsteps * 0.38, -31.0
    box('S_dock', -1.8, 1.8, dy1, dy0, -1.82, -1.72, M('dock_wood'), c, 0.005)
    for k, y in enumerate((dy0 - 1.0, (dy0 + dy1) / 2, dy1 + 0.3)):
        for x in (-1.6, 1.6):
            cyl(f'S_post{k}{x}', 0.12, 2.2, (x, y, -2.8), M('beam_dark'), c, 12, bev=0.01)
    lc = coll('Exterior_Lights')
    for k, x in enumerate((-1.55, 1.55)):
        box(f'S_lantern{k}', x - 0.09, x + 0.09, dy1 + 0.2, dy1 + 0.38, -1.72, -0.95, M('metal_dark'), c, 0.006)
        box(f'S_lanternGlow{k}', x - 0.07, x + 0.07, dy1 + 0.22, dy1 + 0.36, -1.15, -1.0, M('warm_light'), c, 0)
        I.point(f'S_lanternL{k}', (x, dy1 + 0.29, -1.08), 25, 2600, lc, 0.05)
    # lawn (west front) + fire-pit lounge
    fx, fy = -9.0, -9.7
    # lawn as a grid with a hole for the fire-pit deck (hair grows from faces)
    lv, lf, idx = [], [], {}
    xs_ = [-26.0 + i for i in range(30)] + [3.4]
    ys_ = [-13.0 + 0.5 * j for j in range(14)]
    ys_[-1] = -6.4
    for j, yy in enumerate(ys_):
        for i, xx in enumerate(xs_):
            idx[(i, j)] = len(lv)
            lv.append((xx, yy, -0.04))
    for j in range(len(ys_) - 1):
        for i in range(len(xs_) - 1):
            cx_, cy_ = (xs_[i] + xs_[i + 1]) / 2, (ys_[j] + ys_[j + 1]) / 2
            if abs(cx_ - fx) < 3.7 and abs(cy_ - fy) < 2.5:
                continue
            lf.append((idx[(i, j)], idx[(i + 1, j)], idx[(i + 1, j + 1)], idx[(i, j + 1)]))
    mesh_obj('S_lawn', lv, lf, c, M('lawn'))
    box('S_lawnbase', -26.0, 3.4, -13.0, -6.4, -0.6, -0.045, M('soil'), c, 0)
    box('S_firedeck', fx - 3.6, fx + 3.6, fy - 2.4, fy + 2.4, -0.4, 0.0, P, c, 0.004)
    I.lathe('S_firepit', [(0.0, 0.0), (1.0, 0.0), (1.0, 0.42), (0.78, 0.42), (0.78, 0.3), (0.0, 0.3)], c, M('concrete'), 64, (fx, fy, 0))
    I.lathe('S_fireglass', [(0.0, 0.3), (0.74, 0.3), (0.74, 0.34), (0.0, 0.34)], c, M('black_glass'), 48, (fx, fy, 0))
    for k in range(3):
        a = k * math.pi / 3
        fl = vplane(f'S_flame{k}', (fx - 0.55 * math.cos(a), fy - 0.55 * math.sin(a)), (fx + 0.55 * math.cos(a), fy + 0.55 * math.sin(a)), 0.32, 0.95, M('flames'), c)
    I.point('S_fireL', (fx, fy, 0.6), 380, 1900, lc, 0.3)
    I.sofa('S_firesofaW', 2.8, 0.95, c, M('fabric_sand'), (fx - 2.6, fy, 0), math.pi / 2, legmat=M('metal_dark'))
    I.sofa('S_firesofaE', 2.8, 0.95, c, M('fabric_sand'), (fx + 2.6, fy, 0), -math.pi / 2, legmat=M('metal_dark'))
    # pool lights
    for k in range(5):
        x = px0 + (px1 - px0) * (k + 0.5) / 5
        cyl(f'S_poollamp{k}', 0.1, 0.02, (x, py1 - 0.03, -0.55), M('warm_light'), c, 24, rot=(math.pi / 2, 0, 0), bev=0)
        I.spot(f'S_poolL{k}', (x, py1 - 0.1, -0.55), 160, 110, 0.9, 5200, lc, aim=(x, py0, -1.4), radius=0.1)
    # bollard path lights along the terrace edge
    for k, x in enumerate((-16.5, -13.0, -5.0, -1.2, 1.2)):
        cyl(f'S_bollard{k}', 0.07, 0.6, (x, -6.8, 0.3), M('metal_dark'), c, 16, bev=0.004)
        cyl(f'S_bollardGlow{k}', 0.06, 0.06, (x, -6.8, 0.52), M('warm_soft'), c, 16, bev=0)
        I.point(f'S_bollardL{k}', (x, -6.8, 0.5), 8, 2700, lc, 0.04)

def build_planting(c):
    rock_meshes = [make_rock_mesh(f'RockMesh{i}', i) for i in range(6)]
    grass_meshes = [make_grass_clump(f'GrassMesh{i}', i) for i in range(4)]
    box_meshes = []
    for i in range(3):
        ob = sphere(f'BoxwoodMesh{i}', 0.5, (0, 0, 0), M('boxwood'), coll('_tmpb'), 3)
        for v in ob.data.vertices:
            v.co *= 1 + 0.12 * mnoise.noise(v.co * 4 + Vector((i * 3, 0, 0)))
        box_meshes.append(ob.data)
        bpy.data.objects.remove(ob)
    bpy.data.collections.remove(bpy.data.collections['_tmpb'])
    rc = coll('Rocks', c)
    # boulders along the lake shore in front of the wall and around the sides
    for i in range(70):
        x = RS.uniform(-34, 36)
        y = -13.9 - RS.uniform(0, 2.6) if abs(x) < 26 else shore_y(x) + RS.uniform(-2, 1.5)
        if abs(x) < 2.6:
            continue
        s = RS.uniform(0.5, 1.6)
        z = WATER_Z - 0.2 * s if abs(x) < 26 else height(x, y) - 0.25 * s
        instance(f'Rock{i}', rock_meshes[i % 6], rc, (x, y, z), RS.uniform(0, 6.28), sxyz=(s * RS.uniform(0.9, 1.5), s, s))
    # lawn-edge boulders & grasses (like an alpine rock garden)
    gc = coll('Grasses', c)
    for i in range(46):
        x = RS.uniform(-25, 3)
        y = RS.uniform(-12.9, -12.0)
        instance(f'Grass{i}', grass_meshes[i % 4], gc, (x, y, -0.05), RS.uniform(0, 6.28), RS.uniform(0.8, 1.3))
    for i in range(26):
        x = RS.uniform(-25, 2.5)
        y = RS.uniform(-12.8, -11.6)
        if abs(x + 9) < 4:
            continue
        s = RS.uniform(0.35, 0.8)
        instance(f'LawnRock{i}', rock_meshes[(i + 2) % 6], rc, (x, y, -0.1), RS.uniform(0, 6.28), s)
    bc = coll('Shrubs', c)
    for i in range(40):
        side = RS.choice((-1, 1))
        x = RS.uniform(-26, -18) if side < 0 else RS.uniform(21.2, 27)
        y = RS.uniform(-12.5, 14)
        s = RS.uniform(0.5, 1.2)
        instance(f'Shrub{i}', box_meshes[i % 3], bc, (x, y, height(x, y) + 0.25 * s), RS.uniform(0, 6.28), sxyz=(s * 1.2, s * 1.2, s))
    # planting strip along the entry court and pool deck edges
    for i in range(18):
        x = RS.uniform(3.6, 20.8)
        instance(f'DeckGrass{i}', grass_meshes[i % 4], gc, (x, RS.uniform(-12.95, -12.3), 0.0), RS.uniform(0, 6.28), RS.uniform(0.7, 1.1))
    return rock_meshes

def build_lawn_hair(lawn):
    ps_mod = lawn.modifiers.new('LawnHair', 'PARTICLE_SYSTEM')
    ps = lawn.particle_systems[0]
    st = ps.settings
    st.type = 'HAIR'
    st.count = 30000
    st.hair_length = 0.09
    st.use_advanced_hair = True
    st.emit_from = 'FACE'
    st.child_type = 'INTERPOLATED'
    st.child_percent = 6
    st.rendered_child_count = 6
    st.child_length = 1.0
    st.roughness_2 = 0.08
    st.roughness_endpoint = 0.04
    st.factor_random = 0.4
    st.brownian_factor = 0.02
    st.normal_factor = 1.0
    st.material_slot = 'Lawn_Hair'
    st.root_radius = 0.0012
    st.tip_radius = 0.0
    st.radius_scale = 1.0
    try:
        st.hair_step = 3
        st.render_step = 3
        st.display_step = 2
    except Exception:
        pass

POOL_HOLE = (5.2, 19.6, -12.2, -6.8)  # outer edge of the pool coping

def build_terrain(c):
    hx0, hx1, hy0, hy1 = POOL_HOLE
    # grid lines on the coping edge so the pool opening is a clean rectangle
    xs = sorted(set(axis_samples(-460, 460, 0.0, 1.0, 0.045) + [hx0, hx1]))
    ys = sorted(set(axis_samples(-90, 560, 0.0, 1.0, 0.045) + [hy0, hy1]))
    verts = [(x, y, height(x, y)) for y in ys for x in xs]
    nx = len(xs)
    faces = []
    for j in range(len(ys) - 1):
        for i in range(nx - 1):
            cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            if hx0 < cx < hx1 and hy0 < cy < hy1:
                continue  # leave the pool basin open
            a = j * nx + i
            faces.append((a, a + 1, a + nx + 1, a + nx))
    ob = mesh_obj('Terrain', verts, faces, c, M('terrain'), True)
    return ob

def build_far(c):
    # foothills ring (forested)
    xs = [x for x in axis_samples(-3200, 3200, 0, 6.0, 0.03)]
    ys = [y for y in axis_samples(480, 2000, 480, 6.0, 0.012)]
    verts = []
    for y in ys:
        for x in xs:
            env = smooth(480, 900, y)
            hz = env * (90 + 160 * smooth(800, 1900, y)) * (0.55 + 0.45 * fbm(x / 600, y / 600, 4, seed=9.3)) \
                 + fbm(x / 120, y / 120, 4, seed=2.2) * 18 * env + 55
            verts.append((x, y, hz))
    nx = len(xs)
    faces = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i) for j in range(len(ys) - 1) for i in range(nx - 1)]
    mesh_obj('Foothills', verts, faces, c, M('hills'), True)
    # alpine range (ridged)
    xs = axis_samples(-6500, 6500, 0, 12.0, 0.012)
    ys = axis_samples(1700, 7500, 2300, 12.0, 0.012)
    raw = []
    for y in ys:
        for x in xs:
            p = Vector((x / 2900.0, y / 2900.0, 0.31))
            raw.append(mnoise.ridged_multi_fractal(p, 0.95, 2.1, 8, 1.0, 2.1, noise_basis='PERLIN_ORIGINAL'))
    srt = sorted(raw)
    lo, hi = srt[int(len(srt) * 0.2)], srt[int(len(srt) * 0.995)]
    verts = []
    k = 0
    for y in ys:
        for x in xs:
            r = max(0.0, (raw[k] - lo) / (hi - lo))
            k += 1
            env = smooth(1700, 3300, y) * (0.75 + 0.25 * math.cos(x / 5200.0))
            peak = 1 + 0.45 * math.exp(-((x + 600) / 2600) ** 2) * smooth(2200, 3600, y)
            hz = (r ** 1.5) * 980 * env * peak + 60 + fbm(x / 300, y / 300, 3, seed=4.4) * 30 * env
            verts.append((x, y, hz))
    nx = len(xs)
    faces = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i) for j in range(len(ys) - 1) for i in range(nx - 1)]
    mesh_obj('Alps', verts, faces, c, M('mountain'), True)

def build_forest(c):
    variants = [make_conifer_mesh(f'ConiferMesh{i}', H=RS.uniform(15, 22), R0=RS.uniform(2.8, 4.0), seed=i * 7 + 1) for i in range(6)]
    n = 0
    tries = 0
    while n < 2600 and tries < 40000:
        tries += 1
        x = RS.uniform(-440, 440)
        y = RS.uniform(-60, 540)
        d = y - shore_y(x)
        if d < 4.0:
            continue
        # keep the residence clear and the hero sightline open
        if abs(x - 1) < 32 and y < 30:
            continue
        if abs(x - 1) < 24 and y < 40:
            continue
        # view corridor from the study window to the peaks
        if 7 < x < 30 and y < 260:
            continue
        dens = 0.35 + 0.65 * smooth(20, 120, y) if abs(x) < 120 else 0.85
        if RS.random() > dens:
            continue
        z = height(x, y)
        s = RS.uniform(0.65, 1.2) * (1.0 - 0.25 * (1 - smooth(40, 160, y)) * (1 if abs(x) < 70 else 0))
        instance(f'Tree{n}', variants[n % 6], c, (x, y, z - 0.3), RS.uniform(0, 6.28), sxyz=(s * RS.uniform(0.85, 1.15), s * RS.uniform(0.85, 1.15), s))
        n += 1
    # framing clusters close to the house
    for k in range(40):
        side = -1 if k % 2 == 0 else 1
        x = (RS.uniform(-58, -33) if side < 0 else RS.uniform(34, 62))
        y = RS.uniform(-8, 40)
        if y - shore_y(x) < 4:
            continue
        s = RS.uniform(0.9, 1.4)
        instance(f'TreeNear{k}', variants[k % 6], c, (x, y, height(x, y) - 0.3), RS.uniform(0, 6.28), s)
    return n

def build():
    MATS['terrain'] = m_terrain()
    MATS['mountain'] = m_mountain()
    MATS['hills'] = m_hills()
    MATS['conifer'] = m_conifer()
    MATS['rock'] = m_rock()
    MATS['lake'] = m_lake()
    MATS['pool_water'] = m_pool_water()
    MATS['pool_tile'] = m_pool_tile()
    MATS['grass_blade'] = m_grass_blade()
    MATS['lawn_hair'] = m_lawn_hair()
    MATS['boxwood'] = m_boxwood()
    MATS['lawn'] = m_simple('Lawn_Base', srgb('#3c4524'), 0.9)
    MATS['dock_wood'] = m_wood_planks('Dock_Cedar', '#9a6a45', '#5c3b25', 0.15, 3.0, 'Y', 0.6, seam=0.008)
    c = coll('Site')
    build_hardscape(coll('Hardscape', c))
    build_planting(coll('Planting', c))
    plane('Lake', -6000, 6000, -6000, 400, WATER_Z, M('lake'), coll('Water', c))
    build_terrain(coll('Terrain', c))
    far = coll('Far', c)
    build_far(far)
    fc = coll('Forest', c)
    build_forest(fc)
    fc.hide_viewport = True
