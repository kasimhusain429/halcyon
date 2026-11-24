import AvailableStills from "./stills/AvailableStills";
import type { Still } from "./stills/StillsStrip";

export const STILLS: Still[] = [
  { src: "/stills/dusk.webp", room: "From the lake", note: "The gable lit at dusk, late September.", width: 1920, height: 1080 },
  { src: "/stills/aerial.webp", room: "From above", note: "Pool, terraces and the cedar dock on their limestone plinth.", width: 1920, height: 1080 },
  { src: "/stills/arrival.webp", room: "Arrival hall", note: "The great room seen from the foot of the stair.", width: 1920, height: 1080 },
  { src: "/stills/great.webp", room: "Great room", note: "The hearth wall in honed limestone, oak trusses overhead.", width: 1920, height: 1080 },
  { src: "/stills/kitchen.webp", room: "Kitchen", note: "Calacatta island, walnut joinery, the library beyond the glass.", width: 1920, height: 1080 },
  { src: "/stills/study.webp", room: "Study", note: "Eleven metres of walnut shelving and one window north.", width: 1920, height: 1080 },
];

/** Full-resolution stills from the same model as the walkthrough. */
export default function Stills() {
  return (
    <section id="stills" data-theme="dark" aria-labelledby="stills-title" className="bg-ink py-[clamp(72px,10vw,160px)]">
      <div className="px-[var(--gutter)]">
        <h2 id="stills-title" className="font-wide text-[clamp(2rem,4.4vw,4rem)] font-medium leading-none text-[#efe9de]">
          Stills
        </h2>
        <p className="mt-4 max-w-[44ch] text-[1.05rem] leading-relaxed text-haze">
          Rendered at full resolution from the same model as the walkthrough. Select a still to see it larger.
        </p>
      </div>
      <div className="mt-[clamp(20px,3vw,40px)]">
        <AvailableStills stills={STILLS} />
      </div>
    </section>
  );
}
