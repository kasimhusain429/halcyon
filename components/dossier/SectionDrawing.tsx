import section from "@/lib/section.json";

type Loop = { pts: [number, number][]; glass: boolean; metal: boolean };
type Cut = { loops: Loop[]; water: number; bounds: [number, number, number, number] };
const DATA = section as unknown as Record<"ew" | "ns", Cut>;

/** A 1.8 m figure for scale. */
function Figure({ x, flip = false }: { x: number; flip?: boolean }) {
  return (
    <g transform={`translate(${x} 0) scale(${flip ? -1 : 1} 1)`} fill="none" stroke="#3f2c21" strokeWidth={0.035} strokeLinecap="round">
      <circle cx={0} cy={-1.66} r={0.12} />
      <path d="M0 -1.52 L0 -0.86 M0 -1.38 L-0.2 -1.0 M0 -1.38 L0.18 -1.02 M0 -0.86 L-0.14 0 M0 -0.86 L0.12 0" />
    </g>
  );
}

/** Noon sun ray grazing the cantilever edge (y −2.2 m, z 3.32 m) and where it lands. */
function SunRay({ deg, label, dashed }: { deg: number; label: string; dashed?: boolean }) {
  const a = (deg * Math.PI) / 180;
  const ex = -2.2;
  const ez = 3.32;
  const land = ex + ez / Math.tan(a);
  const len = 9;
  const sx = ex - Math.cos(a) * len;
  const sz = ez + Math.sin(a) * len;
  return (
    <g>
      <line x1={sx} y1={-sz} x2={land} y2={0} stroke="#e9b67c" strokeWidth={0.07} strokeDasharray={dashed ? "0.35 0.22" : undefined} />
      <circle cx={land} cy={0} r={0.14} fill="#e9b67c" />
      <text x={sx + 0.3} y={-sz + 0.2} fontSize={0.62} fill="#3f2c21" className="font-semi">
        {label}
      </text>
    </g>
  );
}

/**
 * Sections cut from the model: `ew` is the long section at y = 7 m,
 * `ns` is a cross-section through the kitchen and the bunk room above it at x = 9 m (lake to the left).
 */
export default function SectionDrawing({ cut = "ew", sun = false }: { cut?: "ew" | "ns"; sun?: boolean }) {
  const S = DATA[cut];
  const [x0, z0, w, h] = S.bounds;
  const vb = `${x0} ${-(z0 + h)} ${w} ${h}`;
  const poly = (pts: [number, number][]) => pts.map(([x, z]) => `${x},${-z}`).join(" ");
  return (
    <svg
      viewBox={vb}
      className="h-full w-full"
      role="img"
      aria-label={sun ? "Cross-section through the kitchen with summer and winter noon sun" : "Long section through the three volumes"}
    >
      <rect x={x0} y={-S.water} width={w} height={Math.max(0, S.water - z0)} fill="#9aabbb" fillOpacity={0.2} />
      <line x1={x0} x2={x0 + w} y1={-S.water} y2={-S.water} stroke="#5e7286" strokeWidth={0.04} />
      <g>
        {S.loops.map((l, i) => (
          <polygon
            key={i}
            points={poly(l.pts)}
            fill={l.glass ? "none" : l.metal ? "#3f2c21" : "#0d1820"}
            stroke={l.glass ? "#5e7286" : "#0d1820"}
            strokeWidth={l.glass ? 0.05 : 0.012}
          />
        ))}
      </g>
      {cut === "ew" ? (
        <>
          <Figure x={-9} />
          <Figure x={-1.2} flip />
          <Figure x={8.4} />
        </>
      ) : (
        <>
          <Figure x={-4.2} />
          <Figure x={6.0} flip />
        </>
      )}
      {sun && (
        <>
          <SunRay deg={66.9} label="Summer noon, 66.9°" />
          <SunRay deg={20.1} label="Winter noon, 20.1°" dashed />
        </>
      )}
    </svg>
  );
}
