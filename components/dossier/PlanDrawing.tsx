"use client";

import { useState } from "react";
import plan from "@/lib/plan.json";

type Plan = {
  bounds: [number, number, number, number];
  cut: [number, number, number, number, number][];
  glass: [number, number, number, number][];
  furniture: [number, number][][];
  site: [number, number, number, number][];
  pool: [number, number, number, number];
  rooms: { id: string; name: string; area: string; rect: [number, number, number, number] }[];
  dock: [number, number, number, number];
  wall: [number, number, number, number];
};

const P = plan as unknown as Plan;

/** Label anchors (world metres) placed on open floor, clear of furniture. */
const LABEL_AT: Record<string, [number, number]> = {
  great: [-9.0, 11.6],
  arrival: [-0.6, 4.4],
  kitchen: [8.5, 5.5],
  study: [16.3, 6.4],
};

/** Ground-floor plan drawn from the model's cut at 1.1 m. Rooms are selectable. */
export default function PlanDrawing({ onSelect }: { onSelect?: (id: string) => void }) {
  const [hover, setHover] = useState<string | null>(null);
  const [x0, y0, w, h] = P.bounds;
  const vb = `${x0} ${-(y0 + h)} ${w} ${h}`;
  const rect = (r: number[]) => ({ x: r[0], y: -(r[1] + r[3]), width: r[2], height: r[3] });
  const current = P.rooms.find((r) => r.id === hover);

  return (
    <figure className="relative h-full w-full">
      <svg viewBox={vb} className="h-full w-full" role="group" aria-label="Ground floor plan">
        <g fill="#d8d0c2" fillOpacity={0.45} stroke="#0d1820" strokeWidth={0.04}>
          {P.site.map((r, i) => (
            <rect key={i} {...rect(r)} />
          ))}
        </g>
        <rect {...rect(P.pool)} fill="#9aabbb" fillOpacity={0.55} stroke="#0d1820" strokeWidth={0.05} />
        <rect {...rect(P.wall)} fill="#3f2c21" fillOpacity={0.85} />
        <rect {...rect(P.dock)} fill="none" stroke="#0d1820" strokeWidth={0.04} strokeDasharray="0.3 0.2" />
        {P.rooms.map((r) => (
          <rect
            key={r.id}
            {...rect(r.rect)}
            tabIndex={0}
            role="button"
            aria-label={`${r.name}, ${r.area}. Walk to this room.`}
            className="cursor-pointer outline-none transition-[fill-opacity] duration-300"
            fill="#e9b67c"
            fillOpacity={hover === r.id ? 0.32 : 0}
            onMouseEnter={() => setHover(r.id)}
            onMouseLeave={() => setHover(null)}
            onFocus={() => setHover(r.id)}
            onBlur={() => setHover(null)}
            onClick={() => onSelect?.(r.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelect?.(r.id);
              }
            }}
          />
        ))}
        <g fill="none" stroke="#0d1820" strokeOpacity={0.55} strokeWidth={0.025} pointerEvents="none">
          {P.furniture.map((poly, i) => (
            <polygon key={i} points={poly.map(([x, y]) => `${x},${-y}`).join(" ")} />
          ))}
        </g>
        <g stroke="#5e7286" strokeWidth={0.06} pointerEvents="none">
          {P.glass.map((g, i) => (
            <line key={i} x1={g[0]} y1={-g[1]} x2={g[2]} y2={-g[3]} />
          ))}
        </g>
        <g pointerEvents="none">
          {P.cut.map((c, i) => (
            <rect key={i} x={c[0]} y={-(c[1] + c[3])} width={c[2]} height={c[3]} fill={c[4] ? "#3f2c21" : "#0d1820"} />
          ))}
        </g>
        <g pointerEvents="none" className="font-semi" fontSize={0.62} fill="#0d1820">
          {P.rooms.map((r) => (
            <text key={r.id} x={(LABEL_AT[r.id] ?? [r.rect[0] + r.rect[2] / 2])[0]} y={-(LABEL_AT[r.id]?.[1] ?? r.rect[1] + r.rect[3] / 2)} textAnchor="middle">
              {r.name}
              <tspan x={(LABEL_AT[r.id] ?? [r.rect[0] + r.rect[2] / 2])[0]} dy={0.85} fontSize={0.5} fill="#5e7286">
                {r.area}
              </tspan>
            </text>
          ))}
        </g>
        <g transform={`translate(${x0 + w - 2.2} ${-(y0 + h) + 2.2})`} stroke="#0d1820" strokeWidth={0.05} fill="none">
          <circle r={1.1} />
          <path d="M0 -0.95 L0.35 0.6 L0 0.28 L-0.35 0.6 Z" fill="#0d1820" />
        </g>
      </svg>
      <figcaption className="sr-only">Ground floor plan. Select a room to walk to it.</figcaption>
      <p
        aria-live="polite"
        className={`pointer-events-none absolute left-0 top-0 text-[0.95rem] leading-snug text-walnut transition-opacity duration-300 ${current ? "opacity-100" : "opacity-0"}`}
      >
        {current ? (
          <>
            <span className="font-semi text-ink">{current.name}</span>, {current.area}. Select to walk here.
          </>
        ) : (
          " "
        )}
      </p>
    </figure>
  );
}
