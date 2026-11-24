"""Helpers for the real-time builds (bake_rt.py): world matrices, material table, lights,
joining collections into a few objects, and the OIDN denoiser Blender ships with."""
import bpy, bmesh, ctypes, os, random, shutil
import numpy as np
from mathutils import Vector

# ---------------------------------------------------------------- transforms
def world(o):
    """World matrix from location/rotation/scale and the parent chain. Objects placed by
    script are saved with a stale matrix_world, and a background session doesn't refresh it."""
    m = o.matrix_basis.copy()
    while o.parent:
        m = o.parent.matrix_basis @ o.matrix_parent_inverse @ m
        o = o.parent
    return m

def fix_world(s):
    W = {o.name: world(o) for o in s.objects}
    for o in s.objects:
        o.matrix_world = W[o.name]
    bpy.context.view_layer.update()

def coll_of(o):
    return o.users_collection[0].name if o.users_collection else ''

# ---------------------------------------------------------------- material table
def rgb(v):
    return [round(float(c), 4) for c in tuple(v)[:3]]

def avg(cols):
    cols = [c for c in cols if c]
    if not cols:
        return None
    return [round(sum(c[i] for c in cols) / len(cols), 4) for i in range(3)]

def rep_color(sock, depth=0):
    if depth > 10:
        return None
    if not sock.is_linked:
        v = sock.default_value
        try:
            return rgb(v)
        except TypeError:
            return [round(float(v), 4)] * 3
    n = sock.links[0].from_node
    if n.type == 'RGB':
        return rgb(n.outputs[0].default_value)
    if n.type == 'VALTORGB':
        return avg([rgb(e.color) for e in n.color_ramp.elements])
    ins = [i for i in n.inputs if i.type == 'RGBA' and getattr(i, 'enabled', True)]
    return avg([rep_color(i, depth + 1) for i in ins]) if ins else None

def rep_value(sock, fallback):
    if not sock.is_linked:
        return round(float(sock.default_value), 4)
    n = sock.links[0].from_node
    if n.type == 'VALUE':
        return round(float(n.outputs[0].default_value), 4)
    if n.type == 'MAP_RANGE':
        try:
            return round((n.inputs['To Min'].default_value + n.inputs['To Max'].default_value) / 2, 4)
        except KeyError:
            return fallback
    return fallback

def describe(mat, outdir):
    d = dict(color=[0.6, 0.6, 0.6], rough=0.6, metal=0.0, emit=None, glass=False, image=None)
    if not mat or not mat.node_tree:
        return d
    nodes = mat.node_tree.nodes
    pr = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if pr:
        c = rep_color(pr.inputs['Base Color'])
        if c:
            d['color'] = c
        d['rough'] = rep_value(pr.inputs['Roughness'], 0.5)
        d['metal'] = rep_value(pr.inputs['Metallic'], 0.0)
        es, ec = pr.inputs.get('Emission Strength'), pr.inputs.get('Emission Color')
        if es is not None and ec is not None:
            st, col = rep_value(es, 0.0), rep_color(ec)
            if st > 0 and col and max(col) > 0:
                d['emit'] = dict(color=col, strength=st)
    em = next((n for n in nodes if n.type == 'EMISSION'), None)
    if em:
        d['emit'] = dict(color=rep_color(em.inputs['Color']) or [1, 1, 1], strength=rep_value(em.inputs['Strength'], 1.0))
    for n in nodes:
        if n.type == 'TEX_IMAGE' and n.image and n.image.filepath and n.name != 'RT_BAKE':
            src = bpy.path.abspath(n.image.filepath)
            if os.path.isfile(src):
                shutil.copyfile(src, os.path.join(outdir, os.path.basename(src)))
                d['image'] = os.path.basename(src)
    kinds = {n.type for n in nodes}
    tw = pr.inputs.get('Transmission Weight') if pr else None
    if 'BSDF_GLASS' in kinds or 'BSDF_TRANSPARENT' in kinds or (tw is not None and rep_value(tw, 0) > 0.5) or 'glass' in mat.name.lower():
        d['glass'] = True
    return d

def collect_lights(s):
    out = []
    for o in s.objects:
        if o.type != 'LIGHT':
            continue
        L, m = o.data, o.matrix_world
        out.append(dict(name=o.name, type=L.type, pos=[round(v, 3) for v in m.translation],
                        dir=[round(v, 4) for v in (m.to_3x3() @ Vector((0, 0, -1))).normalized()],
                        color=rgb(L.color), energy=round(L.energy, 3), coll=coll_of(o)))
    return out

# ---------------------------------------------------------------- per-object randomness
def random_to_attribute(materials):
    """Object Info > Random doesn't survive joining objects: route it through an attribute
    ('rt_rand') that each source object will carry."""
    touched = set()
    for m in materials:
        if not m or not m.node_tree:
            continue
        nt = m.node_tree
        for n in list(nt.nodes):
            if n.type != 'OBJECT_INFO':
                continue
            links = [l for l in nt.links if l.from_node == n and l.from_socket.name == 'Random']
            if not links:
                continue
            at = nt.nodes.new('ShaderNodeAttribute')
            at.attribute_type = 'GEOMETRY'
            at.attribute_name = 'rt_rand'
            for l in links:
                nt.links.new(at.outputs['Fac'], l.to_socket)
            touched.add(m.name)
    return touched

# ---------------------------------------------------------------- joining
def temp_copy(o, dg, coll, rel=None, rand_mats=(), replace=None):
    """World-space (or rel-space) copy of an evaluated object as a plain mesh object."""
    me = replace(o) if replace else None
    if me is None:
        ev = o.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
        m = world(o) if rel is None else world(rel).inverted() @ world(o)
        me.transform(m)
        if m.determinant() < 0:
            me.flip_normals()
    me.materials.clear()
    for sl in o.material_slots:
        me.materials.append(sl.material)
    if any(sl.material and sl.material.name in rand_mats for sl in o.material_slots) and len(me.vertices):
        a = me.attributes.new('rt_rand', 'FLOAT', 'POINT')
        a.data.foreach_set('value', np.full(len(me.vertices), random.random(), dtype=np.float32))
    t = bpy.data.objects.new(o.name + '_rt', me)
    coll.objects.link(t)
    return t

def join(objs, name):
    objs = [o for o in objs if len(o.data.polygons)]
    if not objs:
        return None
    target = objs[0]
    if len(objs) > 1:
        with bpy.context.temp_override(active_object=target, object=target, selected_objects=objs,
                                       selected_editable_objects=objs):
            bpy.ops.object.join()
    target.name = name
    target.data.name = name
    return target

def split_faces(ob, keep, name):
    """Copy of ob holding only the faces whose material passes keep(material)."""
    me = ob.data.copy()
    me.name = name
    bm = bmesh.new()
    bm.from_mesh(me)
    mats = me.materials
    drop = [f for f in bm.faces if not keep(mats[f.material_index] if f.material_index < len(mats) else None)]
    bmesh.ops.delete(bm, geom=drop, context='FACES')
    bm.to_mesh(me)
    bm.free()
    if not len(me.polygons):
        bpy.data.meshes.remove(me)
        return None
    o = bpy.data.objects.new(name, me)
    o.matrix_world = ob.matrix_world.copy()
    for c in ob.users_collection:
        c.objects.link(o)
    return o

def mesh_area(ob):
    return sum(p.area for p in ob.data.polygons)

# ---------------------------------------------------------------- denoise (OIDN, as shipped with Blender)
_oidn = None

def oidn():
    global _oidn
    if _oidn is None:
        d = os.path.join(os.path.dirname(bpy.app.binary_path), 'blender.shared')
        os.add_dll_directory(d)
        lib = ctypes.CDLL(os.path.join(d, 'OpenImageDenoise.dll'))
        vp, cp, sz = ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t
        lib.oidnNewDevice.restype = vp
        lib.oidnNewDevice.argtypes = [ctypes.c_int]
        lib.oidnCommitDevice.argtypes = [vp]
        lib.oidnNewFilter.restype = vp
        lib.oidnNewFilter.argtypes = [vp, cp]
        lib.oidnSetSharedFilterImage.argtypes = [vp, cp, vp, ctypes.c_int, sz, sz, sz, sz, sz]
        lib.oidnSetFilterBool.argtypes = [vp, cp, ctypes.c_bool]
        lib.oidnCommitFilter.argtypes = [vp]
        lib.oidnExecuteFilter.argtypes = [vp]
        lib.oidnGetDeviceError.restype = ctypes.c_int
        lib.oidnGetDeviceError.argtypes = [vp, ctypes.POINTER(ctypes.c_char_p)]
        lib.oidnReleaseFilter.argtypes = [vp]
        lib.oidnReleaseDevice.argtypes = [vp]
        _oidn = lib
    return _oidn

def denoise(color, normal=None, albedo=None):
    """color/normal/albedo: float32 (h, w, 3). Returns the denoised color (HDR)."""
    lib = oidn()
    h, w, _ = color.shape
    color = np.ascontiguousarray(color, dtype=np.float32)
    out = np.zeros_like(color)
    dev = lib.oidnNewDevice(0)
    lib.oidnCommitDevice(dev)
    f = lib.oidnNewFilter(dev, b'RT')
    keep = [color, out]

    def put(name, arr):
        arr = np.ascontiguousarray(arr, dtype=np.float32)
        keep.append(arr)
        lib.oidnSetSharedFilterImage(f, name, arr.ctypes.data, 3, w, h, 0, 12, 12 * w)

    put(b'color', color)
    if albedo is not None:
        put(b'albedo', albedo)
        if normal is not None:
            put(b'normal', normal)
    lib.oidnSetSharedFilterImage(f, b'output', out.ctypes.data, 3, w, h, 0, 12, 12 * w)
    lib.oidnSetFilterBool(f, b'hdr', True)
    lib.oidnCommitFilter(f)
    lib.oidnExecuteFilter(f)
    msg = ctypes.c_char_p()
    err = lib.oidnGetDeviceError(dev, ctypes.byref(msg))
    lib.oidnReleaseFilter(f)
    lib.oidnReleaseDevice(dev)
    if err:
        raise RuntimeError(f'OIDN error {err}: {msg.value}')
    return out
