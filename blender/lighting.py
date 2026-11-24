"""HALCYON residence — world sky, sun, exterior architectural lighting, Cycles settings."""
import bpy, math
from mathutils import Vector
from hlib import *
import interior as I

# Look: last light — sun just above the western ridge, deep blue zenith,
# warm interiors glowing.  (azimuth: compass bearing of the sun, 0 = +Y north)
LOOK = dict(sun_elev=1.6, sun_azim=246.0, sun_strength=3.2, sky_strength=0.5,
            exposure=0.35, sky_rot_offset=None, occluder_top=95.0)

def sun_vector(elev, azim):
    e, a = math.radians(elev), math.radians(azim)
    return Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))

def build_world(look):
    w = bpy.data.worlds.get('HalcyonSky') or bpy.data.worlds.new('HalcyonSky')
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputWorld')
    sky = nt.nodes.new('ShaderNodeTexSky')
    sky.sky_type = 'MULTIPLE_SCATTERING'
    sky.sun_disc = False
    sky.sun_elevation = math.radians(look['sun_elev'])
    off = look.get('sky_rot_offset') or 0.0
    sky.sun_rotation = math.radians(look['sun_azim']) + off
    sky.altitude = 600.0
    sky.air_density = 1.0
    sky.aerosol_density = 1.6
    sky.ozone_density = 1.2
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Strength'].default_value = look['sky_strength']
    nt.links.new(sky.outputs['Color'], bg.inputs['Color'])
    nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    bpy.context.scene.world = w
    return w

def build_sun(look, c):
    ld = bpy.data.lights.get('Sun') or bpy.data.lights.new('Sun', 'SUN')
    ld.energy = look['sun_strength']
    ld.angle = math.radians(0.8)
    ld.color = I.kelvin_rgb(2500, shift=False)
    ob = bpy.data.objects.get('Sun') or bpy.data.objects.new('Sun', ld)
    if ob.name not in c.objects:
        c.objects.link(ob)
    d = -sun_vector(look['sun_elev'], look['sun_azim'])
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return ob

def build_valley_shadow(look, c):
    """Shadow-only ridge towards the sun: the valley falls into blue shade while
    the high peaks keep the last warm light (alpenglow)."""
    d = sun_vector(look['sun_elev'], look['sun_azim'])
    hd = Vector((d.x, d.y, 0)).normalized()
    ctr = hd * 1300.0
    side = Vector((-hd.y, hd.x, 0))
    top = look.get('occluder_top', 95.0)
    vs = [ctr - side * 6000 + Vector((0, 0, -200)), ctr + side * 6000 + Vector((0, 0, -200)),
          ctr + side * 6000 + Vector((0, 0, top)), ctr - side * 6000 + Vector((0, 0, top))]
    ob = mesh_obj('ValleyShadow', vs, [(0, 1, 2, 3)], c, M('black_plastic'))
    for attr in ('visible_camera', 'visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter'):
        setattr(ob, attr, False)
    ob.visible_shadow = True
    return ob

def build_exterior_lights(c):
    # cantilever soffit downlights over the kitchen terrace
    for k in range(9):
        x = 3.8 + k * 2.0
        I.spot(f'X_soffit{k}', (x, -1.1, 3.26), 70, 70, 0.85, 2800, c, aim=(x + 0.001, -1.1, 0), radius=0.04)
        cyl(f'X_soffittrim{k}', 0.05, 0.006, (x, -1.1, 3.275), M('warm_light'), coll('Exterior_Fixtures'), 24, bev=0)
    # entry portal: downlight + grazing uplights on the limestone core
    I.spot('X_portal', (0.0, 1.75, 6.3), 140, 50, 0.7, 2800, c, aim=(0.0, 1.8, 0.0))
    for k, x in enumerate((-2.2, 2.2)):
        I.spot(f'X_graze{k}', (x, 1.6, 0.05), 160, 22, 0.5, 2900, c, aim=(x, 1.9, 7.0), radius=0.02)
    # chimney & pavilion corners grazed from below
    for k, (x, y, tx, ty) in enumerate(((-16.4, 4.9, -16.0, 5.3), (-16.4, 9.1, -16.0, 8.7), (-15.2, -0.6, -15.0, 0.0), (-2.8, -0.6, -3.0, 0.0))):
        I.spot(f'X_up{k}', (x, y, 0.05), 140, 18, 0.5, 2900, c, aim=(tx, ty, 9.0), radius=0.02)
    # east stone end
    for k, y in enumerate((1.5, 6.0, 10.5)):
        I.spot(f'X_east{k}', (19.6, y, 0.05), 90, 24, 0.5, 2900, c, aim=(19.05, y, 3.4), radius=0.02)

def render_settings(res=(1280, 720), samples=8, look=LOOK):
    s = bpy.context.scene
    s.render.engine = 'CYCLES'
    cy = s.cycles
    cy.device = 'CPU'
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.08
    cy.adaptive_min_samples = 4
    cy.use_denoising = True
    try:
        cy.denoiser = 'OPENIMAGEDENOISE'
        cy.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
        cy.denoising_prefilter = 'ACCURATE'
    except Exception:
        pass
    cy.max_bounces = 6
    cy.diffuse_bounces = 2
    cy.glossy_bounces = 2
    cy.transmission_bounces = 4
    cy.transparent_max_bounces = 8
    cy.use_fast_gi = True
    cy.fast_gi_method = 'REPLACE'
    cy.ao_bounces_render = 1
    if s.world:
        s.world.light_settings.distance = 6.0
    cy.volume_bounces = 0
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.blur_glossy = 1.0
    cy.sample_clamp_direct = 0.0
    cy.sample_clamp_indirect = 6.0
    cy.use_light_tree = True
    try:
        cy.use_auto_tile = True
        cy.tile_size = 512
    except Exception:
        pass
    s.render.use_persistent_data = True
    s.render.resolution_x, s.render.resolution_y = res
    s.render.resolution_percentage = 100
    s.render.film_transparent = False
    s.render.filter_size = 1.3
    s.render.threads_mode = 'AUTO'
    vs = s.view_settings
    vs.view_transform = 'AgX'
    for lk in ('AgX - Medium High Contrast', 'Medium High Contrast', 'AgX - Base Contrast', 'None'):
        try:
            vs.look = lk
            break
        except Exception:
            continue
    vs.exposure = look['exposure']
    vs.gamma = 1.0
    s.render.image_settings.file_format = 'PNG'
    s.render.image_settings.color_depth = '8'
    s.render.image_settings.compression = 15

def build(look=None):
    look = look or LOOK
    c = coll('Lighting')
    build_world(look)
    build_sun(look, c)
    build_valley_shadow(look, c)
    build_exterior_lights(coll('Exterior_Lights'))
    render_settings(look=look)
