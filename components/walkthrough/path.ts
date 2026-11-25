import { CatmullRomCurve3, Vector3 } from "three";

/** Blender coordinates: metres, Z up, +Y north (lake to the south). */
type V3 = [number, number, number];

export type Key = {
  p: V3;
  look: V3;
  lens: number;
  /** scroll weight per metre: higher = the camera lingers */
  dens: number;
  /** exposure in stops (same values the Cycles film used) */
  ev: number;
  /** a chapter of the walk (lib/residence.ts CHAPTERS) begins at this key */
  chapter?: string;
};

/**
 * One continuous take: from the lake, up over the terraces, through the pivot door, a loop
 * around the great room (the lake through the gable), back across the hall and up the
 * floating stair to the bedroom gallery; into each of the three rooms off it in turn (the
 * west suite by its walnut dressing passage, the bunk room to its window seat and back, a
 * loop round the principal suite's travertine bed wall), back along the gallery and down the
 * stair, along the kitchen, through the open bay in the glass partition, and down to the
 * laptop in the study, whose screen (the drawing set) fills the frame at the end.
 *
 * The camera is a scripted path, not a physics walk: nothing stops a key sitting inside a wall.
 * blender/check_route.py tests the whole route against the model (see the README).
 *
 * On the stair the eye stays 1.62 m above the treads: z = 1.84 + 0.75 * (y - 5.51).
 */
export const KEYS: Key[] = [
  { p: [3.0, -58.0, 6.2], look: [2.0, 8.0, 6.6], lens: 32, dens: 1.1, ev: 0.35, chapter: "threshold" },
  { p: [12.0, -52.0, 12.0], look: [3.0, 5.0, 5.0], lens: 30, dens: 0.55, ev: 0.35 },
  { p: [30.0, -36.0, 19.0], look: [5.0, 2.0, 2.0], lens: 28, dens: 0.45, ev: 0.35, chapter: "aerial" },
  { p: [28.0, -18.0, 12.0], look: [4.0, 0.0, 2.5], lens: 28, dens: 0.5, ev: 0.35 },
  { p: [16.0, -22.0, 5.0], look: [1.5, 2.0, 2.4], lens: 28, dens: 0.7, ev: 0.35 },
  { p: [3.0, -20.0, 2.6], look: [0.5, 4.0, 2.4], lens: 28, dens: 0.9, ev: 0.35 },
  { p: [0.4, -12.0, 1.85], look: [0.3, 4.0, 2.4], lens: 26, dens: 1.1, ev: 0.35 },
  { p: [0.22, -5.0, 1.72], look: [0.2, 4.0, 1.95], lens: 26, dens: 1.6, ev: 0.35 },
  { p: [0.2, -1.0, 1.68], look: [0.2, 6.0, 1.9], lens: 24, dens: 2.6, ev: 0.4 },
  { p: [0.2, 2.2, 1.66], look: [0.1, 8.0, 2.4], lens: 22, dens: 3.2, ev: 0.7 },
  { p: [0.1, 4.6, 1.66], look: [-0.6, 10.0, 3.0], lens: 22, dens: 3.2, ev: 0.95, chapter: "arrival" },
  { p: [-0.4, 6.3, 1.64], look: [-4.5, 8.6, 2.5], lens: 22, dens: 3.0, ev: 0.9 },
  { p: [-2.3, 7.4, 1.62], look: [-12.0, 7.6, 2.0], lens: 22, dens: 2.6, ev: 0.55, chapter: "great" },
  { p: [-3.9, 7.0, 1.64], look: [-13.6, 6.6, 2.2], lens: 21, dens: 2.4, ev: 0.55 },
  // round the east and south side of the second sofa (x -7.05..-6.05, y 5.1..7.7), not over it
  { p: [-5.3, 5.7, 1.7], look: [-13.4, 3.4, 2.6], lens: 20, dens: 2.4, ev: 0.55 },
  { p: [-6.4, 4.3, 1.74], look: [-10.6, -1.2, 3.0], lens: 20, dens: 2.4, ev: 0.55 },
  { p: [-7.6, 3.6, 1.8], look: [-8.5, -6.0, 2.4], lens: 20, dens: 2.4, ev: 0.55 },
  { p: [-5.8, 3.7, 1.7], look: [0.0, 1.5, 2.0], lens: 21, dens: 2.4, ev: 0.6 },
  { p: [-4.4, 4.8, 1.68], look: [3.0, 4.4, 1.8], lens: 22, dens: 2.6, ev: 0.7 },
  { p: [-3.15, 4.8, 1.66], look: [4.0, 4.4, 1.7], lens: 22, dens: 2.8, ev: 0.8 },
  // across the hall to the foot of the stair, and up the sixteen treads
  { p: [-0.4, 4.75, 1.66], look: [3.2, 7.4, 2.5], lens: 22, dens: 1.6, ev: 0.8 },
  { p: [1.85, 5.0, 1.7], look: [2.15, 9.5, 3.7], lens: 22, dens: 1.2, ev: 0.85 },
  { p: [2.1, 6.6, 2.66], look: [2.1, 10.6, 4.4], lens: 22, dens: 1.1, ev: 0.85 },
  { p: [2.1, 8.4, 4.01], look: [2.0, 12.4, 5.3], lens: 22, dens: 1.1, ev: 0.85 },
  { p: [2.05, 10.15, 5.32], look: [3.8, 12.6, 5.35], lens: 22, dens: 1.1, ev: 0.85 },
  // the landing, then through the doorway into the gallery: walnut to the right, forest to the left
  { p: [2.05, 11.3, 5.33], look: [8.0, 11.85, 5.2], lens: 22, dens: 1.3, ev: 0.9 },
  { p: [3.5, 11.78, 5.33], look: [16.0, 11.85, 5.0], lens: 22, dens: 1.8, ev: 0.9, chapter: "gallery" },
  { p: [5.5, 11.8, 5.33], look: [13.5, 11.4, 5.0], lens: 22, dens: 1.5, ev: 0.9 },
  // the west suite: right through its doorway and down the walnut dressing passage
  { p: [7.05, 11.3, 5.33], look: [7.4, 5.5, 4.9], lens: 22, dens: 1.1, ev: 0.9 },
  { p: [7.35, 9.4, 5.33], look: [7.0, 4.0, 4.95], lens: 22, dens: 1.1, ev: 0.9 },
  // the room opens with the bed to the right; keep it in view, then pan left to the lake and hold
  { p: [7.3, 5.0, 5.33], look: [4.0, 2.6, 4.45], lens: 22, dens: 1.4, ev: 0.9, chapter: "west" },
  { p: [6.5, 1.2, 5.32], look: [3.6, 4.2, 4.4], lens: 22, dens: 1.6, ev: 0.9 },
  // (far enough back, ~2.7 m, that the sill, the head of the window and the sheers frame the lake)
  { p: [5.65, 1.1, 5.32], look: [5.0, -12.0, 4.3], lens: 24, dens: 1.6, ev: 0.9 },
  { p: [5.8, 0.65, 5.32], look: [5.9, -12.0, 4.25], lens: 24, dens: 2.0, ev: 0.9 },
  // turn back by the painting on the east wall, out through the passage, right along the gallery
  { p: [6.35, 0.55, 5.32], look: [9.0, 1.2, 4.85], lens: 22, dens: 0.9, ev: 0.9 },
  { p: [7.35, 4.4, 5.33], look: [7.45, 9.0, 5.2], lens: 22, dens: 0.7, ev: 0.9 },
  { p: [7.35, 8.8, 5.33], look: [7.6, 12.5, 5.2], lens: 22, dens: 0.7, ev: 0.9 },
  { p: [7.4, 10.95, 5.33], look: [12.0, 12.2, 5.15], lens: 22, dens: 0.7, ev: 0.9 },
  { p: [9.2, 11.8, 5.33], look: [16.0, 11.6, 5.05], lens: 22, dens: 0.8, ev: 0.9 },
  // the bunk room: in at its doorway and down the lobby beside the shower room
  { p: [11.35, 11.4, 5.33], look: [11.75, 6.0, 5.0], lens: 22, dens: 1.0, ev: 0.9 },
  { p: [11.62, 9.8, 5.33], look: [11.3, 4.0, 5.0], lens: 22, dens: 1.1, ev: 0.9 },
  // the room opens to the right: four bunks in limed oak, paper lanterns, the lake at the end
  { p: [11.7, 6.6, 5.33], look: [9.0, 3.3, 4.85], lens: 22, dens: 1.5, ev: 0.95, chapter: "bunk" },
  { p: [11.75, 3.6, 5.33], look: [8.9, 2.4, 4.9], lens: 21, dens: 1.6, ev: 0.95 },
  // to the window seat, then turn round past the bunks to look back up the length of the room
  { p: [11.45, 0.7, 5.33], look: [9.9, -8.0, 4.4], lens: 24, dens: 1.6, ev: 0.95 },
  { p: [11.05, 0.05, 5.33], look: [8.0, 1.6, 4.8], lens: 22, dens: 1.3, ev: 0.95 },
  { p: [10.95, -0.25, 5.33], look: [9.7, 6.6, 5.15], lens: 21, dens: 1.8, ev: 0.95 },
  // out again along the east side, and on along the gallery
  { p: [11.75, 3.4, 5.33], look: [11.7, 9.0, 5.2], lens: 22, dens: 0.7, ev: 0.9 },
  { p: [11.65, 8.4, 5.33], look: [11.5, 12.5, 5.2], lens: 22, dens: 0.7, ev: 0.9 },
  { p: [11.75, 10.95, 5.33], look: [17.0, 12.0, 5.1], lens: 22, dens: 0.7, ev: 0.9 },
  // the principal suite: through the pair of doors into the dressing room, behind the travertine wall
  { p: [13.6, 11.75, 5.33], look: [16.5, 9.0, 5.05], lens: 22, dens: 0.8, ev: 0.9 },
  { p: [15.3, 10.9, 5.33], look: [16.2, 6.0, 5.0], lens: 22, dens: 1.0, ev: 0.9 },
  { p: [15.55, 9.4, 5.33], look: [18.4, 6.3, 4.9], lens: 22, dens: 1.1, ev: 0.9 },
  { p: [16.7, 7.3, 5.33], look: [19.7, 4.6, 5.0], lens: 22, dens: 1.1, ev: 0.9 },
  // round the east end of the wall: the room revealed, the lake and the sitting corner, wide
  { p: [18.85, 5.7, 5.33], look: [19.4, 1.0, 4.8], lens: 22, dens: 1.1, ev: 0.9 },
  { p: [19.45, 4.1, 5.33], look: [16.8, -3.5, 4.4], lens: 20, dens: 1.8, ev: 0.9, chapter: "principal" },
  { p: [18.7, 2.5, 5.33], look: [15.4, 4.0, 4.6], lens: 22, dens: 1.5, ev: 0.9 },
  // the bed from its foot, square on: the travertine wall, the pendants, the cove-lit coffer
  { p: [16.5, -0.55, 5.33], look: [16.5, 4.6, 4.6], lens: 26, dens: 1.8, ev: 0.9 },
  { p: [16.45, -0.3, 5.33], look: [16.45, 4.6, 4.6], lens: 26, dens: 2.1, ev: 0.9 },
  // out round the west end of the wall and back through the dressing room to the doors
  { p: [14.15, 0.95, 5.33], look: [13.4, 6.0, 5.0], lens: 22, dens: 1.0, ev: 0.9 },
  { p: [13.5, 3.7, 5.33], look: [13.6, 9.0, 5.1], lens: 22, dens: 0.8, ev: 0.9 },
  { p: [13.6, 5.9, 5.33], look: [16.0, 9.2, 5.05], lens: 22, dens: 0.8, ev: 0.9 },
  { p: [14.75, 8.1, 5.33], look: [15.6, 12.2, 5.1], lens: 22, dens: 0.8, ev: 0.9 },
  { p: [15.35, 10.6, 5.33], look: [10.0, 11.8, 5.05], lens: 22, dens: 0.7, ev: 0.9 },
  // the length of the gallery back to the landing, the hall's chandelier through the doorway
  { p: [13.2, 11.75, 5.33], look: [2.0, 11.4, 4.9], lens: 22, dens: 0.7, ev: 0.9 },
  { p: [7.5, 11.8, 5.33], look: [-1.5, 10.8, 4.8], lens: 22, dens: 0.7, ev: 0.9 },
  { p: [4.2, 11.7, 5.33], look: [-1.5, 10.6, 4.8], lens: 22, dens: 0.8, ev: 0.9 },
  // down the stair facing the pivot door, then left through the open bay into the kitchen
  { p: [2.2, 11.25, 5.33], look: [1.8, 6.0, 4.0], lens: 22, dens: 0.9, ev: 0.85 },
  { p: [2.12, 10.15, 5.32], look: [2.05, 4.0, 3.0], lens: 22, dens: 1.0, ev: 0.85 },
  { p: [2.1, 7.6, 3.41], look: [2.3, 2.0, 1.9], lens: 22, dens: 1.1, ev: 0.85 },
  { p: [2.12, 5.95, 2.17], look: [5.0, 3.9, 1.7], lens: 22, dens: 1.3, ev: 0.9 },
  { p: [2.35, 4.85, 1.68], look: [7.5, 4.4, 1.55], lens: 22, dens: 1.8, ev: 0.95 },
  { p: [2.85, 4.3, 1.64], look: [8.0, 4.6, 1.5], lens: 22, dens: 2.8, ev: 0.95 },
  { p: [4.4, 4.4, 1.62], look: [8.6, 9.4, 1.1], lens: 22, dens: 2.6, ev: 1.0, chapter: "kitchen" },
  { p: [6.0, 4.9, 1.64], look: [9.6, 9.8, 1.15], lens: 22, dens: 2.4, ev: 1.0 },
  { p: [7.8, 5.3, 1.66], look: [11.6, 10.0, 1.3], lens: 22, dens: 2.4, ev: 1.0 },
  { p: [10.2, 5.4, 1.7], look: [13.8, 9.6, 1.5], lens: 22, dens: 2.4, ev: 1.0 },
  { p: [12.6, 4.5, 1.66], look: [17.0, 7.0, 1.6], lens: 22, dens: 2.6, ev: 0.95 },
  { p: [14.1, 4.3, 1.64], look: [17.5, 8.0, 1.6], lens: 22, dens: 2.8, ev: 0.9 },
  { p: [15.2, 4.9, 1.62], look: [16.9, 12.6, 1.6], lens: 22, dens: 2.6, ev: 0.85, chapter: "study" },
  { p: [15.9, 6.8, 1.52], look: [16.6, 12.4, 1.35], lens: 24, dens: 2.4, ev: 0.85 },
  { p: [16.4, 8.7, 1.36], look: [16.47, 11.2, 0.95], lens: 28, dens: 2.6, ev: 0.85 },
  { p: [16.45, 9.9, 1.12], look: [16.45, 10.92, 0.89], lens: 34, dens: 3.6, ev: 0.85 },
  { p: [16.45, 10.42, 0.95], look: [16.45, 10.917, 0.887], lens: 40, dens: 4.4, ev: 0.85 },
  // close enough that the screen fills the frame: the drawing set takes over from here
  { p: [16.45, 10.68, 0.915], look: [16.45, 10.917, 0.887], lens: 40, dens: 4.8, ev: 0.85 },
];

/** Blender's camera: 36 mm sensor, horizontal fit. */
export const SENSOR = 36;
/** Scroll weight of turning, in metres per radian at density 1 (pans take scroll time too). */
const ROT = 1.8;
const SAMPLES = 8000;

export type Pose = {
  /** Blender coordinates */
  x: number;
  y: number;
  z: number;
  yaw: number;
  pitch: number;
  lens: number;
  ev: number;
  /** position along the keys, 0..KEYS.length-1 */
  u: number;
};

/** Uniform Catmull-Rom on scalars, matching CatmullRomCurve3's segment indexing. */
function scalarAt(v: number[], t: number) {
  const n = v.length;
  const p = (n - 1) * Math.min(1, Math.max(0, t));
  let i = Math.floor(p);
  let w = p - i;
  if (i >= n - 1) {
    i = n - 2;
    w = 1;
  }
  const p1 = v[i];
  const p2 = v[i + 1];
  const p0 = i > 0 ? v[i - 1] : 2 * p1 - p2;
  const p3 = i + 2 < n ? v[i + 2] : 2 * p2 - p1;
  const w2 = w * w;
  const w3 = w2 * w;
  return 0.5 * (2 * p1 + (-p0 + p2) * w + (2 * p0 - 5 * p1 + 4 * p2 - p3) * w2 + (-p0 + 3 * p1 - 3 * p2 + p3) * w3);
}

export class CameraPath {
  readonly keys: Key[];
  private curve: CatmullRomCurve3;
  private yaw: number[];
  private pitch: number[];
  private lens: number[];
  private ev: number[];
  private ts = new Float64Array(SAMPLES + 1);
  private ss = new Float64Array(SAMPLES + 1);
  private tmp = new Vector3();

  constructor(keys: Key[] = KEYS) {
    this.keys = keys;
    this.curve = new CatmullRomCurve3(
      keys.map((k) => new Vector3(...k.p)),
      false,
      "centripetal",
    );
    this.lens = keys.map((k) => k.lens);
    this.ev = keys.map((k) => k.ev);
    this.yaw = [];
    this.pitch = [];
    keys.forEach((k, i) => {
      const dx = k.look[0] - k.p[0];
      const dy = k.look[1] - k.p[1];
      const dz = k.look[2] - k.p[2];
      let a = Math.atan2(dy, dx);
      if (i > 0) {
        const prev = this.yaw[i - 1];
        while (a - prev > Math.PI) a -= 2 * Math.PI;
        while (a - prev < -Math.PI) a += 2 * Math.PI;
      }
      this.yaw.push(a);
      this.pitch.push(Math.atan2(dz, Math.hypot(dx, dy)));
    });
    // distance along the take, weighted by density and by how much the camera turns
    const dens = keys.map((k) => k.dens);
    const prev = new Vector3();
    const cur = new Vector3();
    this.curve.getPoint(0, prev);
    let lastYaw = this.yaw[0];
    let lastPitch = this.pitch[0];
    for (let k = 1; k <= SAMPLES; k++) {
      const t = k / SAMPLES;
      this.curve.getPoint(t, cur);
      const yw = scalarAt(this.yaw, t);
      const pt = scalarAt(this.pitch, t);
      const d = cur.distanceTo(prev) + ROT * (Math.abs(yw - lastYaw) * Math.cos(pt) + Math.abs(pt - lastPitch));
      this.ts[k] = t;
      this.ss[k] = this.ss[k - 1] + d * scalarAt(dens, t);
      prev.copy(cur);
      lastYaw = yw;
      lastPitch = pt;
    }
  }

  /** Total weighted length (the scroll budget is proportional to this). */
  get length() {
    return this.ss[SAMPLES];
  }

  /** Curve parameter for scroll progress q in [0,1]. */
  tAt(q: number) {
    const s = Math.min(1, Math.max(0, q)) * this.ss[SAMPLES];
    let lo = 0;
    let hi = SAMPLES;
    while (hi - lo > 1) {
      const mid = (lo + hi) >> 1;
      if (this.ss[mid] < s) lo = mid;
      else hi = mid;
    }
    const span = this.ss[hi] - this.ss[lo];
    const f = span > 0 ? (s - this.ss[lo]) / span : 0;
    return this.ts[lo] + f * (this.ts[hi] - this.ts[lo]);
  }

  /** Scroll progress at which the camera reaches key i (fractional i: between keys). */
  qOfKey(i: number) {
    const k = Math.round((i / (this.keys.length - 1)) * SAMPLES);
    return this.ss[k] / this.ss[SAMPLES];
  }

  at(q: number, out: Pose): Pose {
    const t = this.tAt(q);
    this.curve.getPoint(t, this.tmp);
    out.x = this.tmp.x;
    out.y = this.tmp.y;
    out.z = this.tmp.z;
    out.yaw = scalarAt(this.yaw, t);
    out.pitch = scalarAt(this.pitch, t);
    out.lens = scalarAt(this.lens, t);
    out.ev = scalarAt(this.ev, t);
    out.u = t * (this.keys.length - 1);
    return out;
  }
}

export const newPose = (): Pose => ({ x: 0, y: 0, z: 0, yaw: 0, pitch: 0, lens: 22, ev: 0, u: 0 });
