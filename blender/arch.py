"""HALCYON residence — architectural shell.

Plan (metres, +Y = north towards the mountains, lake to the south):
  A  Great-room pavilion   x[-15,-3]  y[0,14]   glazed gable to the lake, eave 6.2, ridge 10.4
  B  Arrival / stair core  x[-3, 3]   y[2,14]   limestone, flat roof 7.4, pivot door at y=2
  C  East wing (2 storey)  x[ 3,19]   y[0,13]   kitchen + dining + study, timber-clad upper floor
                                                cantilevered 2.2 m towards the lake
"""
import bpy, math
from hlib import *

# ---------------------------------------------------------------- primitives
def prism(name, poly, a0, a1, axis, mat, c, bev=0.006):
    """Extrude a 2D polygon. axis='Y': poly in (x,z) extruded y a0..a1; axis='X': poly in (y,z) extruded x."""
    n = len(poly)
    verts = []
    for a in (a0, a1):
        for (u, z) in poly:
            verts.append((u, a, z) if axis == 'Y' else (a, u, z))
    faces = [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    ob = mesh_obj(name, verts, faces, c, mat)
    # fix orientation
    me = ob.data
    import bmesh as _bm
    bm = _bm.new(); bm.from_mesh(me)
    _bm.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    bevel(ob, bev, 2)
    return ob

def wall(name, axis, fixed, t, a0, a1, z0, z1, mat, c, openings=(), bev=0.006):
    """Axis-aligned wall with rectangular openings.
    axis 'X': runs along x (a0..a1), occupies y in [fixed, fixed+t] (t may be negative).
    axis 'Y': runs along y, occupies x in [fixed, fixed+t].
    openings: (o0, o1, oz0, oz1) along the run."""
    f0, f1 = sorted((fixed, fixed + t))
    ops = sorted(openings)
    pieces = []
    cur = a0
    for (o0, o1, oz0, oz1) in ops:
        if o0 > cur:
            pieces.append((cur, o0, z0, z1))
        if oz0 > z0:
            pieces.append((o0, o1, z0, oz0))
        if oz1 < z1:
            pieces.append((o0, o1, oz1, z1))
        cur = o1
    if cur < a1:
        pieces.append((cur, a1, z0, z1))
    obs = []
    for i, (p0, p1, pz0, pz1) in enumerate(pieces):
        if axis == 'X':
            obs.append(box(f"{name}_{i}", p0, p1, f0, f1, pz0, pz1, mat, c, bev))
        else:
            obs.append(box(f"{name}_{i}", f0, f1, p0, p1, pz0, pz1, mat, c, bev))
    return obs

def glazing(name, axis, fixed, a0, a1, z0, z1, c, mull=1.5, mw=0.055, md=0.11, transoms=(), frame=0.07, glass=True, fmat=None):
    """Framed glazing panel. axis 'X': glass plane y=fixed spanning x; 'Y': plane x=fixed spanning y."""
    fmat = fmat or M('metal_dark')
    obs = []
    def bx(nm, u0, u1, zz0, zz1, d):
        if axis == 'X':
            return box(nm, u0, u1, fixed - d / 2, fixed + d / 2, zz0, zz1, fmat, c, 0.004)
        return box(nm, fixed - d / 2, fixed + d / 2, u0, u1, zz0, zz1, fmat, c, 0.004)
    obs.append(bx(f"{name}_fb", a0, a1, z0, z0 + frame, md))
    obs.append(bx(f"{name}_ft", a0, a1, z1 - frame, z1, md))
    obs.append(bx(f"{name}_fl", a0, a0 + frame, z0, z1, md))
    obs.append(bx(f"{name}_fr", a1 - frame, a1, z0, z1, md))
    n = max(1, round((a1 - a0) / mull))
    for i in range(1, n):
        u = a0 + (a1 - a0) * i / n
        obs.append(bx(f"{name}_m{i}", u - mw / 2, u + mw / 2, z0, z1, md))
    for j, tz in enumerate(transoms):
        obs.append(bx(f"{name}_t{j}", a0, a1, tz - mw / 2, tz + mw / 2, md))
    if glass:
        if axis == 'X':
            g = vplane(f"{name}_glass", (a0, fixed), (a1, fixed), z0, z1, M('glass'), c)
        else:
            g = vplane(f"{name}_glass", (fixed, a0), (fixed, a1), z0, z1, M('glass'), c)
        obs.append(g)
    return obs

# ---------------------------------------------------------------- volume A
EAVE, RIDGE = 6.2, 10.4
AX0, AX1, AY0, AY1 = -15.0, -3.0, 0.0, 14.0
ACX = (AX0 + AX1) / 2

def roof_z(x):
    """Underside of the pavilion roof at x (inside the walls)."""
    return EAVE + (RIDGE - EAVE) * (1 - abs(x - ACX) / ((AX1 - AX0) / 2))

def build_pavilion(c):
    T_OUT, T_IN = 0.16, 0.2
    # floor slab
    box('A_slab', AX0, AX1, AY0, AY1, -0.45, -0.03, M('concrete'), c, 0)
    box('A_floor', AX0 + 0.3, AX1, AY0 + 0.25, AY1 - 0.3, -0.03, 0.0, M('oak_floor'), c, 0)
    # west wall (stone out / stone-ledger feature in)
    wall('A_wallW_out', 'Y', AX0, T_OUT, AY0, AY1, -0.4, EAVE + 0.15, M('stone_ext'), c)
    wall('A_wallW_in', 'Y', AX0 + T_OUT, T_IN, AY0 + 0.3, AY1, 0, EAVE, M('stone_int'), c)
    # east wall (shared with core) with grand opening to the arrival hall
    wall('A_wallE', 'Y', AX1 - 0.3, 0.3, AY0 + 0.3, AY1, 0, EAVE, M('plaster'), c,
         openings=[(4.2, 9.6, 0, 3.6)])
    # north gable — solid stone with plaster lining
    pent = [(AX0, -0.4), (AX1, -0.4), (AX1, EAVE + 0.15), (ACX, RIDGE + 0.15), (AX0, EAVE + 0.15)]
    prism('A_gableN_out', pent, AY1 - T_OUT, AY1, 'Y', M('stone_ext'), c)
    pent_in = [(AX0 + 0.3, 0), (AX1 - 0.3, 0), (AX1 - 0.3, roof_z(AX1 - 0.3)), (ACX, RIDGE), (AX0 + 0.3, roof_z(AX0 + 0.3))]
    prism('A_gableN_in', pent_in, AY1 - 0.36, AY1 - T_OUT, 'Y', M('plaster'), c)
    # south glazed gable: heavy dark frame + mullion grid
    fw = 0.32
    fy0, fy1 = AY0 - 0.12, AY0 + 0.34
    outer = [(AX0, -0.4), (AX1, -0.4), (AX1, EAVE + 0.15), (ACX, RIDGE + 0.15), (AX0, EAVE + 0.15)]
    # frame as 5 bars
    box('A_frameL', AX0, AX0 + fw, fy0, fy1, -0.4, EAVE + 0.15, M('metal_dark'), c, 0.01)
    box('A_frameR', AX1 - fw, AX1, fy0, fy1, -0.4, EAVE + 0.15, M('metal_dark'), c, 0.01)
    box('A_frameB', AX0, AX1, fy0, fy1, -0.4, 0.03, M('metal_dark'), c, 0.01)
    slope = (RIDGE - EAVE) / ((AX1 - AX0) / 2)
    ang = math.atan(slope)
    for side, (xa, xb) in (('L', (AX0, ACX)), ('R', (ACX, AX1))):
        za = EAVE + 0.15 if side == 'L' else RIDGE + 0.15
        zb = RIDGE + 0.15 if side == 'L' else EAVE + 0.15
        prism(f'A_frameT{side}', [(xa, za), (xb, zb), (xb, zb - fw / math.cos(ang)), (xa, za - fw / math.cos(ang))],
              fy0, fy1, 'Y', M('metal_dark'), c, 0.01)
    gy = AY0 + 0.12
    gx0, gx1 = AX0 + fw, AX1 - fw
    # glass pentagon
    def topz(x):
        return roof_z(x) + 0.15 - fw / math.cos(ang)
    gpoly = [(gx0, 0.0), (gx1, 0.0), (gx1, topz(gx1)), (ACX, topz(ACX)), (gx0, topz(gx0))]
    mesh_obj('A_gableS_glass', [(x, gy, z) for x, z in gpoly], [tuple(range(5))], c, M('glass'))
    nm = 6
    for i in range(1, nm):
        x = gx0 + (gx1 - gx0) * i / nm
        box(f'A_mull{i}', x - 0.045, x + 0.045, gy - 0.09, gy + 0.09, 0, topz(x), M('metal_dark'), c, 0.004)
    for tz, nmx in ((3.15, 'a'), (EAVE + 0.05, 'b')):
        box(f'A_transom{nmx}', gx0, gx1, gy - 0.09, gy + 0.09, tz - 0.045, tz + 0.045, M('metal_dark'), c, 0.004)
    # sliding door leaf line at the bottom centre (subtle extra mullion depth)
    # roof: two sloped slabs, standing-seam zinc, cedar soffit
    oh_s, oh_n, oh_side = 1.3, 0.6, 0.7
    th = 0.38
    for side in ('L', 'R'):
        xe = AX0 - oh_side if side == 'L' else AX1
        ze_top = RIDGE + 0.15 + th - slope * abs(xe - ACX)
        poly = [(ACX, RIDGE + 0.15 + th), (xe, ze_top), (xe, ze_top - th), (ACX, RIDGE + 0.15)]
        if side == 'R':
            poly = poly[::-1]
        prism(f'A_roof{side}', poly, AY0 - oh_s, AY1 + oh_n, 'Y', M('zinc'), c, 0.01)
        # standing seams
        nseam = 34
        for k in range(nseam + 1):
            y = AY0 - oh_s + (AY1 + oh_n - AY0 + oh_s) * k / nseam
            sx0, sx1 = (xe, ACX) if side == 'L' else (ACX, xe)
            za = RIDGE + 0.15 + th - slope * abs(sx0 - ACX)
            zb = RIDGE + 0.15 + th - slope * abs(sx1 - ACX)
            prism(f'A_seam{side}{k}', [(sx0, za), (sx1, zb), (sx1, zb + 0.035), (sx0, za + 0.035)],
                  y - 0.012, y + 0.012, 'Y', M('zinc'), c, 0)
    box('A_ridgecap', ACX - 0.18, ACX + 0.18, AY0 - oh_s, AY1 + oh_n, RIDGE + 0.15 + th - 0.05, RIDGE + 0.15 + th + 0.06, M('zinc'), c, 0.01)
    # interior oak ceiling following the pitch
    for side in ('L', 'R'):
        xa = AX0 + 0.3 if side == 'L' else AX1 - 0.3
        za = roof_z(xa)
        poly = [(ACX, RIDGE), (xa, za), (xa, za - 0.04), (ACX, RIDGE - 0.04)]
        if side == 'R':
            poly = poly[::-1]
        prism(f'A_ceiling{side}', poly, AY0 + 0.3, AY1 - 0.36, 'Y', M('oak_ceiling'), c, 0)
    # trusses: dark collar ties + principal rafters + ridge beam
    for k, y in enumerate((2.6, 6.2, 9.8, 13.0)):
        box(f'A_collar{k}', AX0 + 0.3, AX1 - 0.3, y - 0.14, y + 0.14, EAVE - 0.55, EAVE - 0.2, M('beam_dark'), c, 0.01)
        for side in ('L', 'R'):
            xa = AX0 + 0.3 if side == 'L' else AX1 - 0.3
            za = roof_z(xa) - 0.04
            poly = [(ACX, RIDGE - 0.04), (xa, za), (xa, za - 0.32), (ACX, RIDGE - 0.36)]
            if side == 'R':
                poly = poly[::-1]
            prism(f'A_rafter{k}{side}', poly, y - 0.13, y + 0.13, 'Y', M('beam_dark'), c, 0.01)
        box(f'A_king{k}', ACX - 0.11, ACX + 0.11, y - 0.11, y + 0.11, EAVE - 0.4, RIDGE - 0.3, M('beam_dark'), c, 0.01)
    box('A_ridgebeam', ACX - 0.16, ACX + 0.16, AY0 + 0.3, AY1 - 0.36, RIDGE - 0.5, RIDGE - 0.04, M('beam_dark'), c, 0.01)
    # chimney (exterior, west) rising through the eave
    box('A_chimney', AX0 - 1.5, AX0, 5.2, 8.8, -0.4, RIDGE + 1.4, M('stone_ext'), c, 0.01)
    box('A_chimcap', AX0 - 1.62, AX0 + 0.12, 5.08, 8.92, RIDGE + 1.4, RIDGE + 1.55, M('metal_dark'), c, 0.01)

# ---------------------------------------------------------------- volume B (arrival core)
BX0, BX1, BY0, BY1, BH = -3.0, 3.0, 2.0, 14.0, 7.4
UPPER = 3.7  # upper floor level
# upper floor (first floor) of the east wing:
#   gallery     along the north wall, y[GAL_Y + 0.2, 13.18], entered from the landing
#   three rooms to the south, each looking at the lake through the ribbon window, each its own size:
#     west suite    x[2.82, 8.3]   walnut dressing block x[2.82, 6.5] y[4.6, 10.3], passage beside it
#     bunk room     x[8.5, 12.5]   long and narrow, lowered oak-board ceiling; shower room in the north-west
#     principal     x[12.7, 20.28] raised coffer over the bed, freestanding travertine bed wall,
#                                  dressing room behind it, bathroom in the north-east corner
#   the partitions stand on the ribbon window's mullions, so every room has whole panes
LANDING_DOOR = (10.8, 12.6, 2.5)        # y0, y1, height: the landing's doorway into the gallery
GAL_Y = 10.3                            # south face of the gallery wall (it is 0.2 thick)
GAL_DOORS = ((6.75, 7.85, 2.3),         # x0, x1, height: west suite (pocket door)
             (11.1, 12.1, 2.3),         # bunk room (pocket door)
             (14.6, 16.2, 2.4))         # principal suite (a pair of doors, standing open)
GAL_DOOR = GAL_DOORS[0]
GAL_WINDOWS = ((5.0, 7.2), (10.6, 12.8), (16.2, 18.4))  # north windows, x ranges
PARTITIONS = (8.4, 12.6)                # centre lines (0.2 thick), on the ribbon's mullions
SUITE_BLOCK = (2.82, 6.5, 4.6)          # west suite dressing block: x0, x1, y0 (it runs to GAL_Y)
BUNK_BATH = (8.5, 10.8, 6.6, (8.75, 9.6))       # x0, x1, y0 (to GAL_Y), door y range on its east wall
PRINCIPAL_BATH = (17.8, 20.28, 7.2, (8.5, 9.4))  # x0, x1, y0 (to GAL_Y), door y range on its west wall
COFFER = (13.9, 19.2, -0.9, 4.2, 0.35)  # x0, x1, y0, y1, depth: raised ceiling over the principal bed

def build_core(c):
    box('B_slab', BX0, BX1, BY0, BY1, -0.45, -0.03, M('concrete'), c, 0)
    box('B_floor', BX0, BX1 - 0.3, BY0 + 0.3, BY1 - 0.3, -0.03, 0.0, M('limestone_floor'), c, 0)
    # front facade (y=2) — limestone with tall portal: pivot door + glass slot above
    door_w0, door_w1 = -0.8, 0.8
    wall('B_front_out', 'X', BY0, 0.16, BX0, BX1, -0.4, BH, M('stone_ext'), c,
         openings=[(door_w0 - 0.25, door_w1 + 0.25, 0, 6.6)])
    wall('B_front_in', 'X', BY0 + 0.16, 0.18, BX0, BX1 - 0.3, 0, 7.0, M('plaster'), c,
         openings=[(door_w0 - 0.25, door_w1 + 0.25, 0, 6.6)])
    # bronze portal lining
    pd0, pd1 = BY0 - 0.35, BY0 + 0.34
    box('B_portalL', door_w0 - 0.25, door_w0 - 0.05, pd0, pd1, 0, 6.6, M('metal_dark'), c, 0.006)
    box('B_portalR', door_w1 + 0.05, door_w1 + 0.25, pd0, pd1, 0, 6.6, M('metal_dark'), c, 0.006)
    box('B_portalT', door_w0 - 0.25, door_w1 + 0.25, pd0, pd1, 6.4, 6.6, M('metal_dark'), c, 0.006)
    box('B_portalMid', door_w0 - 0.05, door_w1 + 0.05, BY0 + 0.05, BY0 + 0.2, 3.5, 3.62, M('metal_dark'), c, 0.004)
    g = vplane('B_transom_glass', (door_w0 - 0.05, BY0 + 0.12), (door_w1 + 0.05, BY0 + 0.12), 3.62, 6.4, M('glass'), c)
    # side walls
    box('C_wallW_front', BX1, BX1 + 0.3, AY0 + 0.1, BY0 + 0.16, -0.4, 3.32, M('stone_ext'), c, 0.01)
    # ground: the open bay to the kitchen; upper: thinner (the wing's rooms start at x 2.82),
    # with the landing's doorway into the bedroom gallery
    wall('B_wallE', 'Y', BX1 - 0.3, 0.3, BY0 + 0.16, BY1, 0, UPPER, M('plaster'), c,
         openings=[(3.4, 5.2, 0, 3.0)])
    wall('B_wallE_up', 'Y', BX1 - 0.3, 0.12, BY0 + 0.16, BY1, UPPER, 7.0, M('plaster'), c,
         openings=[(LANDING_DOOR[0], LANDING_DOOR[1], UPPER, UPPER + LANDING_DOOR[2])])
    wall('B_wallW_out', 'Y', BX0, 0.12, BY0, AY1, 6.2, BH, M('stone_ext'), c)
    box('B_wallW_lining', BX0 + 0.12, BX0 + 0.3, BY0 + 0.34, BY1 - 0.3, 6.2, 7.0, M('plaster'), c, 0)
    box('B_wallW_front', BX0, BX0 + 0.16, AY0 + 0.3, BY0, -0.4, EAVE + 0.15, M('stone_ext'), c, 0.01)
    # north wall — walnut feature wall at ground level
    wall('B_wallN', 'X', BY1 - 0.3, 0.3, BX0, BX1, -0.4, BH, M('stone_ext'), c)
    box('B_walnutwall', BX0, BX1 - 0.3, BY1 - 0.36, BY1 - 0.3, 0, UPPER - 0.3, M('walnut_panel'), c, 0.003)
    box('B_northlining', BX0, BX1 - 0.3, BY1 - 0.34, BY1 - 0.3, UPPER - 0.3, 7.0, M('plaster'), c, 0)
    # roof + parapet + slatted oak ceiling
    box('B_roof', BX0 - 0.05, BX1 + 0.05, BY0 - 0.05, BY1 + 0.05, 7.0, BH + 0.05, M('concrete'), c, 0.01)
    box('B_coping', BX0 - 0.1, BX1 + 0.1, BY0 - 0.1, BY0 + 0.25, BH + 0.05, BH + 0.15, M('metal_dark'), c, 0.004)
    nsl = 46
    for i in range(nsl):
        x = BX0 + 0.35 + (BX1 - BX0 - 0.7) * (i + 0.5) / nsl
        box(f'B_slat{i}', x - 0.028, x + 0.028, BY0 + 0.34, BY1 - 0.3, 6.82, 6.98, M('oak'), c, 0.004)
    box('B_ceilback', BX0, BX1, BY0, BY1, 6.98, 7.0, M('black_plastic'), c, 0)
    # upper landing / gallery
    land_y = 10.15
    box('B_landing', BX0, BX1 - 0.3, land_y, BY1 - 0.3, UPPER - 0.32, UPPER, M('plaster'), c, 0.01)
    box('B_landing_floor', BX0, BX1 - 0.3, land_y, BY1 - 0.3, UPPER, UPPER + 0.02, M('oak_floor'), c, 0)
    box('B_landing_edge', BX0, BX1 - 0.3, land_y - 0.01, land_y + 0.02, UPPER - 0.32, UPPER + 0.02, M('oak'), c, 0.003)
    gl = vplane('B_landing_glass', (BX0 + 0.3, land_y + 0.06), (1.45, land_y + 0.06), UPPER + 0.02, UPPER + 1.08, M('glass_clear'), c)
    box('B_landing_rail', BX0 + 0.3, 1.45, land_y + 0.03, land_y + 0.09, UPPER + 1.06, UPPER + 1.1, M('brass'), c, 0.004)
    # floating oak stair cantilevered from the east wall
    n = 16
    run, rise = 0.29, UPPER / (n + 1)
    sx0, sx1 = 1.5, BX1 - 0.3
    y0 = land_y - n * run
    for i in range(n):
        z = rise * (i + 1)
        box(f'B_tread{i}', sx0, sx1, y0 + i * run, y0 + (i + 1) * run - 0.012, z - 0.085, z, M('oak'), c, 0.006)
    # stair glass balustrade (parallelogram) + brass handrail
    za, zb = rise, UPPER
    ya, yb = y0, land_y
    hh = 1.0
    mesh_obj('B_stair_glass', [(sx0 - 0.03, ya, za), (sx0 - 0.03, yb, zb), (sx0 - 0.03, yb, zb + hh), (sx0 - 0.03, ya, za + hh)],
             [(0, 1, 2, 3)], c, M('glass_clear'))
    slen = math.hypot(yb - ya, zb - za)
    r = cyl('B_handrail', 0.022, slen, (sx0 - 0.03, (ya + yb) / 2, (za + zb) / 2 + hh + 0.02), M('brass'), c, 16,
            rot=(-(math.pi / 2 - math.atan2(zb - za, yb - ya)), 0, 0))
    # stringer shadow-gap on the wall (dark recessed line)
    # upper-floor walls of the core (simple)
    box('B_upper_back', BX0, BX1 - 0.3, BY1 - 0.35, BY1 - 0.33, UPPER, 7.0, M('plaster'), c, 0)

# ---------------------------------------------------------------- volume C (east wing)
CX0, CX1, CY0, CY1 = 3.0, 19.0, 0.0, 13.0
GH = 3.3          # ground floor ceiling
UF0, UF1 = 3.7, 6.6   # upper floor finished level / ceiling
CANT = -2.2

def build_wing(c):
    box('C_slab', CX0, CX1, CY0, CY1, -0.45, -0.03, M('concrete'), c, 0)
    box('C_floor', CX0, CX1 - 0.3, CY0 + 0.1, CY1 - 0.3, -0.03, 0.0, M('oak_floor'), c, 0)
    # ground-floor south: full-height sliding glass (kitchen/dining) + stone pier + study window
    glazing('C_slideS', 'X', CY0 + 0.1, CX0 + 0.05, 13.8, 0.0, GH, c, mull=2.6, mw=0.05, md=0.1)
    box('C_pierS', 13.8, 14.5, CY0 - 0.05, CY0 + 0.35, -0.4, GH, M('stone_ext'), c, 0.01)
    wall('C_studyS_out', 'X', CY0 - 0.05, 0.16, 14.5, CX1, -0.4, GH, M('stone_ext'), c, openings=[(15.4, 18.2, 0.7, 2.9)])
    wall('C_studyS_in', 'X', CY0 + 0.11, 0.2, 14.5, CX1 - 0.3, 0, GH, M('plaster'), c, openings=[(15.4, 18.2, 0.7, 2.9)])
    glazing('C_studyS_win', 'X', CY0 + 0.1, 15.4, 18.2, 0.7, 2.9, c, mull=1.4)
    # east wall stone
    wall('C_wallE_out', 'Y', CX1 - 0.16, 0.16, CY0 - 0.05, CY1, -0.4, GH + 0.4, M('stone_ext'), c)
    wall('C_wallE_in', 'Y', CX1 - 0.36, 0.2, CY0 + 0.3, CY1 - 0.3, 0, GH, M('plaster'), c)
    # north wall: stone out, plaster in; study window looking at the mountains, kitchen clerestory
    north_ops = [(15.2, 18.4, 0.75, 3.0), (7.0, 10.0, 2.25, 3.0)]
    wall('C_wallN_out', 'X', CY1 - 0.16, 0.16, CX0, CX1, -0.4, GH + 0.4, M('stone_ext'), c, openings=north_ops)
    wall('C_wallN_in', 'X', CY1 - 0.36, 0.2, CX0 + 0.3, CX1 - 0.36, 0, GH, M('plaster'), c, openings=north_ops)
    glazing('C_studyN_win', 'X', CY1 - 0.24, 15.2, 18.4, 0.75, 3.0, c, mull=1.6)
    glazing('C_clere', 'X', CY1 - 0.24, 7.0, 10.0, 2.25, 3.0, c, mull=1.0)
    # ground ceiling + floor slab of upper level
    box('C_ceiling', CX0, CX1 - 0.2, CY0 + 0.1, CY1 - 0.2, GH, GH + 0.02, M('plaster'), c, 0)
    box('C_upperslab', CX0 - 0.4, CX1 + 1.5, CANT, CY1 + 0.4, GH + 0.02, UF0, M('concrete'), c, 0.01)
    # cedar soffit under the cantilever (covered terrace)
    box('C_soffit', CX0 - 0.4, CX1 + 1.5, CANT, CY0 + 0.1, GH - 0.02, GH + 0.02, M('cedar_soffit'), c, 0)
    # kitchen/study steel-and-glass partition at x = 14
    px = 14.1
    glazing('C_partition', 'Y', px, CY0 + 0.35, CY1 - 0.36, 0, GH, c, mull=0.9, mw=0.035, md=0.05,
            transoms=(2.35,), fmat=M('metal_black'))
    # upper storey volume clad in dark vertical timber with ribbon window
    ux0, ux1, uy0, uy1 = CX0 - 0.4, CX1 + 1.5, CANT, CY1 + 0.4
    rib = (ux0 + 1.6, ux1 - 1.6, UF0 + 0.55, UF1 - 0.25)
    wall('C_upS', 'X', uy0, 0.22, ux0, ux1, UF0, UF1 + 0.45, M('charred'), c, openings=[(rib[0], rib[1], rib[2], rib[3])])
    glazing('C_ribbon', 'X', uy0 + 0.12, rib[0], rib[1], rib[2], rib[3], c, mull=2.2, mw=0.06)
    east_ops = [(1.0, 4.0, UF0 + 0.55, UF1 - 0.25), (10.85, 12.85, UF0 + 0.3, UF1 - 0.25)]
    wall('C_upE', 'Y', ux1 - 0.22, 0.22, uy0, uy1, UF0, UF1 + 0.45, M('charred'), c, openings=east_ops)
    glazing('C_upE_win', 'Y', ux1 - 0.1, 1.0, 4.0, UF0 + 0.55, UF1 - 0.25, c, mull=1.0)
    glazing('C_upE_gal', 'Y', ux1 - 0.1, 10.85, 12.85, UF0 + 0.3, UF1 - 0.25, c, mull=1.0)
    west_ops = [(LANDING_DOOR[0], LANDING_DOOR[1], UF0, UF0 + LANDING_DOOR[2])]
    wall('C_upW', 'Y', ux0, 0.22, uy0, uy1, UF0, UF1 + 0.45, M('charred'), c, openings=west_ops)
    north_ops = [(x0, x1, UF0 + 0.55, UF1 - 0.25) for x0, x1 in GAL_WINDOWS]
    wall('C_upN', 'X', uy1 - 0.22, 0.22, ux0, ux1, UF0, UF1 + 0.45, M('charred'), c, openings=north_ops)
    for k, (x0, x1) in enumerate(GAL_WINDOWS):
        glazing(f'C_upN_win{k}', 'X', uy1 - 0.1, x0, x1, UF0 + 0.55, UF1 - 0.25, c, mull=2.2)
    box('C_roof', ux0 - 0.05, ux1 + 0.05, uy0 - 0.05, uy1 + 0.05, UF1 + 0.45, UF1 + 0.62, M('metal_dark'), c, 0.01)
    ix0, ix1, iy0, iy1 = ux0 + 0.22, ux1 - 0.22, uy0 + 0.22, uy1 - 0.22
    # ceiling, with the principal suite's coffer raised into the roof build-up
    cx0, cx1, cy0, cy1, cd = COFFER
    for k, (a0, a1, b0, b1) in enumerate(((ix0, cx0, iy0, iy1), (cx1, ix1, iy0, iy1), (cx0, cx1, iy0, cy0), (cx0, cx1, cy1, iy1))):
        box(f'C_roofin{k}', a0, a1, b0, b1, UF1, UF1 + 0.45, M('plaster'), c, 0)
    box('C_roofin_coffer', cx0, cx1, cy0, cy1, UF1 + cd, UF1 + 0.45, M('plaster'), c, 0)
    box('C_upfloor', ix0, ix1, iy0, iy1, UF0, UF0 + 0.02, M('oak_floor'), c, 0)
    # warm plaster lining inside the timber shell
    pw = M('plaster_warm')
    wall('C_upS_in', 'X', iy0, 0.02, ix0, ix1, UF0, UF1, pw, c, openings=[rib], bev=0.002)
    wall('C_upN_in', 'X', iy1, -0.02, ix0, ix1, UF0, UF1, pw, c, openings=north_ops, bev=0.002)
    wall('C_upE_in', 'Y', ix1, -0.02, iy0, iy1, UF0, UF1, pw, c, openings=east_ops, bev=0.002)
    wall('C_upW_in', 'Y', ix0, 0.02, iy0, iy1, UF0, UF1, pw, c, openings=west_ops, bev=0.002)
    # pier over the end of the core's stone front wall, which runs through to x 3.0
    box('C_upPier', ix0, BX1 + 0.02, BY0 - 0.03, BY0 + 0.19, UF0, UF1, pw, c, 0.004)
    # oak threshold in the landing doorway
    box('C_upThreshold', BX1 - 0.3, ix0, LANDING_DOOR[0], LANDING_DOOR[1], UF0, UF0 + 0.02, M('oak_floor'), c, 0)
    # the gallery wall: the three rooms open off it
    wall('C_upGal', 'X', GAL_Y, 0.2, ix0, ix1, UF0, UF1, pw, c,
         openings=[(d0, d1, UF0, UF0 + h) for d0, d1, h in GAL_DOORS], bev=0.003)
    # partitions between the rooms
    for k, x in enumerate(PARTITIONS):
        box(f'C_upPart{k}', x - 0.1, x + 0.1, iy0, GAL_Y, UF0, UF1, pw, c, 0)
    # west suite: walnut dressing block (wardrobes to the passage, the bed wall to the room)
    bx0, bx1, by0 = SUITE_BLOCK
    box('C_up1_block', bx0, bx1, by0, GAL_Y, UF0 + 0.02, UF1, M('walnut_panel'), c, 0.004)
    # bunk room: shower room in the north-west corner, its door facing the entrance lobby
    sx0, sx1, sy0, (dy0, dy1) = BUNK_BATH
    box('C_up2_bathS', sx0, sx1, sy0, sy0 + 0.1, UF0, UF1, pw, c, 0.002)
    wall('C_up2_bathE', 'Y', sx1 - 0.1, 0.1, sy0 + 0.1, GAL_Y, UF0, UF1, pw, c, openings=[(dy0, dy1, UF0, UF0 + 2.1)], bev=0.002)
    # principal suite: bathroom in the north-east corner, its door facing the dressing room
    px0, px1, py0, (dy0, dy1) = PRINCIPAL_BATH
    box('C_up3_bathS', px0, px1, py0, py0 + 0.1, UF0, UF1, pw, c, 0.002)
    wall('C_up3_bathW', 'Y', px0, 0.1, py0 + 0.1, GAL_Y, UF0, UF1, pw, c, openings=[(dy0, dy1, UF0, UF0 + 2.2)], bev=0.002)

# ---------------------------------------------------------------- pivot door (animated in cams.py)
def build_door(c):
    w, h, t = 1.6, 3.48, 0.09
    # origin at the pivot (x = -0.8 + 0.42), door body offset
    me_ob = cbox('Door_Pivot', (w, t, h), (0, 0, 0), M('walnut_panel'), c, bev=0.004)
    # move geometry so the pivot is the origin
    piv_off = -0.8 + 0.42
    for v in me_ob.data.vertices:
        v.co.x += 0.0 - piv_off  # door centre at x=0 relative to world
        v.co.z += h / 2
    me_ob.location = (piv_off, BY0 + 0.16, 0.0)
    # brass pull bar (parented)
    bar = cbox('Door_Pull', (0.05, 0.05, 1.9), (0.62 - piv_off, -0.1, 1.55), M('brass'), c, bev=0.006)
    bar.parent = me_ob
    for k, zz in enumerate((0.75, 2.35)):
        st = cbox(f'Door_PullStand{k}', (0.03, 0.08, 0.03), (0.62 - piv_off, -0.06, zz), M('brass'), c, bev=0.004)
        st.parent = me_ob
    return me_ob

def build():
    c = coll('Architecture')
    build_pavilion(c)
    build_core(c)
    build_wing(c)
    door = build_door(coll('Door', c))
    return door
