# Halcyon — residence walkthrough

A scroll-driven walkthrough of a lakeside residence. The house is modelled procedurally in
Blender, lit there with Cycles (path-traced, denoised), and drawn live in the browser with
three.js as one continuous camera take: from the lake, through the pivot door and the
ground-floor rooms, up the stair to the bedroom gallery and into each room off it (the
walnut west suite, the oak bunk room, the travertine principal suite), back down through
the kitchen, to the drawing set on the study laptop.

```bash
npm run dev     # http://localhost:3000
npm run build
```

## How the site works

| Part | Where |
| --- | --- |
| Walkthrough: pinned canvas, scroll → camera along one path, chapter cards, route line, hand-off to the drawing set; Lenis, the 3D frame and the overlays share one GSAP tick | `components/walkthrough/Walkthrough.tsx` |
| Renderer: loads the baked model, lake reflection, sky and fog, billboard forest, bloom, dynamic resolution | `components/walkthrough/engine.ts` |
| Camera route (Blender coordinates, chapter keys, scroll weighting) | `components/walkthrough/path.ts` |
| Drawing set: site plan, axonometric, interactive plan (select a room to walk to it), sections, materials | `components/dossier/` |
| Stills strip with shared-element lightbox (adapted from Kokonut UI on 21st.dev, MIT) | `components/stills/StillsStrip.tsx` |
| Copy and figures | `lib/residence.ts`, `lib/drawings.ts` |

`?hud` on the page shows frame rate, GPU time and resolution. If a browser can't run WebGL2
the section shows the dusk still instead.

## 3D pipeline (`blender/`)

The scene is built entirely from Python — no hand-modelled assets.

| Script | Builds |
| --- | --- |
| `hlib.py` | helpers + procedural PBR materials (ledgestone, oak, walnut, Calacatta, bronze, glass…) |
| `arch.py` | the three volumes: glazed gable pavilion, limestone arrival core, cantilevered timber wing (bedroom gallery and three rooms of different sizes upstairs) |
| `interior.py` | furniture, joinery, library, plants, interior lighting; upstairs each room has its own materials, furniture and light |
| `check_route.py`, `route_samples.mjs` | tests the walkthrough route against the model (below) |
| `hsite.py` | terraces, pool, dock, lake, terrain, forest, mountain range |
| `lighting.py` | dusk sky, sun, valley shadow, exterior lights, Cycles settings |
| `cams.py` | camera shots used for the gallery stills, door animation, per-room exposure |
| `build.py` | runs all of the above inside a running Blender |
| `bake_rt.py`, `rtlib.py`, `encode_rt.py` | the real-time build (below) |
| `render_frames.py`, `drawings.py` | gallery stills and the drawing set |

Rebuild the scene (Blender 5.2, in the Python console or via MCP):

```python
exec(open(r"<repo>/blender/build.py").read())
bpy.ops.wm.save_as_mainfile(filepath=r"<repo>/blender/halcyon.blend")
```

or headless:

```bash
blender -b --factory-startup -P blender/build.py --python-expr "import bpy; bpy.context.scene.frame_set(1); bpy.ops.wm.save_as_mainfile(filepath='blender/halcyon.blend')"
```

### Real-time build

```bash
blender -b blender/halcyon.blend --python blender/bake_rt.py -- prep     # join, split, unwrap -> blender/rt/prepared.blend
blender -b blender/rt/prepared.blend --python blender/bake_rt.py -- bake # colour, roughness, light (+ OIDN denoise); resumable
blender -b blender/rt/prepared.blend --python blender/bake_rt.py -- export
python blender/encode_rt.py                                              # atlases -> public/rt/*.webp (+ half size for phones)
```

Large surfaces get texture atlases: colour with roughness in alpha, and light stored as
`sqrt(light / 4)` (denoised with the OIDN library Blender ships). Small or detailed objects
and the landscape carry colour × light per vertex; glass, lamps and metal keep their own
materials. The browser evaluates no lights: every surface is colour × baked light, so it
stays fast on integrated graphics (the page lowers its resolution, then its glow, to hold
60 fps). A fresh bake takes about an hour on the CPU; edits to `path.ts` show at once, edits
to the model only after re-baking and re-exporting.

### Checking the route

The camera is a scripted path through the keys in `path.ts`, not a physics walk: nothing
stops a key sitting inside a wall. After editing the route or the model, test the whole take:

```bash
node blender/route_samples.mjs                                   # samples the path exactly as the browser does
blender -b blender/halcyon.blend -P blender/check_route.py       # exit 1 on any failure
```

It fails if any step passes through a surface (walls, glass, furniture, curtains), if the
camera comes within 0.3 m of anything indoors, if the eye drops below 1.52 m over the floor
or stair underneath, or if the route walks over furniture. The pivot door and the kitchen
bay are opened as in the browser. The final sit-down at the study desk may come within 0.1 m.

Gallery stills and the drawing set:

```bash
blender -b blender/halcyon.blend -P blender/render_frames.py -- --frames 56,166,204,259,306 --tag _still --width 1920 --out blender/renders/stills
blender -b blender/halcyon.blend -P blender/drawings.py -- --what plan,section,site,axo,swatches
```
