"""HALCYON residence — shared helpers and procedural PBR materials (Blender 5.2)."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Euler

# ---------------------------------------------------------------- colour utils
def srgb(h, a=1.0):
    """'#rrggbb' sRGB -> linear RGBA tuple."""
    h = h.lstrip('#')
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (out[0], out[1], out[2], a)

# ---------------------------------------------------------------- collections
def coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c

def wipe_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for blocks in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras,
                   bpy.data.curves, bpy.data.node_groups, bpy.data.images, bpy.data.textures,
                   bpy.data.worlds, bpy.data.particles):
        for b in list(blocks):
            try:
                blocks.remove(b)
            except Exception:
                pass

# ---------------------------------------------------------------- mesh builders
def mesh_obj(name, verts, faces, c, mat=None, smooth=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate()
    me.update()
    ob = bpy.data.objects.new(name, me)
    c.objects.link(ob)
    if mat:
        me.materials.append(mat)
    if smooth:
        me.shade_smooth()
    return ob

BOX_FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]

def bevel(ob, w=0.01, seg=2, angle=40):
    if w <= 0:
        return ob
    m = ob.modifiers.new('Bevel', 'BEVEL')
    m.width = w
    m.segments = seg
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(angle)
    m.harden_normals = True
    ob.data.shade_smooth()
    return ob

def box(name, x0, x1, y0, y1, z0, z1, mat, c, bev=0.008, seg=2):
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    z0, z1 = min(z0, z1), max(z0, z1)
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    ob = mesh_obj(name, v, BOX_FACES, c, mat)
    bevel(ob, bev, seg)
    return ob

def cbox(name, size, loc, mat, c, rot=(0, 0, 0), bev=0.008, seg=2):
    """Centered box with rotation (radians)."""
    sx, sy, sz = (s / 2 for s in size)
    ob = box(name, -sx, sx, -sy, sy, -sz, sz, mat, c, bev, seg)
    ob.location = loc
    ob.rotation_euler = rot
    return ob

def cyl(name, r, h, loc, mat, c, verts=32, rot=(0, 0, 0), bev=0.004, r2=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=verts,
                          radius1=r, radius2=r if r2 is None else r2, depth=h)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    c.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = rot
    if mat:
        me.materials.append(mat)
    me.shade_smooth()
    if bev:
        m = ob.modifiers.new('Bevel', 'BEVEL')
        m.width = bev
        m.segments = 2
        m.limit_method = 'ANGLE'
        m.harden_normals = True
    return ob

def torus(name, R, r, loc, mat, c, rot=(0, 0, 0), maj=64, minr=12):
    bm = bmesh.new()
    verts = []
    for i in range(maj):
        a = 2 * math.pi * i / maj
        ring = []
        for j in range(minr):
            b = 2 * math.pi * j / minr
            x = (R + r * math.cos(b)) * math.cos(a)
            y = (R + r * math.cos(b)) * math.sin(a)
            z = r * math.sin(b)
            ring.append(bm.verts.new((x, y, z)))
        verts.append(ring)
    for i in range(maj):
        for j in range(minr):
            a = verts[i][j]; b = verts[(i + 1) % maj][j]
            cc = verts[(i + 1) % maj][(j + 1) % minr]; d = verts[i][(j + 1) % minr]
            bm.faces.new((a, b, cc, d))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    c.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = rot
    if mat:
        me.materials.append(mat)
    return ob

def sphere(name, r, loc, mat, c, sub=3, scale=(1, 1, 1)):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    c.objects.link(ob)
    ob.location = loc
    ob.scale = scale
    if mat:
        me.materials.append(mat)
    return ob

def plane(name, x0, x1, y0, y1, z, mat, c):
    return mesh_obj(name, [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], [(0, 1, 2, 3)], c, mat)

def vplane(name, p0, p1, z0, z1, mat, c):
    """Vertical quad between two XY points."""
    (ax, ay), (bx, by) = p0, p1
    return mesh_obj(name, [(ax, ay, z0), (bx, by, z0), (bx, by, z1), (ax, ay, z1)], [(0, 1, 2, 3)], c, mat)

def subsurf(ob, lv=2, render=None):
    m = ob.modifiers.new('Subsurf', 'SUBSURF')
    m.levels = lv
    m.render_levels = lv if render is None else render
    return m

def join(objs, name):
    """Join meshes (keeps materials)."""
    ctx = bpy.context
    ctx.view_layer.update()
    for o in objs:
        o.select_set(True)
    ctx.view_layer.objects.active = objs[0]
    with ctx.temp_override(active_object=objs[0], selected_editable_objects=objs, selected_objects=objs):
        bpy.ops.object.join()
    objs[0].name = name
    return objs[0]

def apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)

# ---------------------------------------------------------------- node helpers
def new_mat(name):
    m = bpy.data.materials.get(name)
    if m:
        bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    return m, nt, out

def N(nt, t, inputs=None, **props):
    n = nt.nodes.new(t)
    for k, v in props.items():
        setattr(n, k, v)
    if inputs:
        for k, v in inputs.items():
            n.inputs[k].default_value = v
    return n

def L(nt, a, b):
    nt.links.new(a, b)

def principled(nt, base=None, rough=0.5, metal=0.0, **kw):
    p = N(nt, 'ShaderNodeBsdfPrincipled')
    if base is not None:
        if isinstance(base, tuple):
            p.inputs['Base Color'].default_value = base
        else:
            L(nt, base, p.inputs['Base Color'])
    if isinstance(rough, (int, float)):
        p.inputs['Roughness'].default_value = rough
    else:
        L(nt, rough, p.inputs['Roughness'])
    p.inputs['Metallic'].default_value = metal
    for k, v in kw.items():
        p.inputs[k].default_value = v
    return p

def ramp(nt, fac, stops):
    r = N(nt, 'ShaderNodeValToRGB')
    el = r.color_ramp.elements
    while len(el) > 2:
        el.remove(el[-1])
    for i, (pos, col) in enumerate(stops):
        e = el[i] if i < 2 else el.new(pos)
        e.position = pos
        e.color = col
    L(nt, fac, r.inputs['Fac'])
    return r

def math_node(nt, op, a, b=None, clamp=False):
    n = N(nt, 'ShaderNodeMath', operation=op, use_clamp=clamp)
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            L(nt, v, n.inputs[i])
    return n.outputs[0]

def mix_rgb(nt, fac, a, b, blend='MIX'):
    n = N(nt, 'ShaderNodeMix', data_type='RGBA', blend_type=blend)
    if isinstance(fac, (int, float)):
        n.inputs[0].default_value = fac
    else:
        L(nt, fac, n.inputs[0])
    for idx, v in ((6, a), (7, b)):
        if isinstance(v, tuple):
            n.inputs[idx].default_value = v
        else:
            L(nt, v, n.inputs[idx])
    return n.outputs[2]

def pos_vec(nt, mode='world'):
    if mode == 'world':
        g = N(nt, 'ShaderNodeNewGeometry')
        return g.outputs['Position']
    t = N(nt, 'ShaderNodeTexCoord')
    return t.outputs['Object']

def scale_vec(nt, vec, s):
    n = N(nt, 'ShaderNodeVectorMath', operation='MULTIPLY')
    L(nt, vec, n.inputs[0])
    n.inputs[1].default_value = s
    return n.outputs[0]

def add_vec(nt, a, b):
    n = N(nt, 'ShaderNodeVectorMath', operation='ADD')
    L(nt, a, n.inputs[0])
    if isinstance(b, tuple):
        n.inputs[1].default_value = b
    else:
        L(nt, b, n.inputs[1])
    return n.outputs[0]

def swizzle(nt, vec, order):
    """order e.g. ('X+Y','Z',None) using separate/combine."""
    sep = N(nt, 'ShaderNodeSeparateXYZ')
    L(nt, vec, sep.inputs[0])
    comb = N(nt, 'ShaderNodeCombineXYZ')
    for i, key in enumerate(order):
        if key is None:
            continue
        if key == 'X+Y':
            L(nt, math_node(nt, 'ADD', sep.outputs['X'], sep.outputs['Y']), comb.inputs[i])
        else:
            L(nt, sep.outputs[key], comb.inputs[i])
    return comb.outputs[0]

NOISE_DETAIL_CAP = 4.0  # render-time budget: every octave is re-evaluated by bump nodes

def noise(nt, vec, scale=5.0, detail=4.0, rough=0.5, dist=0.0, dims='3D'):
    detail = min(detail, NOISE_DETAIL_CAP)
    n = N(nt, 'ShaderNodeTexNoise', noise_dimensions=dims)
    if vec is not None:
        L(nt, vec, n.inputs['Vector'])
    n.inputs['Scale'].default_value = scale
    n.inputs['Detail'].default_value = detail
    n.inputs['Roughness'].default_value = rough
    n.inputs['Distortion'].default_value = dist
    return n

def bump(nt, height, strength=0.1, dist=0.02, normal=None):
    b = N(nt, 'ShaderNodeBump')
    b.inputs['Strength'].default_value = strength
    b.inputs['Distance'].default_value = dist
    L(nt, height, b.inputs['Height'])
    if normal is not None:
        L(nt, normal, b.inputs['Normal'])
    return b.outputs['Normal']

def finish(nt, out, shader):
    L(nt, shader.outputs[0] if hasattr(shader, 'outputs') else shader, out.inputs['Surface'])

# ---------------------------------------------------------------- materials
MATS = {}

def M(key):
    return MATS[key]

def m_simple(name, col, rough=0.5, metal=0.0, **kw):
    m, nt, out = new_mat(name)
    p = principled(nt, col, rough, metal, **kw)
    finish(nt, out, p)
    return m

def m_plaster(name, col='#ebe6dd', rough=0.88, scale=1.0):
    m, nt, out = new_mat(name)
    v = pos_vec(nt)
    n1 = noise(nt, v, 18.0 * scale, 8, 0.62)
    n2 = noise(nt, v, 1.6, 3, 0.5)
    c = mix_rgb(nt, math_node(nt, 'MULTIPLY', n2.outputs['Fac'], 0.10), srgb(col), srgb('#d8d1c4'))
    p = principled(nt, c, rough)
    L(nt, bump(nt, n1.outputs['Fac'], 0.06, 0.01), p.inputs['Normal'])
    finish(nt, out, p)
    return m

def m_wood_planks(name, c_light, c_dark, plank_w=0.19, plank_l=2.4, axis='X', rough=0.38,
                  seam=0.0018, coord='world', grain_scale=1.0, plank=True):
    m, nt, out = new_mat(name)
    v = pos_vec(nt, coord)
    vv = swizzle(nt, v, ('X', 'Y', 'Z') if axis == 'X' else (('Y', 'X', 'Z') if axis == 'Y' else ('Z', 'X+Y', None)))
    br = None
    if plank:
        br = N(nt, 'ShaderNodeTexBrick', offset=0.41, offset_frequency=1, squash=1.0, squash_frequency=1)
        for k, val in {'Color1': (0, 0, 0, 1), 'Color2': (1, 1, 1, 1), 'Mortar': (0, 0, 0, 1), 'Scale': 1.0,
                       'Mortar Size': seam, 'Mortar Smooth': 0.3, 'Bias': 0.0, 'Brick Width': plank_l,
                       'Row Height': plank_w}.items():
            br.inputs[k].default_value = val
        L(nt, vv, br.inputs['Vector'])
        rnd = N(nt, 'ShaderNodeSeparateColor')
        L(nt, br.outputs['Color'], rnd.inputs[0])
        rv = rnd.outputs[0]
        off = N(nt, 'ShaderNodeCombineXYZ')
        L(nt, math_node(nt, 'MULTIPLY', rv, 31.7), off.inputs[0])
        L(nt, math_node(nt, 'MULTIPLY', rv, 17.3), off.inputs[1])
        L(nt, math_node(nt, 'MULTIPLY', rv, 7.1), off.inputs[2])
        vg = add_vec(nt, vv, off.outputs[0])
    else:
        rv = None
        vg = vv
    stretched = scale_vec(nt, vg, (0.5 * grain_scale, 48.0 * grain_scale, 48.0 * grain_scale))
    streak = noise(nt, stretched, 1.0, 10, 0.62)
    rings = N(nt, 'ShaderNodeTexWave', wave_type='BANDS', bands_direction='Y', wave_profile='SIN')
    L(nt, scale_vec(nt, vg, (0.25 * grain_scale, 1.0 * grain_scale, 1.0 * grain_scale)), rings.inputs['Vector'])
    rings.inputs['Scale'].default_value = 5.0 if plank else 3.0
    rings.inputs['Distortion'].default_value = 4.0 if plank else 3.5
    rings.inputs['Detail'].default_value = 2.0 if plank else 1.5
    rw = 0.2 if plank else 0.18
    fac = math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', streak.outputs['Fac'], 1.0 - rw),
                    math_node(nt, 'MULTIPLY', rings.outputs['Fac'], rw))
    col = ramp(nt, fac, [(0.30, srgb(c_dark)), (0.72, srgb(c_light))]).outputs['Color']
    if rv is not None:
        tint = ramp(nt, rv, [(0.0, (0.78, 0.74, 0.70, 1)), (1.0, (1.0, 1.0, 1.0, 1))]).outputs['Color']
        col = mix_rgb(nt, 1.0, col, tint, 'MULTIPLY')
        col = mix_rgb(nt, br.outputs['Fac'], col, srgb('#1a120c'))
    rgh = math_node(nt, 'ADD', rough, math_node(nt, 'MULTIPLY', streak.outputs['Fac'], 0.18))
    p = principled(nt, col, rgh)
    h = math_node(nt, 'MULTIPLY', streak.outputs['Fac'], 0.4)
    if br is not None:
        h = math_node(nt, 'ADD', h, math_node(nt, 'SUBTRACT', 1.0, br.outputs['Fac']))
    L(nt, bump(nt, h, 0.18, 0.004), p.inputs['Normal'])
    finish(nt, out, p)
    return m

def m_stone_cladding(name, tones, bw=0.95, rh=0.32, rough=0.78, mortar='#8d857a'):
    m, nt, out = new_mat(name)
    v = pos_vec(nt)
    vv = swizzle(nt, v, ('X+Y', 'Z', None))
    br = N(nt, 'ShaderNodeTexBrick', offset=0.5, offset_frequency=2, squash=0.62, squash_frequency=3)
    for k, val in {'Color1': (0, 0, 0, 1), 'Color2': (1, 1, 1, 1), 'Mortar': (0, 0, 0, 1), 'Scale': 1.0,
                   'Mortar Size': 0.007, 'Mortar Smooth': 0.6, 'Bias': 0.0, 'Brick Width': bw,
                   'Row Height': rh}.items():
        br.inputs[k].default_value = val
    L(nt, vv, br.inputs['Vector'])
    rsep = N(nt, 'ShaderNodeSeparateColor')
    L(nt, br.outputs['Color'], rsep.inputs[0])
    stops = [(i / max(1, len(tones) - 1), srgb(t)) for i, t in enumerate(tones)]
    tone = ramp(nt, rsep.outputs[0], stops)
    tone.color_ramp.interpolation = 'CONSTANT'
    n1 = noise(nt, v, 9.0, 12, 0.66)
    n2 = noise(nt, v, 1.2, 4, 0.5)
    vor = N(nt, 'ShaderNodeTexVoronoi', feature='F1')
    L(nt, v, vor.inputs['Vector'])
    vor.inputs['Scale'].default_value = 22.0
    col = mix_rgb(nt, 0.35, tone.outputs['Color'],
                  ramp(nt, n1.outputs['Fac'], [(0.35, srgb('#8f8678')), (0.65, srgb('#e6e0d6'))]).outputs['Color'], 'OVERLAY')
    col = mix_rgb(nt, math_node(nt, 'MULTIPLY', n2.outputs['Fac'], 0.25), col, srgb('#7d7466'), 'MULTIPLY')
    col = mix_rgb(nt, math_node(nt, 'SUBTRACT', 1.0, br.outputs['Fac']), col, srgb(mortar))
    rgh = math_node(nt, 'ADD', rough, math_node(nt, 'MULTIPLY', n1.outputs['Fac'], 0.12))
    p = principled(nt, col, rgh)
    face = math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', n1.outputs['Fac'], 0.35),
                     math_node(nt, 'MULTIPLY', vor.outputs['Distance'], 0.25))
    h = math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', br.outputs['Fac'], 1.0), face)
    L(nt, bump(nt, h, 0.55, 0.02), p.inputs['Normal'])
    finish(nt, out, p)
    return m

def m_stone_ledger(name, tones, su=0.95, sv=6.8, rough=0.8, mortar='#6f6a62', depth=0.6):
    """Split-face ledgestone: irregular elongated stones (Voronoi), per-stone tone + relief."""
    m, nt, out = new_mat(name)
    v = pos_vec(nt)
    vv = scale_vec(nt, swizzle(nt, v, ('X+Y', 'Z', None)), (su, sv, 1.0))
    vf = N(nt, 'ShaderNodeTexVoronoi', feature='F1', distance='CHEBYCHEV', voronoi_dimensions='2D')
    ve = N(nt, 'ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE', distance='CHEBYCHEV', voronoi_dimensions='2D')
    for vn in (vf, ve):
        L(nt, vv, vn.inputs['Vector'])
        vn.inputs['Scale'].default_value = 1.0
        vn.inputs['Randomness'].default_value = 0.55
    rs = N(nt, 'ShaderNodeSeparateColor')
    L(nt, vf.outputs['Color'], rs.inputs[0])
    tone = ramp(nt, rs.outputs[0], [(i / max(1, len(tones) - 1), srgb(t)) for i, t in enumerate(tones)])
    tone.color_ramp.interpolation = 'CONSTANT'
    joint = ramp(nt, ve.outputs['Distance'], [(0.0, (0, 0, 0, 1)), (0.028, (1, 1, 1, 1))]).outputs['Color']
    split = noise(nt, scale_vec(nt, v, (3.0, 3.0, 3.0)), 3.0, 12, 0.72)
    grain = noise(nt, v, 40.0, 6, 0.6)
    col = mix_rgb(nt, 0.4, tone.outputs['Color'],
                  ramp(nt, split.outputs['Fac'], [(0.3, srgb('#7f776b')), (0.7, srgb('#e2dccf'))]).outputs['Color'], 'OVERLAY')
    col = mix_rgb(nt, 0.1, col, grain.outputs['Color'], 'OVERLAY')
    col = mix_rgb(nt, math_node(nt, 'SUBTRACT', 1.0, joint), col, srgb(mortar))
    rgh = math_node(nt, 'ADD', rough, math_node(nt, 'MULTIPLY', split.outputs['Fac'], 0.1))
    p = principled(nt, col, rgh)
    relief = math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', rs.outputs[1], 0.35), math_node(nt, 'MULTIPLY', split.outputs['Fac'], 0.65))
    h = math_node(nt, 'MULTIPLY', joint, relief)
    L(nt, bump(nt, h, depth, 0.03), p.inputs['Normal'])
    finish(nt, out, p)
    return m

def m_stone_slab(name, col='#d9d2c5', col2='#c4baa9', rough=0.42, tile=(1.2, 0.6), joint=0.002, axis='XY'):
    """Honed limestone / large format tiles (floor or wall)."""
    m, nt, out = new_mat(name)
    v = pos_vec(nt)
    vv = swizzle(nt, v, ('X', 'Y', None) if axis == 'XY' else ('X+Y', 'Z', None))
    br = N(nt, 'ShaderNodeTexBrick', offset=0.5, offset_frequency=2, squash=1, squash_frequency=1)
    for k, val in {'Color1': (0, 0, 0, 1), 'Color2': (1, 1, 1, 1), 'Mortar': (0, 0, 0, 1), 'Scale': 1.0,
                   'Mortar Size': joint, 'Mortar Smooth': 0.2, 'Bias': 0.0, 'Brick Width': tile[0],
                   'Row Height': tile[1]}.items():
        br.inputs[k].default_value = val
    L(nt, vv, br.inputs['Vector'])
    rs = N(nt, 'ShaderNodeSeparateColor')
    L(nt, br.outputs['Color'], rs.inputs[0])
    n1 = noise(nt, v, 3.0, 10, 0.6)
    n2 = noise(nt, v, 40.0, 6, 0.6)
    base = mix_rgb(nt, math_node(nt, 'MULTIPLY', rs.outputs[0], 0.6), srgb(col), srgb(col2))
    base = mix_rgb(nt, math_node(nt, 'MULTIPLY', n1.outputs['Fac'], 0.5), base, srgb(col2))
    base = mix_rgb(nt, 0.12, base, n2.outputs['Color'], 'OVERLAY')
    base = mix_rgb(nt, br.outputs['Fac'], base, srgb('#9b9385'))
    rg = math_node(nt, 'ADD', rough, math_node(nt, 'MULTIPLY', n1.outputs['Fac'], 0.12))
    p = principled(nt, base, rg)
    h = math_node(nt, 'ADD', math_node(nt, 'SUBTRACT', 1.0, br.outputs['Fac']), math_node(nt, 'MULTIPLY', n2.outputs['Fac'], 0.05))
    L(nt, bump(nt, h, 0.3, 0.003), p.inputs['Normal'])
    finish(nt, out, p)
    return m

def m_marble(name, base='#f2f0ec', vein='#7d7a75', gold='#a39279', rough=0.12, coord='world', scale=1.0):
    m, nt, out = new_mat(name)
    v = pos_vec(nt, coord)
    v = scale_vec(nt, v, (scale, scale, scale))
    warp = noise(nt, v, 1.4, 8, 0.62)
    vw = add_vec(nt, v, scale_vec(nt, warp.outputs['Color'], (1.8, 1.8, 1.8)))
    wave = N(nt, 'ShaderNodeTexWave', wave_type='BANDS', bands_direction='DIAGONAL', wave_profile='SIN')
    L(nt, vw, wave.inputs['Vector'])
    wave.inputs['Scale'].default_value = 0.55
    wave.inputs['Distortion'].default_value = 7.0
    wave.inputs['Detail'].default_value = 3.0
    wave.inputs['Detail Roughness'].default_value = 0.7
    veins = ramp(nt, wave.outputs['Fac'], [(0.0, (1, 1, 1, 1)), (0.03, (0.35, 0.35, 0.35, 1)), (0.09, (0, 0, 0, 1))])
    fine = noise(nt, vw, 6.0, 12, 0.7)
    fv = ramp(nt, fine.outputs['Fac'], [(0.48, (0, 0, 0, 1)), (0.5, (1, 1, 1, 1)), (0.52, (0, 0, 0, 1))])
    vmask = math_node(nt, 'MAXIMUM', veins.outputs['Color'], math_node(nt, 'MULTIPLY', fv.outputs['Color'], 0.12))
    clouds = noise(nt, v, 2.5, 6, 0.5)
    b = mix_rgb(nt, math_node(nt, 'MULTIPLY', clouds.outputs['Fac'], 0.25), srgb(base), srgb('#e4ded5'))
    vc = mix_rgb(nt, clouds.outputs['Fac'], srgb(vein), srgb(gold))
    col = mix_rgb(nt, vmask, b, vc)
    p = principled(nt, col, rough)
    L(nt, bump(nt, vmask, 0.02, 0.002), p.inputs['Normal'])
    finish(nt, out, p)
    return m

def m_metal(name, col='#1b1c1e', rough=0.32, aniso=0.0):
    m, nt, out = new_mat(name)
    v = pos_vec(nt)
    n = noise(nt, v, 60, 6, 0.6)
    rg = math_node(nt, 'ADD', rough, math_node(nt, 'MULTIPLY', n.outputs['Fac'], 0.08))
    p = principled(nt, srgb(col), rg, 1.0, **{'Anisotropic': aniso})
    finish(nt, out, p)
    return m

def m_glass_window(name, tint='#e9f0ef'):
    """Architectural thin glazing — reflection + transparency; shadow rays pass through."""
    m, nt, out = new_mat(name)
    lp = N(nt, 'ShaderNodeLightPath')
    lw = N(nt, 'ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.12
    tr = N(nt, 'ShaderNodeBsdfTransparent')
    tr.inputs['Color'].default_value = srgb(tint)
    gl = N(nt, 'ShaderNodeBsdfGlossy')
    gl.inputs['Roughness'].default_value = 0.0
    gl.inputs['Color'].default_value = (1, 1, 1, 1)
    fres = math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', lw.outputs['Fresnel'], 0.9), 0.06, clamp=True)
    mx = N(nt, 'ShaderNodeMixShader')
    L(nt, fres, mx.inputs[0]); L(nt, tr.outputs[0], mx.inputs[1]); L(nt, gl.outputs[0], mx.inputs[2])
    tr2 = N(nt, 'ShaderNodeBsdfTransparent')
    mx2 = N(nt, 'ShaderNodeMixShader')
    L(nt, lp.outputs['Is Shadow Ray'], mx2.inputs[0]); L(nt, mx.outputs[0], mx2.inputs[1]); L(nt, tr2.outputs[0], mx2.inputs[2])
    finish(nt, out, mx2)
    return m

def m_glass_solid(name, tint='#f4f7f6', rough=0.0):
    m, nt, out = new_mat(name)
    p = principled(nt, srgb(tint), rough, **{'Transmission Weight': 1.0, 'IOR': 1.5})
    finish(nt, out, p)
    return m

def m_emit(name, col='#ffd9a8', strength=10.0, kelvin=None):
    m, nt, out = new_mat(name)
    e = N(nt, 'ShaderNodeEmission')
    if kelvin:
        bb = N(nt, 'ShaderNodeBlackbody')
        bb.inputs['Temperature'].default_value = kelvin
        L(nt, bb.outputs[0], e.inputs['Color'])
    else:
        e.inputs['Color'].default_value = srgb(col)
    e.inputs['Strength'].default_value = strength
    finish(nt, out, e)
    return m

def m_fabric(name, col, rough=0.9, sheen=0.6, scale=1.0, coord='object'):
    m, nt, out = new_mat(name)
    v = pos_vec(nt, coord)
    n1 = noise(nt, v, 260 * scale, 4, 0.7)
    n2 = noise(nt, v, 9 * scale, 5, 0.5)
    c = mix_rgb(nt, math_node(nt, 'MULTIPLY', n2.outputs['Fac'], 0.18), srgb(col), (0.0, 0.0, 0.0, 1))
    p = principled(nt, c, rough, **{'Sheen Weight': sheen, 'Sheen Roughness': 0.4})
    L(nt, bump(nt, n1.outputs['Fac'], 0.35, 0.002), p.inputs['Normal'])
    finish(nt, out, p)
    return m

def m_leather(name, col='#8a5532', rough=0.42):
    m, nt, out = new_mat(name)
    v = pos_vec(nt, 'object')
    vor = N(nt, 'ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE')
    L(nt, v, vor.inputs['Vector'])
    vor.inputs['Scale'].default_value = 140
    n = noise(nt, v, 6, 4, 0.5)
    c = mix_rgb(nt, math_node(nt, 'MULTIPLY', n.outputs['Fac'], 0.35), srgb(col), srgb('#4a2a17'))
    p = principled(nt, c, math_node(nt, 'ADD', rough, math_node(nt, 'MULTIPLY', n.outputs['Fac'], 0.15)),
                   **{'Coat Weight': 0.15, 'Coat Roughness': 0.3})
    L(nt, bump(nt, vor.outputs['Distance'], 0.15, 0.003), p.inputs['Normal'])
    finish(nt, out, p)
    return m

def m_rug(name, c1='#cfc4b2', c2='#a89880'):
    m, nt, out = new_mat(name)
    v = pos_vec(nt, 'object')
    n1 = noise(nt, v, 400, 3, 0.8)
    n2 = noise(nt, v, 4, 6, 0.6, dist=1.5)
    c = ramp(nt, n2.outputs['Fac'], [(0.35, srgb(c1)), (0.7, srgb(c2))]).outputs['Color']
    p = principled(nt, c, 0.96, **{'Sheen Weight': 0.25, 'Sheen Roughness': 0.5})
    L(nt, bump(nt, n1.outputs['Fac'], 0.6, 0.004), p.inputs['Normal'])
    finish(nt, out, p)
    return m

def m_random_tint(name, cols, rough=0.6, coat=0.0):
    """Per-object colour from a palette via Object Info random (books, ceramics)."""
    m, nt, out = new_mat(name)
    oi = N(nt, 'ShaderNodeObjectInfo')
    r = ramp(nt, oi.outputs['Random'], [(i / max(1, len(cols) - 1), srgb(c)) for i, c in enumerate(cols)])
    r.color_ramp.interpolation = 'CONSTANT'
    v = pos_vec(nt, 'object')
    n = noise(nt, v, 30, 5, 0.6)
    c = mix_rgb(nt, math_node(nt, 'MULTIPLY', n.outputs['Fac'], 0.2), r.outputs['Color'], (0, 0, 0, 1))
    p = principled(nt, c, rough, **{'Coat Weight': coat})
    finish(nt, out, p)
    return m

def m_canvas_art(name, palette, seed=1.0, style='strokes'):
    """Procedural abstract painting (generated coords on a canvas box)."""
    m, nt, out = new_mat(name)
    tc = N(nt, 'ShaderNodeTexCoord')
    v = add_vec(nt, tc.outputs['Generated'], (seed * 3.1, seed * 1.7, seed * 0.9))
    if style == 'strokes':
        f = noise(nt, v, 2.2, 6, 0.55, dist=2.5).outputs['Fac']
    else:
        wv = N(nt, 'ShaderNodeTexWave', wave_type='RINGS', rings_direction='SPHERICAL')
        L(nt, v, wv.inputs['Vector'])
        wv.inputs['Scale'].default_value = 1.6
        wv.inputs['Distortion'].default_value = 6
        wv.inputs['Detail'].default_value = 4
        f = wv.outputs['Fac']
    r = ramp(nt, f, [(i / (len(palette) - 1), srgb(c)) for i, c in enumerate(palette)])
    fine = noise(nt, v, 120, 6, 0.7)
    p = principled(nt, r.outputs['Color'], 0.55)
    L(nt, bump(nt, fine.outputs['Fac'], 0.25, 0.002), p.inputs['Normal'])
    finish(nt, out, p)
    return m

def m_image_emit(name, path, strength=1.0):
    m, nt, out = new_mat(name)
    img = bpy.data.images.load(path, check_existing=True)
    t = N(nt, 'ShaderNodeTexImage')
    t.image = img
    e = N(nt, 'ShaderNodeEmission')
    e.inputs['Strength'].default_value = strength
    L(nt, t.outputs['Color'], e.inputs['Color'])
    gl = N(nt, 'ShaderNodeBsdfGlossy')
    gl.inputs['Roughness'].default_value = 0.05
    lw = N(nt, 'ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.1
    mx = N(nt, 'ShaderNodeMixShader')
    L(nt, lw.outputs['Fresnel'], mx.inputs[0]); L(nt, e.outputs[0], mx.inputs[1]); L(nt, gl.outputs[0], mx.inputs[2])
    finish(nt, out, mx)
    return m

def build_materials():
    MATS.clear()
    MATS['plaster'] = m_plaster('Plaster_White')
    MATS['plaster_warm'] = m_plaster('Plaster_Warm', '#e3d9ca')
    MATS['oak_floor'] = m_wood_planks('Oak_Floor', '#c49a6c', '#8a5f3a', 0.22, 2.6, 'X', 0.32)
    MATS['oak_ceiling'] = m_wood_planks('Oak_Ceiling', '#c99c6b', '#93653d', 0.10, 3.4, 'Y', 0.55, seam=0.006)
    MATS['oak'] = m_wood_planks('Oak_Solid', '#c8a175', '#8f6641', 0.3, 3.0, 'X', 0.36, coord='object', plank=False)
    MATS['walnut'] = m_wood_planks('Walnut', '#6b4a33', '#33221a', 0.3, 3.0, 'X', 0.34, coord='object', plank=False)
    MATS['walnut_panel'] = m_wood_planks('Walnut_Panel', '#664530', '#2f2017', 0.42, 2.8, 'Z', 0.4, seam=0.003)
    MATS['charred'] = m_wood_planks('Timber_Dark', '#3a322c', '#171311', 0.14, 6.0, 'Z', 0.62, seam=0.006)
    MATS['cedar_soffit'] = m_wood_planks('Cedar_Soffit', '#b98257', '#7a4b2b', 0.12, 4.0, 'X', 0.5, seam=0.005)
    MATS['beam_dark'] = m_wood_planks('Beam_Dark', '#3b2a1f', '#1d140e', 0.3, 5.0, 'X', 0.5, coord='object', plank=False)
    MATS['stone_ext'] = m_stone_ledger('Stone_Ledger_Ext', ['#bdb8ae', '#a39d92', '#cdc8be', '#959087', '#b3ada2', '#8a857c', '#c6c0b5'])
    MATS['stone_int'] = m_stone_ledger('Stone_Ledger_Int', ['#d3cdc2', '#c0b9ac', '#dcd7cd', '#b3ab9c', '#c9c2b5'], su=0.8, sv=7.5, mortar='#9b958b', depth=0.45)
    MATS['limestone_floor'] = m_stone_slab('Limestone_Floor', '#d8d0c2', '#c7bba8', 0.36, (1.2, 0.6))
    MATS['paver'] = m_stone_slab('Terrace_Paver', '#bdb4a6', '#a39888', 0.7, (1.0, 0.5), 0.006)
    MATS['coping'] = m_stone_slab('Pool_Coping', '#d4ccbf', '#c0b6a6', 0.6, (1.0, 0.5), 0.004)
    MATS['marble'] = m_marble('Marble_Calacatta')
    MATS['marble_dark'] = m_marble('Marble_Nero', '#1b1a19', '#d9d2c7', '#a08a66', 0.1)
    MATS['metal_dark'] = m_metal('Metal_Bronze_Dark', '#1d1b19', 0.35)
    MATS['metal_black'] = m_metal('Metal_Black', '#0f0f10', 0.42)
    MATS['brass'] = m_metal('Brass_Brushed', '#c9a46a', 0.28, 0.3)
    MATS['steel'] = m_metal('Steel_Brushed', '#b9bbbd', 0.25, 0.4)
    MATS['zinc'] = m_metal('Roof_Zinc', '#2c2e30', 0.48)
    MATS['glass'] = m_glass_window('Glass_Window')
    MATS['glass_clear'] = m_glass_solid('Glass_Clear')
    MATS['glass_frost'] = m_glass_solid('Glass_Frosted', '#f2f2f0', 0.25)
    MATS['concrete'] = m_plaster('Concrete_Board', '#b4aea5', 0.8, 0.6)
    MATS['lacquer_dark'] = m_simple('Lacquer_Charcoal', srgb('#25272a'), 0.32, **{'Coat Weight': 0.3})
    MATS['lacquer_white'] = m_simple('Lacquer_White', srgb('#eeebe5'), 0.3, **{'Coat Weight': 0.2})
    MATS['fabric_cream'] = m_fabric('Boucle_Cream', '#e4dccd')
    MATS['fabric_sand'] = m_fabric('Linen_Sand', '#c2b29a')
    MATS['fabric_olive'] = m_fabric('Velvet_Olive', '#5f6146', 0.7, 0.9)
    MATS['fabric_char'] = m_fabric('Wool_Charcoal', '#3d3c3a')
    MATS['leather'] = m_leather('Leather_Cognac')
    MATS['rug'] = m_rug('Rug_Wool')
    MATS['rug_dark'] = m_rug('Rug_Dark', '#5b544b', '#3f3a34')
    MATS['books'] = m_random_tint('Books', ['#e8e2d6', '#24364a', '#7a2f25', '#c9b48e', '#2f3a2f', '#d8cfc0', '#9a8a70', '#1e1e1e', '#b9583a', '#e0d8c8'], 0.7)
    MATS['ceramic'] = m_random_tint('Ceramics', ['#e9e4da', '#c7b59a', '#3a3632', '#a7603f'], 0.35, 0.4)
    MATS['soil'] = m_simple('Planter_Soil', srgb('#2b2119'), 0.95)
    MATS['leaf'] = m_simple('Leaf_Green', srgb('#3e5a2e'), 0.45)
    MATS['bark'] = m_simple('Bark', srgb('#4a3b2d'), 0.85)
    MATS['black_plastic'] = m_simple('Black_Matte', srgb('#121212'), 0.55)
    MATS['white_matte'] = m_simple('White_Matte', srgb('#f2f0eb'), 0.6)
    MATS['shade_linen'] = m_simple('Lampshade_Linen', srgb('#f1e7d4'), 0.8, **{'Transmission Weight': 0.35})
    MATS['warm_light'] = m_emit('Emit_Warm', kelvin=3400, strength=12.0)
    MATS['warm_soft'] = m_emit('Emit_Warm_Soft', kelvin=3200, strength=4.0)
    MATS['fire'] = m_emit('Emit_Fire', kelvin=1900, strength=28.0)
    MATS['art1'] = m_canvas_art('Art_Ochre', ['#efe7d8', '#c9a77a', '#8c5a34', '#2d2622', '#e9e0cf'], 1.0)
    MATS['art2'] = m_canvas_art('Art_Ink', ['#f1eee8', '#d9d3c8', '#2a2a2a', '#efebe4', '#9b8f7d'], 2.3)
    MATS['art3'] = m_canvas_art('Art_Ember', ['#2a2622', '#6b5644', '#b59a78', '#e4dccd', '#3a332c'], 4.7, 'strokes')
    return MATS
