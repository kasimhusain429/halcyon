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

def tub_chair(name, c, loc, rz, fabric, base=None):
    """Upholstered tub chair on a bronze disc: a round seat inside a back that wraps 240 degrees.
    Faces -Y before rotation, like lounge_chair."""
    g = grp(name, loc, rz, c)
    base = base or M('metal_dark')
    par(cyl(f'{name}_base', 0.22, 0.03, (0, 0, 0.015), base, c, 40, bev=0.004), g)
    par(cyl(f'{name}_stem', 0.03, 0.16, (0, 0, 0.11), base, c, 16, bev=0), g)
    par(cyl(f'{name}_seat', 0.36, 0.2, (0, 0, 0.29), fabric, c, 48, bev=0.03), g)
    n, verts, faces = 24, [], []
    for i in range(n + 1):
        a = math.radians(-30 + 240 * i / n)  # from the right side, round the back (+Y), to the left
        for (r, z) in ((0.27, 0.3), (0.4, 0.3), (0.4, 0.72), (0.27, 0.72)):
            verts.append((r * math.cos(a), r * math.sin(a), z))
    for i in range(n):
        for k in range(4):
            a0, a1 = i * 4 + k, i * 4 + (k + 1) % 4
            faces.append((a0, a1, a1 + 4, a0 + 4))
    faces += [(0, 3, 2, 1), (n * 4, n * 4 + 1, n * 4 + 2, n * 4 + 3)]
    back = mesh_obj(f'{name}_back', verts, faces, c, fabric, True)
    bm = bmesh.new()
    bm.from_mesh(back.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(back.data)
    bm.free()
    bevel(back, 0.03, 3)
    par(back, g)
    return g

def globe_pendant(name, c, loc, ceiling, lc, r=0.085, power=10):
    """Opal glass globe with a bronze cap, hung on a cable from the ceiling (loc: globe centre)."""
    x, y, z = loc
    s = sphere(f'{name}_globe', r, loc, M('warm_soft'), c, 3)
    s.visible_shadow = False  # the bulb inside lights the room through it
    cyl(f'{name}_cap', 0.03, 0.05, (x, y, z + r + 0.012), M('metal_dark'), c, 24, bev=0.003)
    drop = ceiling - (z + r + 0.037)
    cyl(f'{name}_cable', 0.004, drop, (x, y, z + r + 0.037 + drop / 2), M('metal_dark'), c, 8, bev=0)
    point(f'{name}_light', loc, power, 2700, lc, r * 0.7)

def paper_lantern(name, c, loc, ceiling, lc, r, power=22):
    """Round paper lantern on a cord: glowing paper, a brass ring at the top."""
    x, y, z = loc
    s = sphere(f'{name}_paper', r, loc, M('emit_paper'), c, 3)
    s.visible_shadow = False
    cyl(f'{name}_ring', r * 0.34, 0.02, (x, y, z + r * 0.94), M('brass'), c, 24, bev=0)
    drop = ceiling - (z + r)
    cyl(f'{name}_cord', 0.003, drop, (x, y, z + r + drop / 2), M('black_plastic'), c, 6, bev=0)
    point(f'{name}_light', loc, power, 2700, lc, r * 0.6)

def drum_floor_lamp(name, c, loc, lc, power=30):
    """Bronze stem, linen drum shade."""
    g = grp(name, loc, 0, c)
    par(cyl(f'{name}_base', 0.16, 0.025, (0, 0, 0.0125), M('metal_dark'), c, 40, bev=0.004), g)
    par(cyl(f'{name}_stem', 0.011, 1.2, (0, 0, 0.62), M('metal_dark'), c, 12, bev=0), g)
    sh = lathe(f'{name}_shade', [(0.23, 1.18), (0.23, 1.52)], c, M('shade_linen'), 48, cap=False)
    sh.modifiers.new('Solid', 'SOLIDIFY').thickness = 0.004
    par(sh, g)
    par(point(f'{name}_bulb', (0, 0, 1.36), power, 2700, lc, 0.06), g)
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

def upper_gallery(c, lc):
    """The bedroom gallery along the north wall of the wing, entered from the stair landing."""
    f0, f1 = arch.UF0 + 0.02, arch.UF1        # finished floor, ceiling
    gy0, gy1 = arch.GAL_Y + 0.2, 13.16         # gallery wall face, north lining face
    gx0, gx1 = 2.84, 20.26
    gm = (gy0 + gy1) / 2
    # walnut panelling on the gallery wall, full height, opening into the three rooms
    arch.wall('UPG_walnut', 'X', gy0, 0.03, gx0, gx1, f0, f1, M('walnut_panel'), c,
              openings=[(d0, d1, f0, f0 + dh) for d0, d1, dh in arch.GAL_DOORS], bev=0.002)
    # walnut linings in the doorways
    for n, (d0, d1, dh) in enumerate(arch.GAL_DOORS):
        for k, x in enumerate((d0, d1 - 0.02)):
            box(f'UPG_jamb{n}{k}', x, x + 0.02, arch.GAL_Y - 0.01, gy0 + 0.03, f0, f0 + dh, M('walnut'), c, 0.002)
        box(f'UPG_head{n}', d0, d1, arch.GAL_Y - 0.01, gy0 + 0.03, f0 + dh - 0.02, f0 + dh, M('walnut'), c, 0.002)
    # art between the north windows, a bench under the middle one, an olive tree at the east end
    for k, (x, mat) in enumerate(((8.9, 'art1'), (14.5, 'art3'))):
        cbox(f'UPG_art{k}', (1.5, 0.04, 1.05), (x, gy1 - 0.03, f0 + 1.62), M(mat), c, bev=0.004)
    box('UPG_bench', 10.95, 12.45, 12.72, 13.12, f0 + 0.06, f0 + 0.42, M('walnut'), c, 0.008)
    box('UPG_bench_plinth', 11.05, 12.35, 12.78, 13.06, f0, f0 + 0.06, M('metal_black'), c, 0.003)
    box('UPG_cushion', 10.98, 12.42, 12.74, 13.1, f0 + 0.42, f0 + 0.5, M('fabric_sand'), c, 0.03, 3)
    lathe('UPG_vase', [(0.0, 0.0), (0.07, 0.0), (0.12, 0.1), (0.1, 0.32), (0.05, 0.42), (0.06, 0.46), (0.0, 0.46)], c, M('ceramic'), 40, (12.2, 12.92, f0 + 0.5))
    olive_tree('UPG_olive', c, (19.5, 12.3, f0), 2.2, seed=41)
    # light: a slot along the ceiling, washers on the walnut, pictures lit, a soft fill
    box('UPG_slot', 3.6, 19.6, gm - 0.025, gm + 0.025, f1 - 0.012, f1 - 0.002, M('warm_light'), c, 0)
    area('UPG_fill', (11.6, gm, f1 - 0.06), 16.0, 230, 2900, lc, size_y=0.5, glossy=False)
    area('UPG_bounce', (11.6, gm, f0 + 0.7), 16.0, 60, 3000, lc, rot=(math.pi, 0, 0), size_y=2.0, glossy=False)
    for k, x in enumerate((4.3, 9.6, 13.35, 17.6, 19.6)):
        spot(f'UPG_wash{k}', (x, gy0 + 0.45, f1 - 0.04), 55, 75, 0.9, 2900, lc, aim=(x, gy0, f0 + 0.8))
    for k, x in enumerate((8.9, 14.5)):
        spot(f'UPG_artlight{k}', (x, gy1 - 1.0, f1 - 0.04), 70, 34, 0.6, 3000, lc, aim=(x, gy1, f0 + 1.6))
    spot('UPG_olive_light', (19.0, 11.6, f1 - 0.04), 60, 45, 0.7, 2900, lc, aim=(19.5, 12.3, f0 + 1.2))

def upper_suite_west(c, lc):
    """The west suite: walk-in dressing passage beside a walnut block, the bedroom facing the lake."""
    f0, f1 = arch.UF0 + 0.02, arch.UF1
    bx0, bx1, by0 = arch.SUITE_BLOCK
    px1 = arch.PARTITIONS[0] - 0.1              # east partition face (8.3)
    # wardrobe fronts on the block, facing the passage: shadow gaps and brass pulls
    ys = [by0 + 0.6 + 0.95 * i for i in range(6)]
    for i, y in enumerate(ys):
        box(f'UP1_wr_gap{i}', bx1, bx1 + 0.004, y - 0.003, y + 0.003, f0 + 0.08, f1 - 0.45, M('black_plastic'), c, 0)
        if i < len(ys) - 1:
            box(f'UP1_wr_pull{i}', bx1 + 0.004, bx1 + 0.03, y + 0.05, y + 0.07, f0 + 0.7, f0 + 1.6, M('brass'), c, 0.003)
    box('UP1_wr_top', bx1, bx1 + 0.004, by0 + 0.4, arch.GAL_Y, f1 - 0.453, f1 - 0.447, M('black_plastic'), c, 0)
    box('UP1_wr_led', bx1 + 0.004, bx1 + 0.012, by0 + 0.4, arch.GAL_Y - 0.1, f1 - 0.02, f1 - 0.01, M('warm_soft'), c, 0)
    for k, y in enumerate((6.1, 8.6)):
        spot(f'UP1_pass{k}', (7.4, y, f1 - 0.04), 45, 70, 0.8, 2900, lc, aim=(7.0, y, f0))
    # the bed against the walnut wall
    cx = 4.6
    box('UP1_headboard', cx - 1.25, cx + 1.25, by0 - 0.1, by0, f0 + 0.24, f0 + 1.38, M('fabric_sand'), c, 0.03, 3)
    box('UP1_bedbase', cx - 1.05, cx + 1.05, 2.3, by0 - 0.1, f0 + 0.06, f0 + 0.28, M('walnut'), c, 0.01)
    box('UP1_bedplinth', cx - 0.95, cx + 0.95, 2.4, by0 - 0.2, f0, f0 + 0.06, M('black_plastic'), c, 0)
    box('UP1_mattress', cx - 1.0, cx + 1.0, 2.36, by0 - 0.14, f0 + 0.28, f0 + 0.52, M('fabric_cream'), c, 0.06, 4)
    box('UP1_throw', cx - 1.03, cx + 1.03, 2.33, 3.05, f0 + 0.5, f0 + 0.56, M('fabric_olive'), c, 0.025, 3)
    for k, (dx, w, dz, m) in enumerate(((-0.48, 0.78, 0.0, 'fabric_cream'), (0.48, 0.78, 0.0, 'fabric_cream'),
                                        (-0.42, 0.6, -0.05, 'fabric_sand'), (0.42, 0.6, -0.05, 'fabric_sand'))):
        y = by0 - 0.3 - (0.16 if k >= 2 else 0.0)
        cbox(f'UP1_pillow{k}', (w, 0.17, 0.42 + dz), (cx + dx, y, f0 + 0.74 + dz / 2), M(m), c,
             rot=(math.radians(-12), 0, math.radians(R.uniform(-4, 4))), bev=0.07, seg=4)
    for k, sx in enumerate((-1, 1)):
        nx = cx + sx * 1.43
        box(f'UP1_night{k}', nx - 0.24, nx + 0.24, by0 - 0.5, by0 - 0.04, f0 + 0.12, f0 + 0.55, M('walnut'), c, 0.008)
        box(f'UP1_night{k}_leg', nx - 0.2, nx + 0.2, by0 - 0.46, by0 - 0.08, f0, f0 + 0.12, M('metal_black'), c, 0.003)
        table_lamp(f'UP1_lamp{k}', c, (nx, by0 - 0.28, f0 + 0.55), lc, 14)
    cbox('UP1_book', (0.22, 0.16, 0.03), (cx + 1.38, by0 - 0.3, f0 + 0.565), M('books'), c, rot=(0, 0, 0.3), bev=0.003)
    # bench at the foot, rug, reading chair by the window, credenza and a painting on the east wall
    box('UP1_bench_frame', cx - 0.72, cx + 0.72, 1.62, 2.02, f0, f0 + 0.36, M('walnut'), c, 0.008)
    box('UP1_bench_seat', cx - 0.7, cx + 0.7, 1.64, 2.0, f0 + 0.36, f0 + 0.45, M('leather'), c, 0.03, 3)
    box('UP1_rug', 3.0, 6.4, 0.9, by0 - 0.12, f0, f0 + 0.015, M('rug'), c, 0.004)
    lounge_chair('UP1_chair', c, (3.75, -0.55, f0), math.radians(30), M('fabric_olive'))
    cyl('UP1_side', 0.2, 0.48, (3.2, 0.25, f0 + 0.24), M('marble_dark'), c, 40, bev=0.006)
    lathe('UP1_cup', [(0.0, 0.0), (0.035, 0.0), (0.042, 0.085), (0.039, 0.085), (0.032, 0.006), (0.0, 0.006)], c, M('ceramic'), 32, (3.15, 0.2, f0 + 0.48))
    box('UP1_credenza', px1 - 0.46, px1, -0.9, 1.7, f0 + 0.1, f0 + 0.62, M('walnut'), c, 0.008)
    box('UP1_cred_plinth', px1 - 0.42, px1 - 0.04, -0.85, 1.65, f0, f0 + 0.1, M('metal_black'), c, 0.003)
    for k in range(1, 3):
        y = -0.9 + 2.6 * k / 3
        box(f'UP1_cred_seam{k}', px1 - 0.465, px1 - 0.46, y - 0.003, y + 0.003, f0 + 0.12, f0 + 0.6, M('black_plastic'), c, 0)
    lathe('UP1_vase', [(0.0, 0.0), (0.1, 0.0), (0.13, 0.06), (0.12, 0.14), (0.0, 0.16)], c, M('ceramic'), 40, (px1 - 0.23, -0.3, f0 + 0.62))
    lathe('UP1_vase2', [(0.0, 0.0), (0.05, 0.0), (0.09, 0.08), (0.08, 0.22), (0.035, 0.32), (0.04, 0.36), (0.0, 0.36)], c, M('ceramic'), 40, (px1 - 0.25, 1.15, f0 + 0.62))
    cbox('UP1_art', (0.04, 1.6, 1.1), (px1 - 0.03, 0.4, f0 + 1.65), M('art2'), c, bev=0.004)
    # sheers drawn back to either end of the window
    curtain('UP1_sheerW', c, 2.95, 4.05, -1.8, f0 + 0.03, f1 - 0.05, M('sheer'), folds=9, amp=0.06)
    curtain('UP1_sheerE', c, px1 - 0.75, px1 - 0.1, -1.8, f0 + 0.03, f1 - 0.05, M('sheer'), folds=6, amp=0.06)
    # light
    area('UP1_fill', (4.9, 1.3, f1 - 0.06), 3.6, 100, 2800, lc, size_y=4.6, glossy=False)
    area('UP1_bounce', (4.9, 1.3, f0 + 0.6), 3.6, 45, 3000, lc, rot=(math.pi, 0, 0), size_y=4.6, glossy=False)
    for k, x in enumerate((cx - 0.7, cx + 0.7)):
        spot(f'UP1_head_wash{k}', (x, by0 - 0.35, f1 - 0.04), 45, 60, 0.85, 2900, lc, aim=(x, by0, f0 + 0.6))
    spot('UP1_art_light', (px1 - 1.0, 0.4, f1 - 0.04), 55, 36, 0.6, 3000, lc, aim=(px1, 0.4, f0 + 1.6))
    spot('UP1_chair_light', (3.6, -0.3, f1 - 0.04), 35, 50, 0.8, 2800, lc, aim=(3.65, -0.45, f0))

def upper_bunk_room(c, lc):
    """The bunk room: long and narrow (4 x 12 m) under a lowered white-oak board ceiling. Built-in
    bunks for four along the west wall, a window seat over the lake, a desk wall on the shower room,
    paper lanterns over a round rug. Limed oak and lake-blue linen."""
    f0 = arch.UF0 + 0.02
    x0, x1 = arch.PARTITIONS[0] + 0.1, arch.PARTITIONS[1] - 0.1       # 8.5, 12.5
    y0 = -1.96                                                         # south lining face
    sx0, sx1, sy0, (dy0, dy1) = arch.BUNK_BATH
    cz = 6.46                                                          # lowered ceiling
    ow, lake, sand, cream = M('oak_white'), M('fabric_lake'), M('fabric_sand'), M('fabric_cream')
    # the lowered board ceiling, its boards running the length of the room
    box('UPB_ceiling', x0, x1, y0, arch.GAL_Y, cz, cz + 0.04, M('oak_boards'), c, 0)
    # shower room door (closed), lobby with coat pegs and a bench
    box('UPB_bathdoor', sx1 - 0.045, sx1 - 0.005, dy0 + 0.01, dy1 - 0.01, f0, f0 + 2.07, ow, c, 0.003)
    box('UPB_bathdoor_pull', sx1 - 0.005, sx1 + 0.02, dy1 - 0.13, dy1 - 0.11, f0 + 0.85, f0 + 1.3, M('brass'), c, 0.003)
    for k in range(5):
        cyl(f'UPB_peg{k}', 0.014, 0.09, (x1 - 0.045, 7.3 + 0.32 * k, f0 + 1.62), M('brass'), c, 12, rot=(0, math.pi / 2, 0), bev=0)
    box('UPB_bag', x1 - 0.12, x1 - 0.05, 7.47, 7.83, f0 + 1.05, f0 + 1.58, sand, c, 0.02, 2)
    box('UPB_lobby_bench', x1 - 0.36, x1, 7.15, 8.75, f0 + 0.06, f0 + 0.44, ow, c, 0.01)
    box('UPB_lobby_bench_plinth', x1 - 0.32, x1, 7.2, 8.7, f0, f0 + 0.06, M('black_plastic'), c, 0)
    # desk wall on the shower room: a tall bookcase beside the bunks, a desk with shelves over it
    cb0 = sy0 - 0.38
    box('UPB_case_back', x0 + 0.03, 9.6, sy0 - 0.02, sy0, f0, cz, ow, c, 0.002)
    for k, (a, b) in enumerate(((x0 + 0.03, x0 + 0.06), (9.57, 9.6))):
        box(f'UPB_case_side{k}', a, b, cb0, sy0 - 0.02, f0, cz, ow, c, 0.003)
    box('UPB_case_plinth', x0 + 0.06, 9.57, cb0, sy0 - 0.02, f0, f0 + 0.1, ow, c, 0.003)
    for k in range(6):
        z = f0 + 0.38 + 0.44 * k
        box(f'UPB_case_shelf{k}', x0 + 0.06, 9.57, cb0, sy0 - 0.02, z - 0.025, z, ow, c, 0.003)
        if k < 5:
            books_row(f'UPB_books{k}', c, x0 + 0.09, 9.54, sy0 - 0.03, z, 0.28, M('books_attr'), axis='X', seed=70 + k, face=-1)
    box('UPB_desk', 9.65, sx1, sy0 - 0.58, sy0, f0 + 0.72, f0 + 0.76, ow, c, 0.006)
    box('UPB_desk_pedestal', 9.65, 10.1, sy0 - 0.56, sy0, f0, f0 + 0.72, ow, c, 0.006)
    box('UPB_desk_end', sx1 - 0.04, sx1, sy0 - 0.58, sy0, f0, f0 + 0.72, ow, c, 0.004)
    for k, z in enumerate((f0 + 1.28, f0 + 1.7)):
        box(f'UPB_shelf{k}', 9.65, sx1, sy0 - 0.26, sy0, z, z + 0.03, ow, c, 0.004)
    books_row('UPB_deskbooks', c, 9.7, 10.35, sy0 - 0.02, f0 + 1.31, 0.22, M('books_attr'), axis='X', seed=81, face=-1)
    lathe('UPB_jar', [(0.0, 0.0), (0.06, 0.0), (0.07, 0.05), (0.06, 0.16), (0.0, 0.16)], c, M('ceramic'), 32, (10.55, sy0 - 0.12, f0 + 1.73))
    cyl('UPB_stool', 0.19, 0.43, (10.3, sy0 - 0.78, f0 + 0.215), ow, c, 32, bev=0.012)
    cyl('UPB_stool_pad', 0.18, 0.04, (10.3, sy0 - 0.78, f0 + 0.45), lake, c, 32, bev=0.012)
    cyl('UPB_desklamp_base', 0.07, 0.02, (10.55, sy0 - 0.2, f0 + 0.77), M('brass'), c, 24, bev=0.003)
    cyl('UPB_desklamp_stem', 0.006, 0.36, (10.55, sy0 - 0.2, f0 + 0.95), M('brass'), c, 8, bev=0)
    sh = lathe('UPB_desklamp_shade', [(0.03, 1.15 - 0.03), (0.1, 1.15 - 0.16)], c, M('brass'), 32, cap=False)
    sh.location = (10.55, sy0 - 0.25, f0)
    sh.modifiers.new('Solid', 'SOLIDIFY').thickness = 0.003
    point('UPB_desklamp_bulb', (10.55, sy0 - 0.25, f0 + 1.06), 8, 2700, lc, 0.03)
    # built-in bunks for four along the west wall: two bays, a lower and an upper berth in each
    bx1 = x0 + 1.05                                                    # front of the bunks (9.55)
    ya, yb = 1.1, 5.52
    mid = (ya + yb) / 2
    bays = ((ya + 0.04, mid - 0.02), (mid + 0.02, yb - 0.04))
    box('UPB_back', x0, x0 + 0.03, ya, yb, f0, cz, ow, c, 0.002)
    for k, y in enumerate((ya, mid - 0.02, yb - 0.04)):
        box(f'UPB_panel{k}', x0 + 0.03, bx1, y, y + 0.04, f0, cz, ow, c, 0.004)
    box('UPB_soffit', x0 + 0.03, bx1, ya, yb, cz - 0.4, cz, ow, c, 0.004)
    lo_top, up_base, up_top = f0 + 0.34, f0 + 1.46, f0 + 1.58
    xm = (x0 + 0.03 + bx1) / 2
    for n, (b0, b1) in enumerate(bays):
        box(f'UPB_base{n}', x0 + 0.03, bx1, b0, b1, f0, lo_top, ow, c, 0.006)
        for j in range(1, 3):
            yy = b0 + (b1 - b0) * j / 3
            box(f'UPB_drawer{n}{j}', bx1, bx1 + 0.004, yy - 0.003, yy + 0.003, f0 + 0.06, lo_top - 0.04, M('black_plastic'), c, 0)
        for j in range(3):
            sphere(f'UPB_knob{n}{j}', 0.018, (bx1 + 0.012, b0 + (b1 - b0) * (j + 0.5) / 3, f0 + 0.19), M('brass'), c, 2)
        box(f'UPB_deck{n}', x0 + 0.03, bx1, b0, b1, up_base, up_top, ow, c, 0.004)
        box(f'UPB_guard{n}', bx1 - 0.04, bx1, b0 + 0.55, b1, up_top, up_top + 0.24, ow, c, 0.004)
        for j, (zb, duvet) in enumerate(((lo_top, lake if n == 0 else sand), (up_top, sand if n == 0 else lake))):
            box(f'UPB_mat{n}{j}', x0 + 0.07, bx1 - 0.07, b0 + 0.03, b1 - 0.03, zb, zb + 0.17, cream, c, 0.05, 3)
            box(f'UPB_duvet{n}{j}', x0 + 0.06, bx1 - 0.05, b0 + 0.03, b1 - 0.6, zb + 0.15, zb + 0.23, duvet, c, 0.04, 3)
            cbox(f'UPB_pillow{n}{j}', (0.6, 0.34, 0.12), (xm, b1 - 0.3, zb + 0.24), cream, c,
                 rot=(0, 0, math.radians(R.uniform(-5, 5))), bev=0.05, seg=3)
            cyl(f'UPB_sconce{n}{j}', 0.045, 0.06, (x0 + 0.06, b1 - 0.16, zb + 0.72), M('brass'), c, 20, rot=(0, math.pi / 2, 0), bev=0.003)
            point(f'UPB_read{n}{j}', (x0 + 0.2, b1 - 0.16, zb + 0.66), 6, 2700, lc, 0.03)
        lx = bx1 + 0.035                                               # ladder at the south end of the bay
        for j, yy in enumerate((b0 + 0.08, b0 + 0.46)):
            box(f'UPB_rail{n}{j}', lx - 0.02, lx + 0.02, yy - 0.02, yy + 0.02, f0, up_top + 0.26, ow, c, 0.006)
        for j in range(5):
            # rungs stop at the rails' inner faces: a rung's only vertices are its end rings, and
            # buried inside the rails they would bake black (small objects carry light per vertex)
            cyl(f'UPB_rung{n}{j}', 0.014, 0.33, (lx, b0 + 0.27, f0 + 0.3 + 0.3 * j), ow, c, 12, rot=(math.pi / 2, 0, 0), bev=0)
    # window seat along the lake window, cushions against the glass; linen blinds raised
    ws = y0 + 0.55
    box('UPB_seat', x0, x1, y0, ws, f0, f0 + 0.42, ow, c, 0.008)
    for j in range(1, 4):
        xx = x0 + (x1 - x0) * j / 4
        box(f'UPB_seat_gap{j}', xx - 0.003, xx + 0.003, ws, ws + 0.004, f0 + 0.06, f0 + 0.38, M('black_plastic'), c, 0)
    box('UPB_seat_pad', x0 + 0.04, x1 - 0.04, y0 + 0.02, ws - 0.02, f0 + 0.42, f0 + 0.5, lake, c, 0.03, 3)
    for k, (xx, m) in enumerate(((9.0, sand), (9.55, cream), (11.35, sand), (11.95, lake))):
        cbox(f'UPB_seat_cush{k}', (0.46, 0.14, 0.4), (xx, y0 + 0.12, f0 + 0.68), m, c,
             rot=(math.radians(-14), 0, math.radians(R.uniform(-6, 6))), bev=0.06, seg=4)
    for k, (a, b) in enumerate(((x0 + 0.05, 10.45), (10.55, x1 - 0.05))):
        box(f'UPB_blind{k}', a, b, y0 + 0.02, y0 + 0.1, 6.18, 6.33, sand, c, 0.02, 2)
    # a chart of the lake over a low chest on the east wall, a toy sailboat on the chest
    cbox('UPB_art', (0.04, 2.1, 1.25), (x1 - 0.03, 1.25, f0 + 1.62), M('art_lake'), c, bev=0.004)
    box('UPB_chest', x1 - 0.42, x1, 0.15, 2.35, f0, f0 + 0.46, ow, c, 0.01)
    box('UPB_chest_gap', x1 - 0.424, x1 - 0.42, 1.247, 1.253, f0 + 0.04, f0 + 0.42, M('black_plastic'), c, 0)
    cbox('UPB_boat_hull', (0.09, 0.4, 0.07), (x1 - 0.2, 1.75, f0 + 0.5), M('walnut'), c, bev=0.03, seg=3)
    cyl('UPB_boat_mast', 0.005, 0.42, (x1 - 0.2, 1.77, f0 + 0.74), M('oak'), c, 8, bev=0)
    mesh_obj('UPB_boat_sail', [(x1 - 0.2, 1.79, f0 + 0.57), (x1 - 0.2, 2.0, f0 + 0.57), (x1 - 0.2, 1.79, f0 + 0.93)], [(0, 1, 2)], c, M('white_matte'))
    # round rug, low table, two poufs, three paper lanterns hung at different heights
    rx, ry = 10.65, 2.55
    cyl('UPB_rug', 1.05, 0.012, (rx, ry, f0 + 0.006), M('rug_lake'), c, 72, bev=0.003)
    cyl('UPB_table', 0.3, 0.36, (rx + 0.1, ry + 0.05, f0 + 0.18), ow, c, 48, bev=0.012)
    cyl('UPB_pouf0', 0.25, 0.4, (10.1, 1.75, f0 + 0.2), lake, c, 40, bev=0.05)
    cyl('UPB_pouf1', 0.23, 0.36, (10.05, 3.3, f0 + 0.18), sand, c, 40, bev=0.05)
    for k, (dx, dy, z, r) in enumerate(((-0.35, -0.3, 5.55, 0.24), (0.3, 0.2, 5.85, 0.19), (-0.15, 0.5, 5.3, 0.15))):
        paper_lantern(f'UPB_lantern{k}', c, (rx + 0.1 + dx, ry + 0.05 + dy, z), cz, lc, r)
    # light: a cool, even fill (the room is lighter than the others), art, lobby and window seat
    area('UPB_fill', ((x0 + x1) / 2, 2.0, cz - 0.05), 3.4, 75, 3300, lc, size_y=7.0, glossy=False)
    area('UPB_bounce', ((x0 + x1) / 2, 2.0, f0 + 0.6), 3.4, 35, 3300, lc, rot=(math.pi, 0, 0), size_y=7.0, glossy=False)
    spot('UPB_art_light', (x1 - 1.1, 1.25, cz - 0.04), 50, 40, 0.6, 3000, lc, aim=(x1, 1.25, f0 + 1.6))
    for k, y in enumerate((7.6, 9.4)):
        spot(f'UPB_lobby{k}', (11.65, y, cz - 0.04), 40, 70, 0.8, 2900, lc, aim=(11.6, y, f0))
    spot('UPB_seat_light', (10.5, -1.2, cz - 0.04), 40, 70, 0.8, 2800, lc, aim=(10.5, -1.6, f0 + 0.45))
    spot('UPB_bunk_wash', (10.6, 3.3, cz - 0.04), 45, 70, 0.8, 2900, lc, aim=(x0 + 0.5, 3.3, f0 + 1.2))

def upper_principal_suite(c, lc):
    """The principal suite (7.6 m wide): a freestanding travertine wall carries the bed and hides the
    dressing room behind it, under a raised, cove-lit coffer; a sitting corner at the east window.
    You walk it as a loop: in past the dressing room, round one end of the wall, out round the other.
    Travertine, charcoal wool, cream boucle, bronze."""
    f0, f1 = arch.UF0 + 0.02, arch.UF1
    x0, x1 = arch.PARTITIONS[1] + 0.1, 20.26                          # 12.7, east lining face
    y0 = -1.96
    tw0, tw1, ty0, ty1, th = 14.3, 18.7, 4.6, 4.9, 2.3                 # the travertine bed wall
    cx0, cx1, cy0, cy1, cd = arch.COFFER
    trav, char, cream, sand, bronze = M('travertine_wall'), M('fabric_char'), M('fabric_cream'), M('fabric_sand'), M('metal_dark')
    bx0, bx1, by0, (dy0, dy1) = arch.PRINCIPAL_BATH
    # the travertine wall, capped in bronze
    box('UPP_wall', tw0, tw1, ty0, ty1, f0, f0 + th, trav, c, 0.006)
    box('UPP_wall_cap', tw0, tw1, ty0, ty1, f0 + th, f0 + th + 0.015, bronze, c, 0.002)
    # the bed: dark oak platform floating on a shadow plinth, cream linen, a charcoal wool fold
    bc = (tw0 + tw1) / 2
    box('UPP_bedbase', bc - 1.2, bc + 1.2, 2.05, ty0 - 0.02, f0 + 0.05, f0 + 0.24, M('beam_dark'), c, 0.01)
    box('UPP_bedplinth', bc - 1.1, bc + 1.1, 2.15, ty0 - 0.12, f0, f0 + 0.05, M('black_plastic'), c, 0)
    box('UPP_mattress', bc - 1.1, bc + 1.1, 2.15, ty0 - 0.08, f0 + 0.24, f0 + 0.5, cream, c, 0.06, 4)
    box('UPP_duvet', bc - 1.13, bc + 1.13, 2.12, 3.15, f0 + 0.48, f0 + 0.55, char, c, 0.03, 3)
    for k, dx in enumerate((-0.72, 0.0, 0.72)):
        cbox(f'UPP_pillow{k}', (0.7, 0.18, 0.46), (bc + dx, ty0 - 0.32, f0 + 0.76), cream, c,
             rot=(math.radians(-10), 0, math.radians(R.uniform(-3, 3))), bev=0.07, seg=4)
    for k, dx in enumerate((-0.4, 0.4)):
        cbox(f'UPP_cushion{k}', (0.5, 0.15, 0.34), (bc + dx, ty0 - 0.52, f0 + 0.68), char, c,
             rot=(math.radians(-14), 0, 0), bev=0.06, seg=4)
    cyl('UPP_bolster', 0.1, 1.3, (bc, ty0 - 0.72, f0 + 0.6), sand, c, 32, rot=(0, math.pi / 2, 0), bev=0.03)
    # floating travertine bedside shelves, opal pendants on bronze cables
    for k, sx in enumerate((-1, 1)):
        nx = bc + sx * 1.62
        box(f'UPP_shelf{k}', nx - 0.32, nx + 0.32, ty0 - 0.42, ty0, f0 + 0.44, f0 + 0.52, trav, c, 0.004)
        globe_pendant(f'UPP_pendant{k}', c, (nx, ty0 - 0.26, f0 + 1.12), f1, lc)
    for k in range(3):
        cbox(f'UPP_book{k}', (0.23, 0.16, 0.03), (bc - 1.7, ty0 - 0.2, f0 + 0.535 + 0.031 * k), M('books'), c,
             rot=(0, 0, R.uniform(-0.25, 0.25)), bev=0.003)
    lathe('UPP_vessel', [(0.0, 0.0), (0.05, 0.0), (0.08, 0.06), (0.07, 0.17), (0.03, 0.24), (0.035, 0.27), (0.0, 0.27)], c, M('ceramic'), 40, (bc + 1.75, ty0 - 0.2, f0 + 0.52))
    # rug, a linen bench on bronze at the foot
    box('UPP_rug', bc - 2.0, bc + 2.0, 0.35, ty0 - 0.05, f0, f0 + 0.015, M('rug_dark'), c, 0.004)
    box('UPP_bench', bc - 0.85, bc + 0.85, 1.38, 1.82, f0 + 0.36, f0 + 0.46, sand, c, 0.03, 3)
    for k, dx in enumerate((-0.78, 0.78)):
        box(f'UPP_bench_leg{k}', bc + dx - 0.02, bc + dx + 0.02, 1.42, 1.78, f0, f0 + 0.36, bronze, c, 0.003)
    # sitting corner by the east window: two boucle tub chairs, a round Calacatta table, a drum lamp
    tx, ty = 19.25, 0.1
    cyl('UPP_table_top', 0.32, 0.03, (tx, ty, f0 + 0.5), M('marble'), c, 48, bev=0.006)
    cyl('UPP_table_stem', 0.035, 0.47, (tx, ty, f0 + 0.25), bronze, c, 16, bev=0)
    cyl('UPP_table_foot', 0.2, 0.02, (tx, ty, f0 + 0.01), bronze, c, 40, bev=0.003)
    lathe('UPP_bowl', [(0.0, 0.0), (0.06, 0.0), (0.11, 0.04), (0.12, 0.07), (0.11, 0.075), (0.0, 0.02)], c, M('ceramic'), 40, (tx - 0.08, ty + 0.06, f0 + 0.515))
    tub_chair('UPP_chairA', c, (19.7, 1.05, f0), math.radians(-31), cream)
    tub_chair('UPP_chairB', c, (18.3, -0.3, f0), math.radians(78), cream)
    drum_floor_lamp('UPP_floorlamp', c, (19.95, -1.5, f0), lc, 28)
    # dressing room behind the wall: oak wardrobes with bronze pulls, a console on the back of the wall
    wr0 = 6.4
    box('UPP_wardrobe', x0, x0 + 0.62, wr0, arch.GAL_Y, f0, f1, M('oak'), c, 0.004)
    for i in range(1, 6):
        y = wr0 + (arch.GAL_Y - wr0) * i / 6
        box(f'UPP_wr_gap{i}', x0 + 0.62, x0 + 0.624, y - 0.003, y + 0.003, f0 + 0.06, f1 - 0.06, M('black_plastic'), c, 0)
        box(f'UPP_wr_pull{i}', x0 + 0.624, x0 + 0.65, y - 0.07, y - 0.05, f0 + 0.75, f0 + 1.75, bronze, c, 0.003)
    box('UPP_wr_led', x0 + 0.62, x0 + 0.63, wr0 + 0.1, arch.GAL_Y - 0.1, f1 - 0.02, f1 - 0.01, M('warm_soft'), c, 0)
    box('UPP_console', 15.2, 17.4, ty1, ty1 + 0.36, f0 + 0.7, f0 + 0.76, M('beam_dark'), c, 0.005)
    for k, x in enumerate((15.3, 17.3)):
        box(f'UPP_console_leg{k}', x - 0.015, x + 0.015, ty1 + 0.02, ty1 + 0.34, f0, f0 + 0.7, bronze, c, 0.003)
    lathe('UPP_console_vase', [(0.0, 0.0), (0.07, 0.0), (0.12, 0.1), (0.1, 0.32), (0.05, 0.42), (0.06, 0.46), (0.0, 0.46)], c, M('ceramic'), 40, (15.7, ty1 + 0.18, f0 + 0.76))
    lathe('UPP_console_bowl', [(0.0, 0.0), (0.1, 0.0), (0.16, 0.05), (0.17, 0.08), (0.16, 0.085), (0.0, 0.03)], c, M('ceramic'), 40, (16.9, ty1 + 0.18, f0 + 0.76))
    # the pair of doors from the gallery, standing open; the bathroom door, closed
    d0, d1, dh = arch.GAL_DOORS[2]
    for k, (x, face) in enumerate(((d0 + 0.02, 1), (d1 - 0.06, -1))):
        box(f'UPP_door{k}', x, x + 0.04, arch.GAL_Y - 0.82, arch.GAL_Y - 0.02, f0, f0 + dh - 0.02, M('oak'), c, 0.003)
        px = x + 0.04 if face > 0 else x - 0.025   # pull on the face towards the room's middle
        box(f'UPP_door{k}_pull', px, px + 0.025, arch.GAL_Y - 0.74, arch.GAL_Y - 0.72, f0 + 0.85, f0 + 1.35, bronze, c, 0.003)
    box('UPP_bathdoor', bx0 + 0.005, bx0 + 0.045, dy0 + 0.01, dy1 - 0.01, f0, f0 + 2.17, M('oak'), c, 0.003)
    box('UPP_bathdoor_pull', bx0 - 0.02, bx0 + 0.005, dy0 + 0.1, dy0 + 0.12, f0 + 0.85, f0 + 1.35, bronze, c, 0.003)
    # sheers drawn back at both ends of the lake window
    curtain('UPP_sheerW', c, x0 + 0.1, x0 + 0.75, -1.8, f0 + 0.03, f1 - 0.05, M('sheer'), folds=6, amp=0.06)
    curtain('UPP_sheerE', c, 18.25, 18.85, -1.8, f0 + 0.03, f1 - 0.05, M('sheer'), folds=6, amp=0.06)
    # light: the coffer's cove, the pendants, grazing light on the travertine, lamp-lit sitting corner
    ctop = f1 + cd
    for k, (a0, a1, b0, b1) in enumerate(((cx0, cx0 + 0.01, cy0, cy1), (cx1 - 0.01, cx1, cy0, cy1),
                                          (cx0, cx1, cy0, cy0 + 0.01), (cx0, cx1, cy1 - 0.01, cy1))):
        box(f'UPP_cove{k}', a0, a1, b0, b1, ctop - 0.06, ctop - 0.04, M('warm_soft'), c, 0)
    for k, (x, y, sxl, syl) in enumerate((((cx0 + cx1) / 2, cy0 + 0.15, cx1 - cx0 - 0.3, 0.2), ((cx0 + cx1) / 2, cy1 - 0.15, cx1 - cx0 - 0.3, 0.2),
                                         (cx0 + 0.15, (cy0 + cy1) / 2, 0.2, cy1 - cy0 - 0.6), (cx1 - 0.15, (cy0 + cy1) / 2, 0.2, cy1 - cy0 - 0.6))):
        area(f'UPP_cove_light{k}', (x, y, f1 + 0.02), sxl, 45, 2800, lc, rot=(math.pi, 0, 0), size_y=syl, glossy=False)
    area('UPP_fill', (bc, 1.6, ctop - 0.05), 4.6, 70, 2900, lc, size_y=4.6, glossy=False)
    area('UPP_bounce', (bc, 1.6, f0 + 0.6), 4.6, 40, 3000, lc, rot=(math.pi, 0, 0), size_y=4.6, glossy=False)
    for k, x in enumerate((bc - 1.5, bc, bc + 1.5)):
        spot(f'UPP_graze{k}', (x, ty0 - 0.55, ctop - 0.04), 55, 50, 0.8, 2900, lc, aim=(x, ty0, f0 + 0.9))
    spot('UPP_table_light', (tx, ty, f1 - 0.04), 40, 40, 0.7, 2800, lc, aim=(tx, ty, f0 + 0.5))
    for k, y in enumerate((6.4, 8.6)):
        spot(f'UPP_dress{k}', (15.6, y, f1 - 0.04), 50, 75, 0.85, 2900, lc, aim=(14.2, y, f0 + 0.6))
    area('UPP_dress_fill', (15.8, 7.6, f1 - 0.06), 3.6, 70, 2900, lc, size_y=3.4, glossy=False)
    spot('UPP_console_light', (16.3, ty1 + 0.9, f1 - 0.04), 40, 50, 0.7, 2900, lc, aim=(16.3, ty1 + 0.18, f0 + 0.8))

def upper_rooms(c, lc):
    upper_gallery(c, lc)
    upper_suite_west(c, lc)
    upper_bunk_room(c, lc)
    upper_principal_suite(c, lc)

def build():
    MATS['limestone_wall'] = m_stone_slab('Limestone_Wall', '#d6cdbf', '#c3b8a6', 0.5, (1.2, 0.6), 0.0015, axis='WALL')
    MATS['travertine'] = m_stone_slab('Travertine', '#d8c7ad', '#c6b293', 0.45, (2.0, 2.0), 0.0)
    # upstairs: the bunk room's limed oak and lake-blue linen, the principal suite's travertine
    MATS['travertine_wall'] = m_stone_slab('Travertine_Wall', '#dac9ae', '#c3ae8f', 0.55, (1.2, 0.6), 0.0015, axis='WALL')
    MATS['oak_white'] = m_wood_planks('Oak_White', '#e1cdae', '#b99e7a', 0.3, 3.0, 'X', 0.42, coord='object', plank=False)
    MATS['oak_boards'] = m_wood_planks('Oak_White_Boards', '#e4d4ba', '#c0a785', 0.14, 3.2, 'Y', 0.6, seam=0.004)
    MATS['fabric_lake'] = m_fabric('Linen_Lake', '#6d8592')
    MATS['rug_lake'] = m_rug('Rug_Lake', '#d5d8d4', '#9babb0')
    MATS['art_lake'] = m_canvas_art('Art_Lake', ['#eceeea', '#a3b6bf', '#55707f', '#dacdb4', '#2d3c46'], 6.1)
    MATS['emit_paper'] = m_emit('Emit_Paper', kelvin=3000, strength=1.8)
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
