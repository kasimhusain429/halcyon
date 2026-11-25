// Sample the walkthrough camera exactly as the browser does (CameraPath.at) for check_route.py.
//
//   node blender/route_samples.mjs            -> blender/rt/route_samples.json
//
// Needs Node 23.6+ (it loads components/walkthrough/path.ts directly).
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { CameraPath, newPose } from "../components/walkthrough/path.ts";

const here = dirname(fileURLToPath(import.meta.url));
const out = process.argv[2] ?? join(here, "rt", "route_samples.json");
const N = 24000;
const path = new CameraPath();
const pose = newPose();
const pts = [];
for (let i = 0; i <= N; i++) {
  const p = path.at(i / N, pose);
  pts.push([+p.x.toFixed(4), +p.y.toFixed(4), +p.z.toFixed(4), +p.u.toFixed(3)]);
}
const keys = path.keys.map((k, i) => ({ i, p: k.p, chapter: k.chapter ?? null }));
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, JSON.stringify({ length: path.length, keys, pts }));
console.log(`${pts.length} samples along ${path.length.toFixed(1)} units -> ${out}`);
