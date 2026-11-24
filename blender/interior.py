"""HALCYON residence — interiors: furniture, fixtures, decor and interior lighting."""
import bpy, bmesh, math, random
from mathutils import Vector, Euler
from hlib import *
import arch

R = random.Random(7)

# ---------------------------------------------------------------- lights
KELVIN_SHIFT = 650  # cooler, warm-white interiors (AgX pushes low K towards orange)

def kelvin_rgb(k, shift=True):
    if shift and k > 2200:
        k = k + KELVIN_SHIFT
    t = k / 100.0
    r = 255 if t <= 66 else 329.698727446 * ((t - 60) ** -0.1332047592)
    g = (99.4708025861 * math.log(t) - 161.1195681661) if t <= 66 else 288.1221695283 * ((t - 60) ** -0.0755148492)
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    out = []
    for v in (r, g, b):
        v = max(0, min(255, v)) / 255.0
        out.append(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
    return tuple(out)

def _light(name, kind, loc, power, kelvin, c, rot=(0, 0, 0)):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = power
    ld.color = kelvin_rgb(kelvin)
    ob = bpy.data.objects.new(name, ld)
    c.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = rot
    ob.visible_camera = False
    return ob

def area(name, loc, size, power, kelvin=2800, c=None, rot=(0, 0, 0), size_y=None, spread=180, glossy=True):
    ob = _light(name, 'AREA', loc, power, kelvin, c, rot)
    ld = ob.data
    ld.shape = 'RECTANGLE' if size_y else 'SQUARE'
    ld.size = size
    if size_y:
        ld.size_y = size_y
    ld.spread = math.radians(spread)
    ob.visible_glossy = glossy
    return ob

def spot(name, loc, power, angle=60, blend=0.6, kelvin=3000, c=None, aim=None, radius=0.03):
    ob = _light(name, 'SPOT', loc, power, kelvin, c)
    ob.data.spot_size = math.radians(angle)
    ob.data.spot_blend = blend
    ob.data.shadow_soft_size = radius
    d = (Vector(aim) - Vector(loc)) if aim else Vector((0, 0, -1))
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return ob

def point(name, loc, power, kelvin=2700, c=None, radius=0.05):
    ob = _light(name, 'POINT', loc, power, kelvin, c)
    ob.data.shadow_soft_size = radius
    if radius >= 0.1:
        ob.visible_glossy = False
    return ob

# ---------------------------------------------------------------- grouping
def grp(name, loc=(0, 0, 0), rz=0.0, c=None):
    e = bpy.data.objects.new(name, None)
    c.objects.link(e)
    e.location = loc
    e.rotation_euler = (0, 0, rz)
    e.empty_display_size = 0.3
    return e

def par(ob, g):
    ob.parent = g
    return ob

def lathe(name, profile, c, mat, seg=48, loc=(0, 0, 0), smooth=True, cap=True):
    """Spin a (r, z) profile around Z."""
    verts, faces = [], []
    n = len(profile)
    for i in range(seg):
        a = 2 * math.pi * i / seg
        ca, sa = math.cos(a), math.sin(a)
        for (r, z) in profile:
            verts.append((r * ca, r * sa, z))
    for i in range(seg):
        j = (i + 1) % seg
        for k in range(n - 1):
            faces.append((i * n + k, j * n + k, j * n + k + 1, i * n + k + 1))
    if cap and profile[0][0] > 0:
        verts.append((0, 0, profile[0][1]))
        ci = len(verts) - 1
        for i in range(seg):
            j = (i + 1) % seg
            faces.append((j * n, i * n, ci))
    ob = mesh_obj(name, verts, faces, c, mat, smooth)
    ob.location = loc
    return ob

# ---------------------------------------------------------------- furniture
def sofa(name, length, depth, c, fabric, loc, rz, arms=True, legmat=None):
    g = grp(name, loc, rz, c)
    hl, hd = length / 2, depth / 2
    legmat = legmat or M('metal_dark')
    par(box(f'{name}_plinth', -hl + 0.06, hl - 0.06, -hd + 0.06, hd - 0.06, 0.0, 0.07, legmat, c, 0.005), g)
    par(box(f'{name}_base', -hl, hl, -hd, hd, 0.07, 0.36, fabric, c, 0.03, 3), g)
    aw = 0.2 if arms else 0.0
    if arms:
        par(box(f'{name}_armL', -hl, -hl + aw, -hd, hd, 0.36, 0.6, fabric, c, 0.05, 4), g)
        par(box(f'{name}_armR', hl - aw, hl, -hd, hd, 0.36, 0.6, fabric, c, 0.05, 4), g)
    par(box(f'{name}_back', -hl + aw, hl - aw, hd - 0.2, hd, 0.36, 0.74, fabric, c, 0.05, 4), g)
    n = max(1, round((length - 2 * aw) / 1.05))
    w = (length - 2 * aw) / n
    for i in range(n):
        x0 = -hl + aw + i * w
        par(box(f'{name}_seat{i}', x0 + 0.01, x0 + w - 0.01, -hd + 0.03, hd - 0.2, 0.36, 0.52, fabric, c, 0.06, 4), g)
        b = box(f'{name}_bk{i}', x0 + 0.02, x0 + w - 0.02, hd - 0.4, hd - 0.2, 0.5, 0.88, fabric, c, 0.08, 4)
        b.rotation_euler = (math.radians(-9), 0, 0)
        b.location = (0, 0.03, 0.06)
        par(b, g)
    for k, (xx, m) in enumerate(((-hl + aw + 0.35, M('fabric_olive')), (hl - aw - 0.38, M('fabric_sand')), (hl - aw - 0.72, M('fabric_olive')))):
        p = cbox(f'{name}_pillow{k}', (0.46, 0.14, 0.42), (xx, hd - 0.42, 0.74), m, c,
                 rot=(math.radians(-14), 0, math.radians(R.uniform(-8, 8))), bev=0.06, seg=4)
        par(p, g)
    return g

def lounge_chair(name, c, loc, rz, leather=None, frame=None):
    g = grp(name, loc, rz, c)
    leather = leather or M('leather')
    frame = frame or M('walnut')
    for sx in (-1, 1):
        par(box(f'{name}_side{sx}', sx * 0.4 - 0.03, sx * 0.4 + 0.03, -0.42, 0.42, 0.0, 0.55, frame, c, 0.012), g)
    par(box(f'{name}_seat', -0.37, 0.37, -0.42, 0.3, 0.2, 0.42, leather, c, 0.05, 4), g)
    bk = box(f'{name}_back', -0.37, 0.37, -0.1, 0.1, 0.0, 0.62, leather, c, 0.05, 4)
    bk.location = (0, 0.36, 0.3)
    bk.rotation_euler = (math.radians(-16), 0, 0)
    par(bk, g)
    return g

def dining_chair(name, c, loc, rz, fabric):
    g = grp(name, loc, rz, c)
    for sx in (-1, 1):
        for sy in (-1, 1):
            par(box(f'{name}_leg{sx}{sy}', sx * 0.22 - 0.018, sx * 0.22 + 0.018, sy * 0.22 - 0.018, sy * 0.22 + 0.018, 0, 0.44, M('walnut'), c, 0.004), g)
    par(box(f'{name}_seat', -0.25, 0.25, -0.25, 0.25, 0.42, 0.5, fabric, c, 0.03, 3), g)
    bk = box(f'{name}_back', -0.24, 0.24, -0.035, 0.035, 0.0, 0.38, fabric, c, 0.03, 3)
    bk.location = (0, 0.24, 0.52)
    bk.rotation_euler = (math.radians(-8), 0, 0)
    par(bk, g)
    return g

def stool(name, c, loc):
    g = grp(name, loc, 0, c)
    par(cyl(f'{name}_seat', 0.2, 0.07, (0, 0, 0.74), M('leather'), c, 32, bev=0.02), g)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        lg = cyl(f'{name}_leg{k}', 0.012, 0.76, (0.13 * math.cos(a), 0.13 * math.sin(a), 0.37), M('brass'), c, 10, bev=0,
                 rot=(math.radians(6) * math.sin(a), -math.radians(6) * math.cos(a), 0))
        par(lg, g)
    par(torus(f'{name}_ring', 0.15, 0.008, (0, 0, 0.28), M('brass'), c, maj=40, minr=8), g)
    return g

def table_lamp(name, c, loc, lc, power=18):
    g = grp(name, loc, 0, c)
    par(lathe(f'{name}_base', [(0.0, 0.0), (0.07, 0.0), (0.1, 0.06), (0.11, 0.16), (0.08, 0.28), (0.02, 0.33), (0.0, 0.34)], c, M('ceramic'), 40), g)
    par(cyl(f'{name}_stem', 0.008, 0.12, (0, 0, 0.39), M('brass'), c, 10, bev=0), g)
    sh = lathe(f'{name}_shade', [(0.19, 0.38), (0.15, 0.62)], c, M('shade_linen'), 48, cap=False)
    sh.modifiers.new('Solid', 'SOLIDIFY').thickness = 0.004
    par(sh, g)
    par(point(f'{name}_bulb', (0, 0, 0.5), power, 2600, lc, 0.04), g)
    return g

def floor_lamp_arc(name, c, loc, rz, lc):
    g = grp(name, loc, rz, c)
    par(cyl(f'{name}_base', 0.2, 0.06, (0, 0, 0.03), M('marble_dark'), c, 40, bev=0.01), g)
    cu = bpy.data.curves.new(f'{name}_arc', 'CURVE')
    cu.dimensions = '3D'
    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(1)
    p0, p1 = sp.bezier_points
    p0.co = (0, 0, 0.06); p0.handle_left = (0, 0, -0.5); p0.handle_right = (0, 0, 1.6)
    p1.co = (1.55, 0, 1.85); p1.handle_left = (0.9, 0, 2.3); p1.handle_right = (1.8, 0, 1.7)
    cu.bevel_depth = 0.012
    cu.bevel_resolution = 4
    cu.resolution_u = 24
    arc = bpy.data.objects.new(f'{name}_arc', cu)
    c.objects.link(arc)
    cu.materials.append(M('brass'))
    par(arc, g)
    sh = lathe(f'{name}_shade', [(0.001, 0.0), (0.12, -0.03), (0.22, -0.16), (0.23, -0.2)], c, M('brass'), 48, cap=False)
    sh.modifiers.new('Solid', 'SOLIDIFY').thickness = 0.006
    sh.location = (1.55, 0, 1.84)
    par(sh, g)
    par(cyl(f'{name}_diff', 0.2, 0.004, (1.55, 0, 1.66), M('warm_soft'), c, 32, bev=0), g)
    s = spot(f'{name}_spot', (1.55, 0, 1.64), 140, 95, 0.9, 2700, lc, radius=0.15)
    par(s, g)
    s.location = (1.55, 0, 1.64)
    s.rotation_euler = (0, 0, 0)
    return g

def olive_tree(name, c, loc, h=2.6, planter=True, seed=1, leafmat=None):
    rr = random.Random(seed)
    g = grp(name, loc, rr.uniform(0, 6.28), c)
    if planter:
        par(lathe(f'{name}_pot', [(0.0, 0.0), (0.3, 0.0), (0.36, 0.08), (0.36, 0.62), (0.33, 0.64), (0.0, 0.64)], c, M('concrete'), 48), g)
        par(cyl(f'{name}_soil', 0.32, 0.02, (0, 0, 0.62), M('soil'), c, 32, bev=0), g)
    base = 0.6 if planter else 0.0
    cu = bpy.data.curves.new(f'{name}_wood', 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = 1.0
    cu.bevel_resolution = 3
    cu.resolution_u = 8
    tips = []
    def branch(p0, d, length, rad, depth):
        sp = cu.splines.new('POLY')
        segs = 5
        sp.points.add(segs - 1)
        p = Vector(p0)
        dd = Vector(d).normalized()
        pts = []
        for i in range(segs):
            pts.append(p.copy())
            dd = (dd + Vector((rr.uniform(-0.25, 0.25), rr.uniform(-0.25, 0.25), rr.uniform(-0.05, 0.15)))).normalized()
            p = p + dd * (length / (segs - 1))
        for i, pt in enumerate(pts):
            sp.points[i].co = (pt.x, pt.y, pt.z, 1)
            sp.points[i].radius = rad * (1 - 0.6 * i / (segs - 1))
        if depth > 0:
            for k in range(rr.randint(2, 3)):
                idx = rr.randint(2, segs - 1)
                nd = (Vector(d) + Vector((rr.uniform(-1, 1), rr.uniform(-1, 1), rr.uniform(0.2, 0.9)))).normalized()
                branch(pts[idx], nd, length * rr.uniform(0.5, 0.75), rad * 0.55, depth - 1)
        else:
            tips.append(pts[-1])
            tips.append(pts[-2])
    branch((0, 0, base), (0.1, 0.05, 1), h * 0.55, 0.05, 2)
    wood = bpy.data.objects.new(f'{name}_wood', cu)
    c.objects.link(wood)
    cu.materials.append(M('bark'))
    par(wood, g)
    bm = bmesh.new()
    for tip in tips:
        for k in range(130):
            ctr = Vector(tip) + Vector((rr.gauss(0, 0.26), rr.gauss(0, 0.26), rr.gauss(0.06, 0.18)))
            ln = rr.uniform(0.09, 0.15)
            wd = ln * 0.18
            dirv = Vector((rr.uniform(-1, 1), rr.uniform(-1, 1), rr.uniform(-0.6, 0.4))).normalized()
            side = dirv.cross(Vector((0, 0, 1)))
            if side.length < 1e-3:
                side = Vector((1, 0, 0))
            side.normalize()
            up = side.cross(dirv).normalized()
            a = ctr
            b = ctr + dirv * ln
            m1 = ctr + dirv * ln * 0.5 + side * wd + up * ln * 0.08
            m2 = ctr + dirv * ln * 0.5 - side * wd + up * ln * 0.08
            bm.faces.new([bm.verts.new(v) for v in (a, m1, b, m2)])
    me = bpy.data.meshes.new(f'{name}_leaves')
    bm.to_mesh(me)
    bm.free()
    lv = bpy.data.objects.new(f'{name}_leaves', me)
    c.objects.link(lv)
    me.materials.append(leafmat or M('leaf_olive'))
    par(lv, g)
    return g

def fig_tree(name, c, loc, h=2.2, seed=3):
    """Fiddle-leaf fig: vertical stems with broad leaves."""
    rr = random.Random(seed)
    g = grp(name, loc, rr.uniform(0, 6.28), c)
    par(lathe(f'{name}_pot', [(0.0, 0.0), (0.22, 0.0), (0.27, 0.05), (0.3, 0.55), (0.0, 0.55)], c, M('ceramic'), 48), g)
    bm = bmesh.new()
    stems = []
    for s in range(3):
        base = Vector((rr.uniform(-0.08, 0.08), rr.uniform(-0.08, 0.08), 0.55))
        top = base + Vector((rr.uniform(-0.25, 0.25), rr.uniform(-0.25, 0.25), h * rr.uniform(0.7, 1.0) - 0.55))
        stems.append((base, top))
        for k in range(16):
            t = 0.25 + 0.75 * k / 15
            p = base.lerp(top, t)
            ang = rr.uniform(0, 6.28)
            out = Vector((math.cos(ang), math.sin(ang), 0))
            ln = rr.uniform(0.22, 0.34)
            wd = ln * 0.38
            tipv = (out * 0.85 + Vector((0, 0, rr.uniform(-0.1, 0.45)))).normalized()
            side = tipv.cross(Vector((0, 0, 1))).normalized()
            prof = [(0, 0), (0.15, 0.55), (0.45, 0.95), (0.75, 1.0), (0.95, 0.6), (1.0, 0.0)]
            ring_a, ring_b = [], []
            for (u, wv) in prof:
                cpos = p + tipv * (u * ln) + Vector((0, 0, -0.06 * u * u))
                ring_a.append(bm.verts.new(cpos + side * wd * wv * 0.5))
                ring_b.append(bm.verts.new(cpos - side * wd * wv * 0.5 + Vector((0, 0, 0.012 * wv))))
            for i in range(len(prof) - 1):
                bm.faces.new((ring_a[i], ring_a[i + 1], ring_b[i + 1], ring_b[i]))
    me = bpy.data.meshes.new(f'{name}_leaves')
    bm.to_mesh(me)
    bm.free()
    lv = bpy.data.objects.new(f'{name}_leaves', me)
    c.objects.link(lv)
    me.materials.append(M('leaf'))
    me.shade_smooth()
    par(lv, g)
    for i, (a, b) in enumerate(stems):
        d = b - a
        st = cyl(f'{name}_stem{i}', 0.012, d.length, (a + b) / 2, M('bark'), c, 8, bev=0)
        st.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
        par(st, g)
    return g

def books_row(name, c, x0, x1, y_back, z, depth_max, mat, axis='X', seed=0, face=-1):
    """Fill a shelf with books as one mesh; per-book colour attribute 'bookcol'."""
    rr = random.Random(seed)
    bm = bmesh.new()
    col_layer = bm.loops.layers.color.new('bookcol')
    pal = [srgb(h) for h in ('#e8e2d6', '#24364a', '#7a2f25', '#c9b48e', '#2f3a2f', '#d8cfc0', '#9a8a70', '#1e1e1e', '#b9583a', '#e0d8c8', '#56607a', '#8c7b5e')]
    page = srgb('#efe8d8')
    x = x0 + rr.uniform(0.0, 0.08)
    while x < x1 - 0.03:
        if rr.random() < 0.12:
            x += rr.uniform(0.08, 0.25)
            continue
        cluster = rr.randint(4, 14)
        for _ in range(cluster):
            t = rr.uniform(0.018, 0.05)
            if x + t > x1:
                break
            h = rr.uniform(0.2, 0.31)
            d = rr.uniform(0.15, depth_max)
            col = pal[rr.randrange(len(pal))]
            col = (col[0] * rr.uniform(0.85, 1.1), col[1] * rr.uniform(0.85, 1.1), col[2] * rr.uniform(0.85, 1.1), 1)
            if axis == 'X':
                yb, yf = y_back, y_back + face * d
                vs = [(x, yb, z), (x + t, yb, z), (x + t, yf, z), (x, yf, z), (x, yb, z + h), (x + t, yb, z + h), (x + t, yf, z + h), (x, yf, z + h)]
            else:
                xb, xf = y_back, y_back + face * d
                vs = [(xb, x, z), (xb, x + t, z), (xf, x + t, z), (xf, x, z), (xb, x, z + h), (xb, x + t, z + h), (xf, x + t, z + h), (xf, x, z + h)]
            bv = [bm.verts.new(v) for v in vs]
            for fi, f in enumerate(BOX_FACES):
                try:
                    face_ = bm.faces.new([bv[i] for i in f])
                except ValueError:
                    continue
                for lp in face_.loops:
                    lp[col_layer] = page if fi == 1 else col
            x += t + 0.001
        x += rr.uniform(0.02, 0.12)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    c.objects.link(ob)
    me.materials.append(mat)
    return ob

def m_books_attr():
    m, nt, out = new_mat('Books_Attr')
    at = N(nt, 'ShaderNodeAttribute', attribute_name='bookcol')
    p = principled(nt, None, 0.62)
    L(nt, at.outputs['Color'], p.inputs['Base Color'])
    finish(nt, out, p)
    return m

def m_flame():
    m, nt, out = new_mat('Fire_Flames')
    tc = N(nt, 'ShaderNodeTexCoord')
    gen = tc.outputs['Generated']
    sep = N(nt, 'ShaderNodeSeparateXYZ'); L(nt, gen, sep.inputs[0])
    n = noise(nt, scale_vec(nt, gen, (1.0, 14.0, 2.0)), 1.0, 6, 0.55)
    up = math_node(nt, 'SUBTRACT', 1.0, sep.outputs['Z'])
    tongue = math_node(nt, 'SUBTRACT', math_node(nt, 'MULTIPLY', n.outputs['Fac'], 1.6), math_node(nt, 'MULTIPLY', sep.outputs['Z'], 1.25))
    mask = math_node(nt, 'MULTIPLY', math_node(nt, 'POWER', up, 1.6), tongue, clamp=True)
    mask = math_node(nt, 'MULTIPLY', mask, 2.2, clamp=True)
    bb = N(nt, 'ShaderNodeBlackbody')
    L(nt, math_node(nt, 'ADD', 1300, math_node(nt, 'MULTIPLY', mask, 900)), bb.inputs['Temperature'])
    em = N(nt, 'ShaderNodeEmission')
    L(nt, bb.outputs[0], em.inputs['Color'])
    L(nt, math_node(nt, 'MULTIPLY', mask, 45.0), em.inputs['Strength'])
    tr = N(nt, 'ShaderNodeBsdfTransparent')
    mx = N(nt, 'ShaderNodeMixShader')
    L(nt, mask, mx.inputs[0]); L(nt, tr.outputs[0], mx.inputs[1]); L(nt, em.outputs[0], mx.inputs[2])
    finish(nt, out, mx)
    return m

def m_sheer():
    m, nt, out = new_mat('Curtain_Sheer')
    tl = N(nt, 'ShaderNodeBsdfTranslucent')
    tl.inputs['Color'].default_value = srgb('#f3ead9')
    tr = N(nt, 'ShaderNodeBsdfTransparent')
    df = N(nt, 'ShaderNodeBsdfDiffuse')
    df.inputs['Color'].default_value = srgb('#efe6d6')
    a = N(nt, 'ShaderNodeMixShader'); a.inputs[0].default_value = 0.5
    L(nt, df.outputs[0], a.inputs[1]); L(nt, tl.outputs[0], a.inputs[2])
    b = N(nt, 'ShaderNodeMixShader'); b.inputs[0].default_value = 0.55
    L(nt, tr.outputs[0], b.inputs[1]); L(nt, a.outputs[0], b.inputs[2])
    finish(nt, out, b)
    return m

def curtain(name, c, x0, x1, y, z0, z1, mat, folds=18, amp=0.05):
    nx, nz = 120, 2
    verts, faces = [], []
    for j in range(nz):
        z = z0 + (z1 - z0) * j / (nz - 1)
        for i in range(nx):
            u = i / (nx - 1)
            verts.append((x0 + (x1 - x0) * u, y + amp * math.sin(u * folds * 2 * math.pi), z))
    for i in range(nx - 1):
        faces.append((i, i + 1, nx + i + 1, nx + i))
    return mesh_obj(name, verts, faces, c, mat, True)

def m_screen_placeholder():
    m, nt, out = new_mat('Laptop_Screen')
    tc = N(nt, 'ShaderNodeTexCoord')
    sep = N(nt, 'ShaderNodeSeparateXYZ'); L(nt, tc.outputs['Generated'], sep.inputs[0])
    col = ramp(nt, sep.outputs['Y'], [(0.0, srgb('#0c1a2a')), (0.55, srgb('#27507a')), (1.0, srgb('#d9a46a'))]).outputs['Color']
    e = N(nt, 'ShaderNodeEmission'); L(nt, col, e.inputs['Color']); e.inputs['Strength'].default_value = 2.5
    finish(nt, out, e)
    return m

def m_leaf_olive():
    m, nt, out = new_mat('Leaf_Olive')
    gi = N(nt, 'ShaderNodeNewGeometry')
    p = principled(nt, None, 0.5)
    tl = N(nt, 'ShaderNodeBsdfTranslucent')
    tl.inputs['Color'].default_value = srgb('#7d8a4a')
    L(nt, mix_rgb(nt, gi.outputs['Backfacing'], srgb('#5a6b43'), srgb('#8f9a78')), p.inputs['Base Color'])
    mx = N(nt, 'ShaderNodeMixShader'); mx.inputs[0].default_value = 0.18
    L(nt, p.outputs[0], mx.inputs[1]); L(nt, tl.outputs[0], mx.inputs[2])
    finish(nt, out, mx)
    return m

# ---------------------------------------------------------------- rooms
def great_room(c, lc):
    x0 = -14.64
    fb = (5.3, 8.7, 0.62, 1.12)
    arch.wall('GR_breast', 'Y', x0, 0.6, 4.4, 9.6, 0.0, 6.75, M('limestone_wall'), c, openings=[fb])
    box('GR_firebox_back', x0, x0 + 0.1, fb[0], fb[1], fb[2], fb[3], M('black_plastic'), c, 0)
    box('GR_firebox_floor', x0, x0 + 0.6, fb[0], fb[1], fb[2] - 0.02, fb[2] + 0.02, M('metal_black'), c, 0)
    vplane('GR_flames', (x0 + 0.32, fb[0] + 0.05), (x0 + 0.32, fb[1] - 0.05), fb[2] + 0.02, fb[3] - 0.02, M('flames'), c)
    box('GR_embers', x0 + 0.2, x0 + 0.45, fb[0] + 0.1, fb[1] - 0.1, fb[2] + 0.02, fb[2] + 0.05, M('fire'), c, 0.004)
    point('GR_fire_light', (x0 + 0.42, (fb[0] + fb[1]) / 2, fb[2] + 0.2), 120, 1900, lc, 0.2)
    box('GR_hearth', x0, x0 + 0.78, 1.0, 13.0, 0.0, 0.4, M('limestone_wall'), c, 0.01)
    box('GR_rug', -12.9, -5.9, 3.0, 10.2, 0.0, 0.018, M('rug'), c, 0.004)
    sofa('GR_sofa', 4.3, 1.08, c, M('fabric_cream'), (-9.4, 9.15, 0), 0.0)
    sofa('GR_sofa2', 2.6, 1.0, c, M('fabric_cream'), (-6.55, 6.4, 0), -math.pi / 2)
    lounge_chair('GR_chair1', c, (-10.9, 4.1, 0), math.pi + 0.25)
    lounge_chair('GR_chair2', c, (-8.6, 4.0, 0), math.pi - 0.2)
    box('GR_coffee', -10.6, -8.6, 6.0, 7.1, 0.02, 0.36, M('travertine'), c, 0.02, 3)
    cyl('GR_drum', 0.42, 0.42, (-7.75, 7.85, 0.21), M('walnut'), c, 48, bev=0.01)
    lathe('GR_bowl', [(0.0, 0.0), (0.1, 0.0), (0.18, 0.05), (0.2, 0.09), (0.19, 0.095), (0.0, 0.03)], c, M('ceramic'), 48, (-9.9, 6.5, 0.36))
    for k, (dx, dy) in enumerate(((0.2, 0.15), (0.55, 0.25), (0.35, -0.1))):
        cbox(f'GR_book{k}', (0.28, 0.21, 0.03), (-9.0 + dx * 0.4, 6.55 + dy * 0.2, 0.375 + k * 0.03), M('books'), c, rot=(0, 0, R.uniform(-0.3, 0.3)), bev=0.003)
    lathe('GR_vase', [(0.0, 0.0), (0.05, 0.0), (0.09, 0.08), (0.08, 0.22), (0.035, 0.32), (0.04, 0.36), (0.0, 0.36)], c, M('ceramic'), 40, (-7.65, 7.8, 0.42))
    floor_lamp_arc('GR_arc', c, (-12.3, 9.6, 0), math.radians(-30), lc)
    box('GR_credenza', -11.2, -7.0, 13.12, 13.62, 0.12, 0.72, M('walnut'), c, 0.01)
    box('GR_cred_plinth', -11.1, -7.1, 13.18, 13.56, 0.0, 0.12, M('metal_black'), c, 0.004)
    for k in range(1, 4):
        x = -11.2 + 4.2 * k / 4
        box(f'GR_cred_seam{k}', x - 0.003, x + 0.003, 13.115, 13.12, 0.14, 0.7, M('black_plastic'), c, 0)
    cbox('GR_art', (2.6, 0.05, 1.7), (-9.1, 13.6, 2.45), M('art1'), c, bev=0.006)
    lathe('GR_cred_vase', [(0.0, 0.0), (0.07, 0.0), (0.12, 0.1), (0.1, 0.32), (0.05, 0.42), (0.06, 0.46), (0.0, 0.46)], c, M('ceramic'), 40, (-10.4, 13.37, 0.72))
    lathe('GR_cred_vase2', [(0.0, 0.0), (0.1, 0.0), (0.13, 0.06), (0.12, 0.14), (0.0, 0.16)], c, M('ceramic'), 40, (-7.8, 13.37, 0.72))
    olive_tree('GR_olive', c, (-13.7, 1.3, 0), 2.9, seed=4)
    fig_tree('GR_fig', c, (-4.0, 12.8, 0), 2.3, seed=9)
    for k, y in enumerate((2.6, 6.2, 9.8, 13.0)):
        box(f'GR_led{k}', -14.3, -3.7, y - 0.03, y + 0.03, arch.EAVE - 0.2, arch.EAVE - 0.18, M('warm_light'), c, 0)
        area(f'GR_up{k}', (-9.0, y, arch.EAVE - 0.15), 10.8, 260, 2800, lc, rot=(math.pi, 0, 0), size_y=0.3, spread=120, glossy=False)
    for k, (x, y) in enumerate(((-10.9, 4.3), (-8.4, 4.3), (-9.6, 6.6), (-9.4, 9.3), (-12.0, 9.3), (-7.0, 9.3), (-13.7, 7.0), (-6.6, 6.0))):
        spot(f'GR_down{k}', (x, y, arch.EAVE - 0.56), 130, 48, 0.7, 3000, lc, aim=(x + 0.001, y, 0))
    spot('GR_art_wash', (-9.1, 12.0, arch.EAVE - 0.56), 220, 38, 0.6, 3000, lc, aim=(-9.1, 13.6, 2.4))
    spot('GR_breast_wash', (-12.6, 7.0, arch.EAVE - 0.56), 260, 55, 0.7, 3000, lc, aim=(-14.0, 7.0, 3.0))
    area('GR_fill', (-9.0, 7.0, 4.6), 7.0, 220, 3200, lc, size_y=9.0, glossy=False)

def arrival(c, lc):
    g = grp('AR_chandelier', (0.0, 7.6, 4.9), 0, c)
    for k, (R_, tilt, dz) in enumerate(((0.75, 0.0, 0.0), (0.55, 0.16, 0.38), (0.38, -0.2, 0.7))):
        par(torus(f'AR_ring{k}', R_, 0.022, (0, 0, dz), M('brass'), c, rot=(tilt, 0, 0), maj=96, minr=10), g)
        par(torus(f'AR_ringled{k}', R_, 0.01, (0, 0, dz - 0.022), M('warm_light'), c, rot=(tilt, 0, 0), maj=96, minr=8), g)
        par(cyl(f'AR_cable{k}', 0.003, 2.1 - dz, (R_ * 0.7, 0, dz + (2.1 - dz) / 2), M('metal_black'), c, 6, bev=0), g)
    par(point('AR_ch_light', (0, 0, 0.3), 160, 2800, lc, 0.6), g)
    par(cyl('AR_canopy', 0.12, 0.03, (0, 0, 2.08), M('brass'), c, 32, bev=0.004), g)
    box('AR_console', -1.5, 1.5, 13.18, 13.64, 0.78, 0.86, M('marble'), c, 0.006)
    box('AR_console_leg', -0.12, 0.12, 13.3, 13.6, 0.0, 0.78, M('metal_dark'), c, 0.004)
    cyl('AR_art_round', 0.68, 0.04, (0.0, 13.62, 2.05), M('art3'), c, 72, rot=(math.pi / 2, 0, 0), bev=0.006)
    lathe('AR_urn', [(0.0, 0.0), (0.09, 0.0), (0.17, 0.12), (0.16, 0.34), (0.08, 0.46), (0.09, 0.5), (0.0, 0.5)], c, M('ceramic'), 48, (-0.9, 13.42, 0.86))
    sphere('AR_sphere', 0.11, (0.85, 13.42, 0.97), M('brass'), c, 4)
    olive_tree('AR_olive', c, (1.95, 3.35, 0), 2.6, seed=11)
    box('AR_bench', -3.0, -2.55, 10.6, 12.9, 0.0, 0.44, M('walnut'), c, 0.01)
    cbox('AR_art_side', (0.04, 1.5, 1.9), (-2.98, 11.75, 1.75), M('art2'), c, bev=0.004)
    n, run = 16, 0.29
    rise = arch.UPPER / 17
    ys = 10.15 - n * run
    for i in range(n):
        z = rise * (i + 1)
        box(f'AR_treadled{i}', 2.62, 2.66, ys + i * run + 0.02, ys + (i + 1) * run - 0.04, z - 0.095, z - 0.085, M('warm_light'), c, 0)
    for k, (x, y) in enumerate(((-1.2, 4.0), (1.2, 4.6), (-1.2, 9.0), (0.0, 12.0))):
        spot(f'AR_down{k}', (x, y, 6.78), 240, 50, 0.7, 3000, lc, aim=(x + 0.001, y, 0))
    for k, x in enumerate((-1.6, 0.0, 1.6)):
        spot(f'AR_wash{k}', (x, 12.85, arch.UPPER - 0.36), 150, 70, 0.8, 2900, lc, aim=(x, 13.62, 1.0))
    area('AR_fill', (0, 7.0, 6.6), 4.0, 420, 3200, lc, size_y=9.0, glossy=False)
    area('AR_bounce', (0, 7.0, 1.0), 4.0, 160, 3200, lc, rot=(math.pi, 0, 0), size_y=8.0, glossy=False)
    area('AR_landing', (0, 12.0, 6.6), 3.0, 60, 2900, lc, size_y=3.0, glossy=False)

def kitchen(c, lc):
    yb = 12.64
    for k, (a, b) in enumerate(((3.05, 6.9), (10.1, 14.0))):
        box(f'KT_tall{k}', a, b, yb - 0.66, yb, 0.0, 3.28, M('walnut_panel'), c, 0.004)
        n = max(1, round((b - a) / 0.62))
        for i in range(1, n):
            x = a + (b - a) * i / n
            box(f'KT_tallseam{k}_{i}', x - 0.002, x + 0.002, yb - 0.665, yb - 0.66, 0.08, 3.2, M('black_plastic'), c, 0)
    box('KT_base', 6.9, 10.1, yb - 0.66, yb, 0.1, 0.88, M('lacquer_dark'), c, 0.004)
    box('KT_kick', 6.95, 10.05, yb - 0.6, yb, 0.0, 0.1, M('black_plastic'), c, 0)
    box('KT_counter', 6.88, 10.12, yb - 0.68, yb, 0.88, 0.92, M('marble'), c, 0.004)
    box('KT_splash', 6.9, 10.1, yb - 0.03, yb, 0.92, 2.22, M('marble'), c, 0.002)
    box('KT_cooktop', 7.9, 8.8, yb - 0.58, yb - 0.08, 0.92, 0.926, M('black_glass'), c, 0.002)
    box('KT_shelf', 7.1, 9.9, yb - 0.3, yb - 0.02, 1.7, 1.74, M('walnut'), c, 0.003)
    box('KT_shelf_led', 7.1, 9.9, yb - 0.25, yb - 0.22, 1.695, 1.7, M('warm_light'), c, 0)
    for k, x in enumerate((7.5, 8.2, 9.4)):
        lathe(f'KT_jar{k}', [(0.0, 0.0), (0.06, 0.0), (0.065, 0.02), (0.065, 0.2 + 0.05 * k), (0.0, 0.2 + 0.05 * k)], c, M('ceramic'), 32, (x, yb - 0.16, 1.74))
    ix0, ix1, iy0, iy1 = 6.0, 11.0, 7.0, 8.25
    box('KT_island', ix0 + 0.06, ix1 - 0.06, iy0 + 0.25, iy1 - 0.05, 0.08, 0.88, M('walnut_panel'), c, 0.004)
    box('KT_island_kick', ix0 + 0.1, ix1 - 0.1, iy0 + 0.3, iy1 - 0.1, 0.0, 0.08, M('black_plastic'), c, 0)
    box('KT_island_top', ix0, ix1, iy0, iy1, 0.88, 0.94, M('marble'), c, 0.004)
    box('KT_island_wfL', ix0, ix0 + 0.06, iy0, iy1, 0.0, 0.88, M('marble'), c, 0.004)
    box('KT_island_wfR', ix1 - 0.06, ix1, iy0, iy1, 0.0, 0.88, M('marble'), c, 0.004)
    box('KT_sink', 9.2, 9.95, 7.75, 8.15, 0.935, 0.942, M('steel'), c, 0.002)
    tap = bpy.data.curves.new('KT_tap', 'CURVE'); tap.dimensions = '3D'
    sp = tap.splines.new('BEZIER'); sp.bezier_points.add(1)
    pa, pb = sp.bezier_points
    pa.co = (9.57, 8.2, 0.94); pa.handle_left = (9.57, 8.2, 0.8); pa.handle_right = (9.57, 8.2, 1.35)
    pb.co = (9.57, 7.95, 1.18); pb.handle_left = (9.57, 8.1, 1.4); pb.handle_right = (9.57, 7.9, 1.1)
    tap.bevel_depth = 0.012; tap.bevel_resolution = 4
    tob = bpy.data.objects.new('KT_tap', tap); c.objects.link(tob); tap.materials.append(M('brass'))
    lathe('KT_bowl', [(0.0, 0.0), (0.12, 0.0), (0.2, 0.06), (0.22, 0.1), (0.0, 0.04)], c, M('ceramic'), 48, (7.3, 7.6, 0.94))
    for k in range(5):
        sphere(f'KT_lemon{k}', 0.035, (7.3 + R.uniform(-0.08, 0.08), 7.6 + R.uniform(-0.08, 0.08), 1.0 + R.uniform(0, 0.03)), M('lemon'), c, 3, (1, 1, 0.85))
    box('KT_board', 8.0, 8.55, 7.35, 7.7, 0.94, 0.965, M('oak'), c, 0.006)
    for k, x in enumerate((6.75, 7.95, 9.15, 10.35)):
        stool(f'KT_stool{k}', c, (x, 6.55, 0))
    for k, x in enumerate((6.9, 8.5, 10.1)):
        sphere(f'KT_globe{k}', 0.17, (x, 7.62, 2.15), M('glass_frost'), c, 4)
        sphere(f'KT_bulb{k}', 0.05, (x, 7.62, 2.15), M('warm_light'), c, 2)
        cyl(f'KT_cord{k}', 0.004, 1.0, (x, 7.62, 2.8), M('metal_black'), c, 6, bev=0)
        cyl(f'KT_cap{k}', 0.05, 0.05, (x, 7.62, 2.33), M('brass'), c, 24, bev=0.004)
        point(f'KT_globe_light{k}', (x, 7.62, 2.15), 45, 2700, lc, 0.12)
    box('DN_table', 5.9, 11.1, 2.45, 3.6, 0.72, 0.78, M('walnut'), c, 0.008)
    for k, x in enumerate((6.6, 10.4)):
        box(f'DN_leg{k}', x - 0.06, x + 0.06, 2.65, 3.4, 0.0, 0.72, M('travertine'), c, 0.01)
    for k, x in enumerate((6.6, 7.95, 9.3, 10.6)):
        dining_chair(f'DN_chairS{k}', c, (x, 1.95, 0), math.pi, M('fabric_cream'))
        dining_chair(f'DN_chairN{k}', c, (x, 4.1, 0), 0, M('fabric_cream'))
    box('DN_pendant', 6.4, 10.6, 2.97, 3.07, 2.0, 2.05, M('brass'), c, 0.004)
    box('DN_pendant_led', 6.45, 10.55, 2.98, 3.06, 1.995, 2.0, M('warm_light'), c, 0)
    for k, x in enumerate((6.6, 10.4)):
        cyl(f'DN_wire{k}', 0.002, 1.25, (x, 3.02, 2.67), M('metal_black'), c, 6, bev=0)
    area('DN_pendant_light', (8.5, 3.02, 1.98), 4.0, 120, 2700, lc, size_y=0.08, spread=140)
    lathe('DN_vase', [(0.0, 0.0), (0.06, 0.0), (0.1, 0.12), (0.06, 0.3), (0.03, 0.36), (0.0, 0.36)], c, M('ceramic'), 40, (8.5, 3.02, 0.78))
    cbox('KT_art', (0.04, 1.9, 1.3), (3.02, 8.6, 1.75), M('art2'), c, bev=0.004)
    fig_tree('KT_fig', c, (13.4, 0.75, 0), 2.4, seed=21)
    for k, (x, y) in enumerate(((5.0, 4.8), (12.2, 4.8), (5.0, 10.5), (12.2, 10.5), (8.5, 11.6), (6.2, 11.6), (10.8, 11.6), (4.2, 1.4), (12.8, 1.4))):
        spot(f'KT_down{k}', (x, y, 3.28), 90, 50, 0.7, 3000, lc, aim=(x + 0.001, y, 0))
        cyl(f'KT_downtrim{k}', 0.045, 0.006, (x, y, 3.297), M('warm_light'), c, 24, bev=0)
    area('KT_fill', (8.5, 6.5, 3.2), 9.0, 300, 3200, lc, size_y=10.0, glossy=False)
    area('KT_bounce', (8.5, 6.0, 1.2), 9.0, 260, 3200, lc, rot=(math.pi, 0, 0), size_y=10.0, glossy=False)
    area('KT_wall_wash', (8.5, 11.4, 3.2), 3.0, 90, 2900, lc, size_y=0.3, glossy=False)

def study(c, lc):
    xr = 18.64
    sh_y0, sh_y1 = 0.9, 12.2
    depth = 0.38
    box('ST_lib_back', xr - 0.02, xr, sh_y0, sh_y1, 0.0, 3.28, M('walnut_panel'), c, 0)
    nb = 8
    for i in range(nb + 1):
        y = sh_y0 + (sh_y1 - sh_y0) * i / nb
        box(f'ST_lib_v{i}', xr - depth, xr - 0.02, y - 0.02, y + 0.02, 0.0, 3.28, M('walnut'), c, 0.004)
    shelves_z = [0.0, 0.42, 0.82, 1.22, 1.62, 2.02, 2.42, 2.84]
    for j, z in enumerate(shelves_z):
        box(f'ST_lib_s{j}', xr - depth, xr - 0.02, sh_y0, sh_y1, z, z + 0.035, M('walnut'), c, 0.003)
        if j > 0:
            box(f'ST_lib_led{j}', xr - depth + 0.03, xr - depth + 0.05, sh_y0, sh_y1, z - 0.004, z, M('warm_soft'), c, 0)
    bmat = M('books_attr')
    for i in range(nb):
        ya = sh_y0 + (sh_y1 - sh_y0) * i / nb + 0.03
        yb_ = sh_y0 + (sh_y1 - sh_y0) * (i + 1) / nb - 0.03
        for j, z in enumerate(shelves_z[:-1]):
            if R.random() < 0.14:
                lathe(f'ST_obj{i}_{j}', [(0.0, 0.0), (0.06, 0.0), (0.09, 0.07), (0.07, 0.2), (0.0, 0.2)], c, M('ceramic'), 32, (xr - 0.2, (ya + yb_) / 2, z + 0.035))
                continue
            books_row(f'ST_books{i}_{j}', c, ya, yb_, xr - 0.03, z + 0.035, 0.3, bmat, axis='Y', seed=i * 31 + j, face=-1)
    box('ST_desk_top', 15.25, 17.85, 10.35, 11.3, 0.73, 0.77, M('walnut'), c, 0.006)
    for k, (x, y) in enumerate(((15.35, 10.45), (17.75, 10.45), (15.35, 11.2), (17.75, 11.2))):
        box(f'ST_desk_leg{k}', x - 0.025, x + 0.025, y - 0.025, y + 0.025, 0.0, 0.73, M('metal_black'), c, 0.003)
    box('ST_desk_drawer', 15.4, 17.7, 10.5, 11.2, 0.62, 0.73, M('walnut'), c, 0.004)
    lp = grp('ST_laptop', (16.45, 10.78, 0.77), 0, c)
    par(box('ST_lap_base', -0.165, 0.165, -0.115, 0.115, 0.0, 0.014, M('steel'), c, 0.004), lp)
    par(box('ST_lap_keys', -0.14, 0.14, -0.035, 0.09, 0.014, 0.0145, M('black_plastic'), c, 0), lp)
    scr = grp('ST_lap_hinge', (0, 0.115, 0.012), 0, c)
    scr.parent = lp
    scr.rotation_euler = (math.radians(-12), 0, 0)
    par(box('ST_lap_lid', -0.165, 0.165, 0.0, 0.008, 0.0, 0.215, M('steel'), c, 0.003), scr)
    s = mesh_obj('ST_lap_screen', [(-0.155, -0.0012, 0.01), (0.155, -0.0012, 0.01), (0.155, -0.0012, 0.205), (-0.155, -0.0012, 0.205)], [(0, 1, 2, 3)], c, M('screen'))
    s.data.uv_layers.new(name='UVMap')
    uv = s.data.uv_layers[0].data
    for i, (u, v) in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uv[i].uv = (u, v)
    par(s, scr)
    table_lamp('ST_lamp', c, (17.5, 11.0, 0.77), lc, 22)
    for k in range(3):
        cbox(f'ST_deskbook{k}', (0.24, 0.17, 0.028), (15.75, 10.95, 0.785 + k * 0.029), M('books'), c, rot=(0, 0, R.uniform(-0.2, 0.2)), bev=0.003)
    lathe('ST_cup', [(0.0, 0.0), (0.035, 0.0), (0.042, 0.085), (0.039, 0.085), (0.032, 0.006), (0.0, 0.006)], c, M('ceramic'), 32, (16.95, 10.6, 0.77))
    ch = grp('ST_chair', (16.45, 9.75, 0), 0.0, c)
    par(cyl('ST_ch_base', 0.32, 0.03, (0, 0, 0.03), M('metal_black'), c, 5, bev=0.005), ch)
    par(cyl('ST_ch_col', 0.03, 0.4, (0, 0, 0.24), M('steel'), c, 16, bev=0), ch)
    par(box('ST_ch_seat', -0.27, 0.27, -0.26, 0.24, 0.44, 0.54, M('leather'), c, 0.04, 4), ch)
    bk = box('ST_ch_back', -0.26, 0.26, -0.05, 0.05, 0.0, 0.52, M('leather'), c, 0.04, 4)
    bk.location = (0, -0.25, 0.58); bk.rotation_euler = (math.radians(10), 0, 0)
    par(bk, ch)
    box('ST_rug', 14.9, 18.0, 8.2, 12.3, 0.0, 0.016, M('rug_dark'), c, 0.004)
    lounge_chair('ST_reader', c, (15.3, 2.2, 0), math.radians(200), M('fabric_olive'))
    cyl('ST_side', 0.22, 0.5, (16.1, 1.6, 0.25), M('marble_dark'), c, 40, bev=0.006)
    olive_tree('ST_olive', c, (14.75, 11.9, 0), 2.2, seed=31)
    for k, (x, y) in enumerate(((16.4, 10.8), (16.4, 6.0), (16.4, 2.0))):
        spot(f'ST_down{k}', (x, y, 3.28), 70, 45, 0.7, 3000, lc, aim=(x + 0.001, y, 0))
    area('ST_lib_wash', (17.4, 6.5, 3.2), 0.5, 150, 2800, lc, size_y=11.0, rot=(0, math.radians(30), 0), glossy=False)
    area('ST_fill', (16.4, 6.5, 3.2), 3.5, 140, 3200, lc, size_y=11.0, glossy=False)
    area('ST_bounce', (16.4, 6.5, 1.0), 3.5, 110, 3200, lc, rot=(math.pi, 0, 0), size_y=11.0, glossy=False)

def upper_rooms(c, lc):
    for k, (xa, xb) in enumerate(((2.9, 8.0), (8.4, 13.4), (13.8, 20.2))):
        cx = (xa + xb) / 2
        box(f'UP_bed{k}', cx - 1.0, cx + 1.0, 3.9, 6.0, arch.UF0, arch.UF0 + 0.5, M('fabric_cream'), c, 0.05, 3)
        box(f'UP_head{k}', cx - 1.4, cx + 1.4, 5.88, 6.0, arch.UF0, arch.UF0 + 1.4, M('walnut_panel'), c, 0.01)
        area(f'UP_light{k}', (cx, 2.0, arch.UF1 - 0.05), 3.0, 120, 2700, lc, size_y=3.0, glossy=False)
        for sx in (-1, 1):
            point(f'UP_lamp{k}{sx}', (cx + sx * 1.35, 5.6, arch.UF0 + 0.75), 14, 2600, lc, 0.08)
        curtain(f'UP_sheer{k}', c, xa + 0.1, xb - 0.1, -1.8, arch.UF0 + 0.05, arch.UF1 - 0.05, M('sheer'), folds=int((xb - xa) * 3), amp=0.04)

def build():
    MATS['limestone_wall'] = m_stone_slab('Limestone_Wall', '#d6cdbf', '#c3b8a6', 0.5, (1.2, 0.6), 0.0015, axis='WALL')
    MATS['travertine'] = m_stone_slab('Travertine', '#d8c7ad', '#c6b293', 0.45, (2.0, 2.0), 0.0)
    MATS['books_attr'] = m_books_attr()
    MATS['flames'] = m_flame()
    MATS['sheer'] = m_sheer()
    import os
    shot = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'laptop_screen.png')
    MATS['screen'] = m_image_emit('Laptop_Screen', shot, 2.0) if os.path.exists(shot) else m_screen_placeholder()
    MATS['leaf_olive'] = m_leaf_olive()
    MATS['black_glass'] = m_simple('Black_Glass', srgb('#050505'), 0.05, **{'Coat Weight': 1.0})
    MATS['lemon'] = m_simple('Lemon', srgb('#e8c13a'), 0.45)
    c = coll('Interior')
    lc = coll('Interior_Lights')
    great_room(coll('Great_Room', c), lc)
    arrival(coll('Arrival', c), lc)
    kitchen(coll('Kitchen', c), lc)
    study(coll('Study', c), lc)
    upper_rooms(coll('Upper', c), lc)
