import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/examples/jsm/loaders/DRACOLoader.js";
import { Sky } from "three/examples/jsm/objects/Sky.js";
import { Reflector } from "three/examples/jsm/objects/Reflector.js";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/examples/jsm/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/examples/jsm/postprocessing/OutputPass.js";
import { CameraPath, newPose, SENSOR, type Pose } from "./path";

/**
 * The house drawn live: one continuous camera take driven by scroll.
 *
 * Everything is lit in Blender beforehand (blender/bake_rt.py): large surfaces carry a colour
 * atlas and a denoised light map, small objects and the landscape carry colour x light in their
 * vertices, so the browser evaluates no lights at all. Glass, lamps and metal keep their own
 * materials; the lake reflects the scene; lamps and lit windows glow (bloom).
 */

/* ------------------------------------------------------------------ public/rt/scene.json */
type MatDesc = { color: number[]; rough: number; metal: number; emit: { color: number[]; strength: number } | null; glass: boolean; image: string | null };
type SceneDesc = {
  materials: Record<string, MatDesc>;
  forest: { meshes: string[]; trees: number[][] };
  door: { open_deg: number };
  world: { sun_elev: number; sun_azim: number };
  atlases: Record<string, { color: string; light: string; size: [number, number] }>;
  objects: Record<string, "atlas" | "vertex" | "special" | "water" | "lod">;
  light_scale: number;
  /** export stamp (bake_rt.py): every file of one export is requested with it */
  build?: string;
};

const BASE = "/rt/";

/* ------------------------------------------------------------------ look */
const FOG_DENSITY = 0.00026;
const FOG_COLOR = new THREE.Color(0.075, 0.1, 0.14);
/** objects seen from inside the house (the lake reflection skips them) */
const INTERIOR_RE = /^(A_Architecture_int|[AVS]_(Arrival|Great_Room|Kitchen|Study|Upper)(_detail)?)$/;
const NO_REFLECT_RE = /^(V_(Rocks|Grasses|Shrubs|Exterior_Fixtures|Far)|.*_detail)$/;
/** landscape and solids drawn front-faces only (leaves, grass and small details stay double-sided) */
const SINGLE_SIDED = /^V_(Far|Terrain|Rocks)$/;
/** layers: 0 drawn and reflected, 1 drawn only, 2 reflected only (billboards standing in for near trees) */
const REFLECT_ONLY = 2;
/** where the interior reflection probe is captured (Blender coordinates): mid great room */
const PROBE_AT = [-9, 6.5, 1.7] as const;
/** how much the glossiest surfaces (marble, oak floor) reflect the room */
const FLOOR_SHINE = 0.16;
/** light on the trees: what the bake gives the open meadow at dusk */
const TREE_LIGHT = new THREE.Color(0.24, 0.27, 0.33);
/** trees within this distance of the camera's route are meshes; the rest are billboards */
const NEAR_TREES = 50;
/** bloom: lamps and lit windows glow */
const BLOOM = { strength: 0.42, radius: 0.55, threshold: 0.85 };
/**
 * Quality tiers, best first: [resolution scale, glow]. The page starts on the best tier that
 * holds 60 fps on this device and steps between tiers as frame times change.
 */
const TIERS: [number, boolean][] = [
  [1, true],
  [0.85, true],
  [0.85, false],
  [0.72, false],
  [0.6, false],
];
/** frame budget for choosing a tier (ms): a 60 Hz frame with a little headroom */
const BUDGET = 16.5;
/** the exporter can't read roughness through procedural nodes; values from hlib.py */
const ROUGH: Record<string, number> = { Brass_Brushed: 0.28, Steel_Brushed: 0.25, Metal_Bronze_Dark: 0.35, Metal_Black: 0.42, Roof_Zinc: 0.48 };
/** linear RGB of the blackbody colours Cycles used for emitters */
const K2700: [number, number, number] = [1.0, 0.4, 0.11];
const K1800: [number, number, number] = [1.0, 0.22, 0.02];
/** materials carrying Cycles' distance haze as emission (fog does that job here) */
const HAZE = new Set(["Conifer_Foliage", "Hills_Forest", "Mountain_Snow", "Terrain_Meadow"]);

/** Blender (x, y, z) -> three (x, z, -y) */
const C = new THREE.Matrix4().set(1, 0, 0, 0, 0, 0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1);
const CT = C.clone().transpose();

/* ------------------------------------------------------------------ water */
const WaterShader = {
  name: "HalcyonWater",
  uniforms: {
    color: { value: new THREE.Color() },
    tDiffuse: { value: null as THREE.Texture | null },
    textureMatrix: { value: new THREE.Matrix4() },
    time: { value: 0 },
    deep: { value: new THREE.Color(0.004, 0.012, 0.018) },
    fogColor: { value: FOG_COLOR.clone() },
    fogDensity: { value: FOG_DENSITY },
  },
  vertexShader: /* glsl */ `
    uniform mat4 textureMatrix;
    varying vec4 vUv;
    varying vec3 vWorld;
    void main() {
      vUv = textureMatrix * vec4(position, 1.0);
      vec4 w = modelMatrix * vec4(position, 1.0);
      vWorld = w.xyz;
      gl_Position = projectionMatrix * viewMatrix * w;
    }`,
  fragmentShader: /* glsl */ `
    uniform sampler2D tDiffuse;
    uniform float time;
    uniform vec3 deep;
    uniform vec3 fogColor;
    uniform float fogDensity;
    varying vec4 vUv;
    varying vec3 vWorld;
    // gradient of a few travelling swells: a calm lake at dusk
    vec2 swell(vec2 p, vec2 d, float k, float a, float s) {
      float ph = dot(p, d) * k + time * s;
      return d * (a * k * cos(ph));
    }
    void main() {
      vec3 toEye = cameraPosition - vWorld;
      float dist = length(toEye);
      vec3 v = toEye / dist;
      vec2 p = vWorld.xz;
      vec2 g = swell(p, normalize(vec2(0.8, 0.6)), 0.21, 0.035, 0.9)
             + swell(p, normalize(vec2(-0.4, 0.9)), 0.37, 0.02, 1.3)
             + swell(p, normalize(vec2(0.95, -0.3)), 0.9, 0.008, 2.1)
             + swell(p, normalize(vec2(-0.7, -0.7)), 1.7, 0.004, 2.9);
      g *= 1.0 / (1.0 + dist * 0.012);
      vec3 n = normalize(vec3(-g.x, 1.0, -g.y));
      float c = max(dot(n, v), 0.0);
      float fres = 0.02 + 0.98 * pow(1.0 - c, 5.0);
      vec4 uv = vUv;
      uv.xy += n.xz * 1.6 * min(1.0, 30.0 / dist);
      vec3 refl = texture2DProj(tDiffuse, uv).rgb;
      vec3 col = mix(deep, refl, clamp(fres * 1.15, 0.0, 1.0));
      float f = 1.0 - exp(-pow(dist * fogDensity, 2.0));
      gl_FragColor = vec4(mix(col, fogColor, f), 1.0);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }`,
};

/* ------------------------------------------------------------------ engine */
export type FrameStats = { fps: number; frameMs: number; cpuMs: number; gpuMs: number | null; dpr: number; calls: number; tris: number; bloom: boolean };

type GpuTimer = { ext: { TIME_ELAPSED_EXT: number; GPU_DISJOINT_EXT: number }; pending: WebGLQuery[]; last: number | null };

export class RealtimeEngine {
  readonly path = new CameraPath();
  readonly renderer: THREE.WebGLRenderer;
  readonly scene = new THREE.Scene();
  readonly camera = new THREE.PerspectiveCamera(40, 16 / 9, 0.06, 12000);
  /** scroll progress 0..1, set by the page before each tick */
  q = 0;
  onFrame: ((pose: Pose, stats: FrameStats) => void) | null = null;
  /** called if the GPU drops the context (drawing stops instead of showing black) */
  onLost: (() => void) | null = null;
  lost = false;
  /** what calibration measured per tier tried (ms per frame), for the ?hud readout */
  calibration: number[] = [];

  private composer: EffectComposer;
  private bloom: UnrealBloomPass;
  private pose = newPose();
  private look = new THREE.Vector3();
  private raf = 0;
  private last = 0;
  private deltas: number[] = [];
  private cpu: number[] = [];
  private gpuTimes: number[] = [];
  private gpu: GpuTimer | null = null;
  private baseDpr = 1;
  private tier = 0;
  private slowSince = 0;
  private fastSince = 0;
  private width = 1;
  private height = 1;
  private water: Reflector | null = null;
  private waterCheap: THREE.Mesh | null = null;
  private doors: { node: THREE.Object3D; q0: THREE.Quaternion }[] = [];
  private doorAxis = new THREE.Vector3(0, 1, 0);
  private doorOpen = THREE.MathUtils.degToRad(84);
  private fire: { mat: THREE.MeshBasicMaterial; base: THREE.Color }[] = [];
  private wordmark: THREE.Mesh | null = null;
  private wordAspect = 5;
  /** "?v=<build>" from scene.json, appended to every file of the export */
  private version = "";
  private disposables: { dispose: () => void }[] = [];

  private constructor(canvas: HTMLCanvasElement) {
    canvas.addEventListener("webglcontextlost", (ev) => {
      ev.preventDefault();
      this.lost = true;
      cancelAnimationFrame(this.raf);
      this.onLost?.();
    });
    // anti-aliasing happens in the composer's multisampled target, not the canvas
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: "high-performance", stencil: false });
    this.renderer.toneMapping = THREE.AgXToneMapping;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.info.autoReset = false;
    const target = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 4 });
    this.composer = new EffectComposer(this.renderer, target);
    this.composer.addPass(new RenderPass(this.scene, this.camera));
    this.bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), BLOOM.strength, BLOOM.radius, BLOOM.threshold);
    this.composer.addPass(this.bloom);
    this.composer.addPass(new OutputPass());
    const gl = this.renderer.getContext() as WebGL2RenderingContext;
    const ext = gl.getExtension("EXT_disjoint_timer_query_webgl2");
    if (ext) this.gpu = { ext, pending: [], last: null };
  }

  static async create(canvas: HTMLCanvasElement, onProgress: (f: number) => void) {
    const e = new RealtimeEngine(canvas);
    await e.load(onProgress);
    return e;
  }

  /* ---------------------------------------------------------------- build */
  private async load(onProgress: (f: number) => void) {
    const draco = new DRACOLoader().setDecoderPath(`${BASE}draco/`);
    const loader = new GLTFLoader().setDRACOLoader(draco);
    // scene.json first and never from cache: its build stamp then versions the model and every
    // texture, so a re-export always loads whole (a cached model never meets newer atlases)
    const desc = (await fetch(`${BASE}scene.json`, { cache: "no-store" }).then((r) => r.json())) as SceneDesc;
    this.version = desc.build ? `?v=${desc.build}` : "";
    const gltf = await loader.loadAsync(`${BASE}halcyon.glb${this.version}`, (ev) => onProgress(Math.min(1, ev.loaded / (ev.total || 3.2e6)) * 0.35));
    draco.dispose();
    this.doorOpen = THREE.MathUtils.degToRad(desc.door.open_deg);
    const maps = await this.loadAtlases(desc, (f) => onProgress(0.35 + 0.55 * f));
    const scale = desc.light_scale;

    const root = gltf.scene;
    root.updateMatrixWorld(true);
    // the top-level nodes are the objects exported from Blender
    const tops = new Map<string, { node: THREE.Object3D; meshes: THREE.Mesh[] }>();
    root.traverse((o) => {
      if (!(o as THREE.Mesh).isMesh) return;
      let top: THREE.Object3D = o;
      while (top.parent && top.parent !== root) top = top.parent;
      if (!tops.has(top.name)) tops.set(top.name, { node: top, meshes: [] });
      tops.get(top.name)!.meshes.push(o as THREE.Mesh);
    });

    const lodMeshes = new Map<string, THREE.Mesh[]>();
    const lakes: THREE.Mesh[] = [];
    const cache = new Map<string, THREE.Material>();
    const probeAtlas: THREE.MeshBasicMaterial[] = [];
    const probeStd: THREE.MeshStandardMaterial[] = [];
    for (const [name, { node, meshes }] of tops) {
      if (name.startsWith("LOD")) {
        lodMeshes.set(name, meshes);
        continue;
      }
      if (name.startsWith("W_")) {
        lakes.push(...meshes);
        continue;
      }
      if (/^[AS]_Door/.test(name)) this.doors.push({ node, q0: node.quaternion.clone() });
      const kind = desc.objects[name] ?? "special";
      const interior = INTERIOR_RE.test(name);
      const layer = interior || NO_REFLECT_RE.test(name) ? 1 : 0;
      if (kind === "atlas" || kind === "vertex") {
        // one draw call per object: every primitive shares the atlas (or the vertex colours)
        let mat: THREE.Material;
        if (kind === "atlas") {
          const mp = maps.get(name)!;
          const am = atlasMaterial(name, mp.color, mp.light, scale);
          if (interior) probeAtlas.push(am);
          mat = am;
        } else {
          mat = vertexMaterial(name, scale);
        }
        this.disposables.push(mat);
        const geo = mergeMeshes(meshes, kind === "atlas" ? ["position", "normal", "uv"] : ["position", "normal", "color"]);
        if (geo) {
          for (const m of meshes) {
            if (m.geometry !== geo) m.geometry.dispose();
            if (m !== node) m.removeFromParent();
          }
          if ((node as THREE.Mesh).isMesh) {
            (node as THREE.Mesh).geometry = geo;
            (node as THREE.Mesh).material = mat;
            node.layers.set(layer);
          } else {
            const one = new THREE.Mesh(geo, mat);
            one.name = name;
            one.layers.set(layer);
            node.add(one);
          }
        } else {
          for (const m of meshes) {
            m.material = mat;
            m.layers.set(layer);
          }
        }
        continue;
      }
      // glass, lamps, metal, the laptop screen: a material per primitive
      for (const m of meshes) {
        const mname = (m.material as THREE.Material).name;
        const key = `${interior ? "i" : "e"}|${mname}`;
        if (!cache.has(key)) {
          const made = this.specialMaterial(mname, desc.materials[mname], interior);
          if (interior && (made as THREE.MeshStandardMaterial).isMeshStandardMaterial) probeStd.push(made as THREE.MeshStandardMaterial);
          cache.set(key, made);
        }
        (m.material as THREE.Material).dispose();
        m.material = cache.get(key)!;
        if (mname === "Laptop_Screen") planarUV(m);
        m.layers.set(layer);
      }
    }
    for (const mat of cache.values()) this.disposables.push(mat);
    root.traverse((o) => {
      o.updateMatrix();
      o.matrixAutoUpdate = false;
    });
    for (const d of this.doors) d.node.traverse((o) => (o.matrixAutoUpdate = true));
    for (const list of lodMeshes.values()) for (const m of list) m.removeFromParent();
    for (const m of lakes) m.removeFromParent();
    this.scene.add(root);

    this.buildSky(desc);
    this.buildForest(desc, lodMeshes);
    if (lakes[0]) this.buildWater(lakes[0]);

    this.resize(window.innerWidth, window.innerHeight);
    this.camera.layers.enableAll();
    this.camera.layers.disable(REFLECT_ONLY);
    this.apply(0);
    this.captureProbe(probeAtlas, probeStd);
    onProgress(0.94);
    // compile every shader now, so nothing compiles mid-scroll
    if (this.waterCheap) this.waterCheap.visible = true;
    await this.renderer.compileAsync(this.scene, this.camera);
    this.calibrate();
    this.apply(0);
    this.composer.render();
    onProgress(1);
  }

  /** Colour and light atlases (half size on phones and low-memory devices). */
  private async loadAtlases(desc: SceneDesc, onProgress: (f: number) => void) {
    const nav = navigator as Navigator & { deviceMemory?: number };
    const half = Math.min(screen.width, screen.height) < 820 || (nav.deviceMemory ?? 8) < 4;
    const tl = new THREE.TextureLoader();
    const entries = Object.entries(desc.atlases);
    let done = 0;
    const get = async (file: string, srgb: boolean) => {
      const t = await tl.loadAsync(`${BASE}${half ? file.replace(/\.webp$/, "_h.webp") : file}${this.version}`);
      t.flipY = false; // glTF UVs: v = 0 is the top row
      t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
      t.anisotropy = srgb ? 4 : 1;
      t.needsUpdate = true;
      this.disposables.push(t);
      onProgress(++done / (entries.length * 2));
      return t;
    };
    const out = new Map<string, { color: THREE.Texture; light: THREE.Texture }>();
    await Promise.all(
      entries.map(async ([name, a]) => {
        const [color, light] = await Promise.all([get(a.color, true), get(a.light, false)]);
        out.set(name, { color, light });
      }),
    );
    return out;
  }

  private specialMaterial(name: string, d: MatDesc | undefined, interior: boolean): THREE.Material {
    const color = new THREE.Color(...((d?.color ?? [0.6, 0.6, 0.6]) as [number, number, number]));
    const base = { name, side: THREE.DoubleSide, envMapIntensity: interior ? 0.6 : 1 };
    switch (name) {
      case "Glass_Window":
        return new THREE.MeshStandardMaterial({ ...base, color: new THREE.Color(0.55, 0.62, 0.64), roughness: 0.04, metalness: 0, transparent: true, opacity: 0.16, depthWrite: false, envMapIntensity: 1 });
      case "Glass_Clear":
        return new THREE.MeshStandardMaterial({ ...base, color: new THREE.Color(0.8, 0.85, 0.84), roughness: 0.03, metalness: 0, transparent: true, opacity: 0.08, depthWrite: false, envMapIntensity: 1 });
      case "Glass_Frosted":
        return new THREE.MeshStandardMaterial({ ...base, color: new THREE.Color(0.85, 0.85, 0.83), roughness: 0.3, transparent: true, opacity: 0.55, depthWrite: false });
      case "Black_Glass":
        return new THREE.MeshStandardMaterial({ ...base, color: new THREE.Color(0.002, 0.002, 0.002), roughness: 0.06, metalness: 0, envMapIntensity: 1 });
      case "Curtain_Sheer":
        return new THREE.MeshStandardMaterial({ ...base, color: new THREE.Color(0.75, 0.72, 0.66), roughness: 0.9, transparent: true, opacity: 0.6, depthWrite: false });
      case "Pool_Water":
        return new THREE.MeshStandardMaterial({ ...base, color: new THREE.Color(0.05, 0.32, 0.33), roughness: 0.04, transparent: true, opacity: 0.55, depthWrite: false });
      case "Fire_Flames":
        return new THREE.MeshBasicMaterial({ name, color: new THREE.Color(K1800[0] * 3, K1800[1] * 3, K1800[2] * 3), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
      case "Laptop_Screen": {
        const tex = new THREE.TextureLoader().load(`${BASE}${d?.image ?? "laptop_screen.png"}${this.version}`);
        tex.colorSpace = THREE.SRGBColorSpace;
        tex.anisotropy = 8;
        this.disposables.push(tex);
        // a lit screen, not a lamp: kept under the glow threshold so the drawing set stays legible
        return new THREE.MeshBasicMaterial({ name, map: tex, color: new THREE.Color(0.62, 0.62, 0.62) });
      }
    }
    if (d?.emit && !HAZE.has(name)) {
      // emitters: their own light, unlit (and bright enough to bloom)
      const k = name === "Emit_Fire" ? K1800 : name.startsWith("Emit_") ? K2700 : (d.emit.color as [number, number, number]);
      const glow = new THREE.Color(...k).multiplyScalar(d.emit.strength);
      const mat = new THREE.MeshBasicMaterial({ name, color: glow, side: THREE.DoubleSide });
      if (name === "Emit_Fire") this.fire.push({ mat, base: glow.clone() });
      return mat;
    }
    // metals: no diffuse to bake, so they show their surroundings (the room probe indoors, the sky outside)
    return new THREE.MeshStandardMaterial({ ...base, color, roughness: ROUGH[name] ?? d?.rough ?? 0.5, metalness: d?.metal ?? 0 });
  }

  /** One reflection capture of the lit interior, for the glossy surfaces indoors. */
  private captureProbe(atlas: THREE.MeshBasicMaterial[], std: THREE.MeshStandardMaterial[]) {
    const rt = new THREE.WebGLCubeRenderTarget(128, { type: THREE.HalfFloatType });
    const cam = new THREE.CubeCamera(0.1, 400, rt);
    cam.layers.enableAll();
    cam.layers.disable(REFLECT_ONLY);
    cam.position.set(PROBE_AT[0], PROBE_AT[2], -PROBE_AT[1]);
    this.scene.add(cam);
    cam.update(this.renderer, this.scene);
    cam.removeFromParent();
    for (const m of atlas) {
      m.envMap = rt.texture;
      m.reflectivity = FLOOR_SHINE;
      m.needsUpdate = true;
    }
    for (const m of std) {
      m.envMap = rt.texture;
      m.needsUpdate = true;
    }
    this.disposables.push(rt);
  }

  /**
   * Conifers: near the route, the decimated mesh; elsewhere a crossed-quad billboard whose
   * picture is rendered from that same mesh at load, so the far forest keeps its silhouette.
   */
  private buildForest(desc: SceneDesc, lods: Map<string, THREE.Mesh[]>) {
    const types = desc.forest.meshes;
    const near: THREE.BufferGeometry[] = types.map((t) => {
      const parts = (lods.get(`LODF_${t}`) ?? []).map((m) => {
        const g = m.geometry.clone();
        g.applyMatrix4(m.matrixWorld);
        const c = desc.materials[(m.material as THREE.Material).name]?.color ?? [0.02, 0.03, 0.02];
        const col = new Float32Array(g.attributes.position.count * 3);
        for (let i = 0; i < g.attributes.position.count; i++) col.set(c, i * 3);
        g.setAttribute("color", new THREE.BufferAttribute(col, 3));
        for (const k of Object.keys(g.attributes)) if (!["position", "normal", "color"].includes(k)) g.deleteAttribute(k);
        return g;
      });
      const merged = parts.length ? mergeGeometries(parts, false) : null;
      parts.forEach((p) => p.dispose());
      return merged ?? new THREE.BufferGeometry();
    });
    const treeMat = new THREE.MeshBasicMaterial({ name: "Forest", vertexColors: true, color: TREE_LIGHT });

    // billboard pictures: each conifer rendered side-on into one atlas row
    const cell = 128;
    const atlasRT = new THREE.WebGLRenderTarget(cell * types.length, cell * 2, { samples: 4 });
    const tmpScene = new THREE.Scene();
    const ortho = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 200);
    const prevClear = this.renderer.getClearColor(new THREE.Color());
    const prevAlpha = this.renderer.getClearAlpha();
    this.renderer.setRenderTarget(atlasRT);
    this.renderer.setClearColor(0x000000, 0);
    this.renderer.clear();
    const far: THREE.BufferGeometry[] = [];
    near.forEach((g, i) => {
      g.computeBoundingBox();
      const bb = g.boundingBox!;
      const w = Math.max(bb.max.x - bb.min.x, bb.max.z - bb.min.z);
      const h = bb.max.y - bb.min.y;
      const cx = (bb.max.x + bb.min.x) / 2;
      const cz = (bb.max.z + bb.min.z) / 2;
      const mesh = new THREE.Mesh(g, treeMat);
      tmpScene.add(mesh);
      ortho.left = -w / 2;
      ortho.right = w / 2;
      ortho.top = h / 2;
      ortho.bottom = -h / 2;
      ortho.position.set(cx, (bb.max.y + bb.min.y) / 2, cz + 100);
      ortho.lookAt(cx, (bb.max.y + bb.min.y) / 2, cz);
      ortho.updateProjectionMatrix();
      this.renderer.setViewport(i * cell, 0, cell, cell * 2);
      this.renderer.setScissor(i * cell, 0, cell, cell * 2);
      this.renderer.setScissorTest(true);
      this.renderer.render(tmpScene, ortho);
      tmpScene.remove(mesh);
      // two quads crossing at the trunk, mapped to this tree's cell
      const u0 = i / types.length;
      const u1 = (i + 1) / types.length;
      const quads: THREE.BufferGeometry[] = [0, Math.PI / 2].map((rot) => {
        const q = new THREE.PlaneGeometry(w, h);
        const uv = q.attributes.uv;
        for (let k = 0; k < uv.count; k++) uv.setX(k, u0 + uv.getX(k) * (u1 - u0));
        q.rotateY(rot);
        q.translate(cx, (bb.max.y + bb.min.y) / 2, cz);
        q.deleteAttribute("normal");
        return q;
      });
      far.push(mergeGeometries(quads, false)!);
      quads.forEach((q) => q.dispose());
    });
    this.renderer.setScissorTest(false);
    this.renderer.setRenderTarget(null);
    this.renderer.setClearColor(prevClear, prevAlpha);
    const atlasTex = atlasRT.texture;
    atlasTex.generateMipmaps = false;

    const route: THREE.Vector2[] = [];
    const p = newPose();
    for (let i = 0; i <= 200; i++) {
      this.path.at(i / 200, p);
      route.push(new THREE.Vector2(p.x, p.y));
    }
    const trees = desc.forest.trees;
    const isNear = (t: number[]) => {
      const v = new THREE.Vector2(t[4], t[8]);
      return route.some((r) => r.distanceToSquared(v) < NEAR_TREES * NEAR_TREES);
    };
    const count = (gs: THREE.BufferGeometry[]) => gs.reduce((a, g) => [a[0] + (g.attributes.position?.count ?? 0), a[1] + (g.index?.count ?? 0)], [0, 0]);
    const [nv, ni] = count(near);
    const [fv, fi] = count(far);
    const nearBatch = new THREE.BatchedMesh(trees.length, nv, ni, treeMat);
    const billMat = new THREE.MeshBasicMaterial({ name: "ForestFar", map: atlasTex, alphaTest: 0.45, side: THREE.DoubleSide });
    const farBatch = new THREE.BatchedMesh(trees.length, fv, fi, billMat);
    const reflBatch = new THREE.BatchedMesh(trees.length, fv, fi, billMat);
    const nearIds = near.map((g) => nearBatch.addGeometry(g));
    const farIds = far.map((g) => farBatch.addGeometry(g));
    const reflIds = far.map((g) => reflBatch.addGeometry(g));
    const mb = new THREE.Matrix4();
    const m3 = new THREE.Matrix4();
    for (const t of trees) {
      mb.set(t[1], t[2], t[3], t[4], t[5], t[6], t[7], t[8], t[9], t[10], t[11], t[12], 0, 0, 0, 1);
      m3.multiplyMatrices(C, mb).multiply(CT);
      if (isNear(t)) {
        nearBatch.setMatrixAt(nearBatch.addInstance(nearIds[t[0]]), m3);
        reflBatch.setMatrixAt(reflBatch.addInstance(reflIds[t[0]]), m3);
      } else farBatch.setMatrixAt(farBatch.addInstance(farIds[t[0]]), m3);
    }
    nearBatch.sortObjects = false;
    farBatch.sortObjects = false;
    reflBatch.sortObjects = false;
    // the lake reflects every tree as a billboard; the eye sees the near ones as meshes
    nearBatch.layers.set(1);
    reflBatch.layers.set(REFLECT_ONLY);
    this.scene.add(nearBatch, farBatch, reflBatch);
    this.disposables.push(nearBatch, farBatch, reflBatch, treeMat, billMat, atlasRT, ...near, ...far);
  }

  private buildSky(desc: SceneDesc) {
    const e = THREE.MathUtils.degToRad(desc.world.sun_elev);
    const a = THREE.MathUtils.degToRad(desc.world.sun_azim);
    // compass azimuth (0 = +Y north) in Blender -> three
    const sun = new THREE.Vector3(Math.sin(a) * Math.cos(e), Math.sin(e), -Math.cos(a) * Math.cos(e));
    const sky = new Sky();
    sky.scale.setScalar(9000);
    const u = sky.material.uniforms;
    u.turbidity.value = 3.2;
    u.rayleigh.value = 2.4;
    u.mieCoefficient.value = 0.004;
    u.mieDirectionalG.value = 0.82;
    u.sunPosition.value.copy(sun);
    if (u.showSunDisc) u.showSunDisc.value = false;
    if (u.cloudCoverage) u.cloudCoverage.value = 0;
    const skyScene = new THREE.Scene();
    skyScene.add(sky);
    // the sky never changes: render it once into a cube map and draw that as the background,
    // instead of evaluating the sky model for every pixel of every frame
    const cubeRT = new THREE.WebGLCubeRenderTarget(512, { type: THREE.HalfFloatType });
    const cubeCam = new THREE.CubeCamera(1, 20000, cubeRT);
    cubeCam.update(this.renderer, skyScene);
    this.scene.background = cubeRT.texture;
    // image-based light (glass, metal) from the same sky
    const pmrem = new THREE.PMREMGenerator(this.renderer);
    const env = pmrem.fromScene(skyScene, 0, 1, 20000);
    this.scene.environment = env.texture;
    this.disposables.push(env, pmrem, cubeRT, sky.geometry, sky.material);
    this.scene.fog = new THREE.FogExp2(FOG_COLOR.clone(), FOG_DENSITY);
  }

  private buildWater(lake: THREE.Mesh) {
    lake.geometry.computeBoundingBox();
    const bb = lake.geometry.boundingBox!.clone().applyMatrix4(lake.matrixWorld);
    const size = new THREE.Vector3();
    const ctr = new THREE.Vector3();
    bb.getSize(size);
    bb.getCenter(ctr);
    const geo = new THREE.PlaneGeometry(size.x, size.z);
    const shader = { ...WaterShader, uniforms: THREE.UniformsUtils.clone(WaterShader.uniforms) };
    const water = new Reflector(geo, { textureWidth: 512, textureHeight: 512, clipBias: 0.002, multisample: 0, shader });
    water.rotation.x = -Math.PI / 2;
    water.position.set(ctr.x, bb.min.y, ctr.z);
    // the reflection skips furniture and small things: none of it is visible in the lake
    const rc = water.getReflectionCamera(this.camera);
    rc.layers.set(0);
    rc.layers.enable(REFLECT_ONLY);
    this.scene.add(water);
    this.water = water;
    const cheap = new THREE.Mesh(
      geo,
      new THREE.MeshStandardMaterial({ name: "LakeCheap", color: new THREE.Color(0.004, 0.012, 0.018), roughness: 0.05, metalness: 0, envMapIntensity: 1.3 }),
    );
    cheap.rotation.x = -Math.PI / 2;
    cheap.position.copy(water.position);
    cheap.visible = false;
    this.scene.add(cheap);
    this.waterCheap = cheap;
    lake.geometry.dispose();
    this.disposables.push(water, geo, cheap.material as THREE.Material);
  }

  /**
   * The name set in the landscape for the opening view: between the house and the peaks, so the
   * trees and the roofline pass in front of it as the camera rises.
   */
  setWordmark(text: string, fontFamily: string, color: THREE.ColorRepresentation) {
    const cv = document.createElement("canvas");
    cv.width = 2048;
    cv.height = 400;
    const g = cv.getContext("2d")!;
    g.font = `600 300px ${fontFamily}`;
    g.fontStretch = "expanded";
    g.letterSpacing = "6px";
    const w = Math.min(cv.width, g.measureText(text).width + 24);
    g.fillStyle = "#fff";
    g.textBaseline = "alphabetic";
    g.textAlign = "center";
    g.fillText(text, cv.width / 2, 318);
    const tex = new THREE.CanvasTexture(cv);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = 4;
    const mat = new THREE.MeshBasicMaterial({ map: tex, color, transparent: true, depthWrite: false, fog: false });
    this.wordAspect = w / cv.height;
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(1, cv.height / w), mat);
    // crop the plane to the inked width
    const uv = mesh.geometry.attributes.uv;
    const u0 = 0.5 - w / cv.width / 2;
    for (let k = 0; k < uv.count; k++) uv.setX(k, u0 + uv.getX(k) * (w / cv.width));
    mesh.renderOrder = -1;
    mesh.frustumCulled = false;
    this.scene.add(mesh);
    this.wordmark = mesh;
    this.disposables.push(tex, mat, mesh.geometry);
    this.placeWordmark();
  }

  /** Size and place the wordmark for the opening view at the current aspect ratio. */
  private placeWordmark() {
    const m = this.wordmark;
    if (!m) return;
    const keep = this.q;
    this.apply(0);
    this.camera.updateMatrixWorld();
    const D = 150; // metres: beyond the house, well short of the mountains
    const halfH = D * Math.tan(THREE.MathUtils.degToRad(this.camera.fov) / 2);
    const halfW = halfH * this.camera.aspect;
    const width = Math.min(2 * halfW * 0.9, 2 * halfH * 0.42 * this.wordAspect);
    m.scale.set(width, width, 1);
    // centred, its baseline a little above the roofline
    const pos = new THREE.Vector3(0, 0.3, 0.5).unproject(this.camera);
    pos.sub(this.camera.position).normalize();
    const fwd = new THREE.Vector3();
    this.camera.getWorldDirection(fwd);
    pos.multiplyScalar(D / pos.dot(fwd)).add(this.camera.position);
    m.position.copy(pos);
    m.quaternion.copy(this.camera.quaternion);
    this.apply(keep);
  }

  /* ---------------------------------------------------------------- frame */
  resize(w: number, h: number) {
    this.width = w;
    this.height = h;
    this.baseDpr = Math.min(window.devicePixelRatio || 1, 1.25);
    this.applySize();
    this.placeWordmark();
  }

  private applySize() {
    const [scale, glow] = TIERS[this.tier];
    this.bloom.enabled = glow;
    const dpr = this.baseDpr * scale;
    this.renderer.setPixelRatio(dpr);
    this.renderer.setSize(this.width, this.height, false);
    this.composer.setPixelRatio(dpr);
    this.composer.setSize(this.width, this.height);
    this.bloom.resolution.set(Math.round((this.width * dpr) / 2), Math.round((this.height * dpr) / 2));
    this.camera.aspect = this.width / this.height;
    // a low-resolution reflection: the ripples blur it anyway
    if (this.water) this.water.getRenderTarget().setSize(Math.round((this.width * dpr) / 6), Math.round((this.height * dpr) / 6));
  }

  /** Put everything where scroll progress q says. */
  apply(q: number, now = performance.now()) {
    const p = this.path.at(q, this.pose);
    this.camera.position.set(p.x, p.z, -p.y);
    const cp = Math.cos(p.pitch);
    this.look.set(p.x + cp * Math.cos(p.yaw), p.z + Math.sin(p.pitch), -(p.y + cp * Math.sin(p.yaw)));
    this.camera.lookAt(this.look);
    const hf = 2 * Math.atan(SENSOR / (2 * p.lens));
    this.camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(hf / 2) / Math.max(this.camera.aspect, 1.45)));
    this.camera.updateProjectionMatrix();
    this.renderer.toneMappingExposure = Math.pow(2, p.ev);
    // the pivot door swings as the camera walks up the steps (as in the film)
    if (this.doors.length) {
      const f = p.u > 11 ? 1 : THREE.MathUtils.smoothstep(p.y, -9, -1.4);
      for (const d of this.doors) d.node.quaternion.setFromAxisAngle(this.doorAxis, this.doorOpen * f).multiply(d.q0);
    }
    const inside = p.y > 2.6 && p.u > 9;
    if (this.water && this.waterCheap) {
      this.water.visible = !inside;
      this.waterCheap.visible = inside;
      (this.water.material as THREE.ShaderMaterial).uniforms.time.value = now / 1000;
    }
    for (const f of this.fire) {
      const t = now / 1000;
      f.mat.color.copy(f.base).multiplyScalar(0.86 + 0.08 * Math.sin(t * 7.1) + 0.06 * Math.sin(t * 13.7 + 1.3));
    }
    if (this.wordmark) {
      const o = 1 - THREE.MathUtils.smoothstep(q, 0.002, 0.022);
      this.wordmark.visible = o > 0.001;
      (this.wordmark.material as THREE.MeshBasicMaterial).opacity = 0.94 * o;
    }
    return p;
  }

  render() {
    this.renderer.info.reset();
    const g = this.gpu;
    const gl = this.renderer.getContext() as WebGL2RenderingContext;
    let query: WebGLQuery | null = null;
    if (g && g.pending.length < 4) {
      query = gl.createQuery();
      if (query) gl.beginQuery(g.ext.TIME_ELAPSED_EXT, query);
    }
    this.composer.render();
    if (g && query) {
      gl.endQuery(g.ext.TIME_ELAPSED_EXT);
      g.pending.push(query);
    }
    if (g && g.pending.length) {
      const q0 = g.pending[0];
      if (gl.getQueryParameter(q0, gl.QUERY_RESULT_AVAILABLE)) {
        if (!gl.getParameter(g.ext.GPU_DISJOINT_EXT)) {
          g.last = gl.getQueryParameter(q0, gl.QUERY_RESULT) / 1e6;
          this.gpuTimes.push(g.last);
          if (this.gpuTimes.length > 90) this.gpuTimes.shift();
        }
        gl.deleteQuery(q0);
        g.pending.shift();
      }
    }
  }

  /** One frame: the page sets q, then calls this from its animation clock. */
  tick(now: number) {
    if (this.lost) return;
    const dt = this.last ? now - this.last : 16.7;
    this.last = now;
    const t0 = performance.now();
    const pose = this.apply(this.q, now);
    this.render();
    this.cpu.push(performance.now() - t0);
    // a long gap means the page was idle or hidden, not slow
    if (dt < 250) this.deltas.push(dt);
    if (this.deltas.length > 90) this.deltas.shift();
    if (this.cpu.length > 90) this.cpu.shift();
    this.adapt(now);
    this.onFrame?.(pose, this.stats());
  }

  /** Standalone loop (the page normally drives tick from its own clock). */
  start() {
    const loop = (now: number) => {
      this.raf = requestAnimationFrame(loop);
      this.tick(now);
    };
    this.raf = requestAnimationFrame(loop);
  }

  /** Forget frame timings (after a pause, so the next frames aren't judged by it). */
  rest() {
    this.last = 0;
    this.deltas.length = 0;
    this.gpuTimes.length = 0;
  }

  /** Start on the best tier that renders a typical outdoor and indoor frame within budget. */
  private calibrate() {
    const gl = this.renderer.getContext();
    const px = new Uint8Array(4);
    const sync = () => gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
    // frames back to back, as playback runs them (CPU and GPU overlap), after a short warm-up
    // so the GPU has left its idle clock
    const cost = () => {
      let worst = 0;
      for (const q of [0.08, 0.5]) {
        this.apply(q);
        for (let k = 0; k < 6; k++) this.render();
        sync();
        const t0 = performance.now();
        for (let k = 0; k < 6; k++) this.render();
        sync();
        worst = Math.max(worst, (performance.now() - t0) / 6);
        if (worst > 3 * BUDGET) break;
      }
      return worst;
    };
    this.calibration = [];
    for (this.tier = 0; this.tier < TIERS.length - 1; this.tier++) {
      this.applySize();
      const c = cost();
      this.calibration.push(+c.toFixed(1));
      if (c <= BUDGET) break;
    }
    this.applySize();
    this.rest();
  }

  /**
   * Dynamic quality: step between tiers to hold the frame rate, with hysteresis. The frame
   * interval can't show headroom (it never drops below the display's refresh), so stepping up
   * uses the GPU's own timings where the browser provides them.
   */
  private adapt(now: number) {
    if (this.deltas.length < 60) return;
    const interval = median(this.deltas);
    const gpu = this.gpuTimes.length >= 30 ? median(this.gpuTimes) : null;
    const slow = interval > 20 || (gpu !== null && gpu > BUDGET);
    const fast = gpu !== null ? gpu < BUDGET * 0.6 : interval < 13;
    if (slow && this.tier < TIERS.length - 1) {
      this.fastSince = 0;
      if (!this.slowSince) this.slowSince = now;
      if (now - this.slowSince > 1200) {
        this.tier++;
        this.applySize();
        this.slowSince = now;
        this.deltas.length = 0;
        this.gpuTimes.length = 0;
      }
    } else if (fast && this.tier > 0) {
      this.slowSince = 0;
      if (!this.fastSince) this.fastSince = now;
      if (now - this.fastSince > 5000) {
        this.tier--;
        this.applySize();
        this.fastSince = now;
        this.deltas.length = 0;
        this.gpuTimes.length = 0;
      }
    } else {
      this.slowSince = 0;
      this.fastSince = 0;
    }
  }

  stats(): FrameStats {
    const med = this.deltas.length ? median(this.deltas) : 0;
    const info = this.renderer.info.render;
    return {
      fps: med ? 1000 / med : 0,
      frameMs: med,
      cpuMs: this.cpu.length ? median(this.cpu) : 0,
      gpuMs: this.gpu?.last ?? null,
      dpr: this.renderer.getPixelRatio(),
      calls: info.calls,
      tris: info.triangles,
      bloom: this.bloom.enabled,
    };
  }

  /** Dev: GPU-synced cost of one frame at each of n poses along the take. */
  bench(n = 16) {
    const gl = this.renderer.getContext();
    const px = new Uint8Array(4);
    const sync = () => gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
    const per: { q: number; ms: number; calls: number; tris: number }[] = [];
    for (let i = 0; i <= n; i++) {
      const q = i / n;
      this.apply(q);
      this.render();
      sync();
      const t0 = performance.now();
      this.render();
      sync();
      const info = this.renderer.info.render;
      per.push({ q: +q.toFixed(3), ms: +(performance.now() - t0).toFixed(1), calls: info.calls, tris: info.triangles });
      if (per[per.length - 1].ms > 400) break; // never hold the GPU long enough to reset it
    }
    this.apply(this.q);
    const ms = per.map((p) => p.ms).sort((a, b) => a - b);
    return { size: [this.renderer.domElement.width, this.renderer.domElement.height], median: ms[ms.length >> 1], max: ms[ms.length - 1], per };
  }

  dispose() {
    cancelAnimationFrame(this.raf);
    for (const d of this.disposables) d.dispose();
    this.scene.traverse((o) => {
      const m = o as THREE.Mesh;
      if (m.isMesh && m.geometry) m.geometry.dispose();
    });
    this.composer.dispose();
    this.renderer.dispose();
  }
}

function median(a: number[]) {
  const s = [...a].sort((x, y) => x - y);
  return s[Math.floor(s.length / 2)];
}

/** The screen has no UVs of its own: project the image onto its plane. */
function planarUV(m: THREE.Mesh) {
  const g = m.geometry;
  g.computeBoundingBox();
  const bb = g.boundingBox!;
  const pos = g.attributes.position;
  const uv = new Float32Array(pos.count * 2);
  const sx = bb.max.x - bb.min.x || 1;
  const sy = bb.max.y - bb.min.y || 1;
  for (let i = 0; i < pos.count; i++) {
    uv[i * 2] = (pos.getX(i) - bb.min.x) / sx;
    uv[i * 2 + 1] = (pos.getY(i) - bb.min.y) / sy;
  }
  g.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
}

/** Concatenate an object's primitives (same atlas or same vertex colours) into one geometry. */
function mergeMeshes(meshes: THREE.Mesh[], keep: string[]): THREE.BufferGeometry | null {
  const geos = meshes.map((m) => {
    const g = m.geometry.clone();
    // primitives of one node sit at identity under it; a lone mesh is the node itself
    if (meshes.length > 1) g.applyMatrix4(m.matrix);
    for (const k of Object.keys(g.attributes)) if (!keep.includes(k)) g.deleteAttribute(k);
    return g;
  });
  if (geos.length === 1) return geos[0];
  const same = geos.every((g) => keep.every((k) => !!g.attributes[k] === !!geos[0].attributes[k]));
  const merged = same ? mergeGeometries(geos, false) : null;
  geos.forEach((g) => g.dispose());
  return merged;
}

/**
 * Atlas surfaces: baked colour x baked light, plus a reflection of the interior probe
 * weighted by the baked roughness (carried in the colour map's alpha).
 */
function atlasMaterial(name: string, color: THREE.Texture, light: THREE.Texture, scale: number) {
  const mat = new THREE.MeshBasicMaterial({ name, map: color, side: THREE.FrontSide, combine: THREE.AddOperation, reflectivity: 0 });
  const uniforms = { rtLight: { value: light } };
  mat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, uniforms);
    sh.fragmentShader = sh.fragmentShader
      .replace("#include <common>", "#include <common>\nuniform sampler2D rtLight;")
      .replace(
        "#include <color_fragment>",
        `#include <color_fragment>
  vec3 rtL = texture2D( rtLight, vMapUv ).rgb;
  diffuseColor.rgb *= rtL * rtL * ${scale.toFixed(3)};
  float rtGloss = 1.0 - sampledDiffuseColor.a;`,
      )
      .replace("#include <specularmap_fragment>", "#include <specularmap_fragment>\n  specularStrength = rtGloss * rtGloss;");
  };
  mat.customProgramCacheKey = () => `atlas${scale}`;
  return mat;
}

/** Small or detailed objects and the landscape: colour x light baked into the vertices, stored as sqrt(x / scale). */
function vertexMaterial(name: string, scale: number) {
  const mat = new THREE.MeshBasicMaterial({ name, vertexColors: true, side: SINGLE_SIDED.test(name) ? THREE.FrontSide : THREE.DoubleSide });
  const k = scale.toFixed(3);
  mat.onBeforeCompile = (sh) => {
    sh.fragmentShader = sh.fragmentShader.replace(
      "#include <color_fragment>",
      `#if defined( USE_COLOR_ALPHA )
  diffuseColor.rgb *= vColor.rgb * vColor.rgb * ${k};
#elif defined( USE_COLOR )
  diffuseColor.rgb *= vColor * vColor * ${k};
#endif`,
    );
  };
  mat.customProgramCacheKey = () => `baked${scale}`;
  return mat;
}
