import { RESIDENCE } from "@/lib/residence";
import { SHEETS } from "@/lib/drawings";

/**
 * Cover sheet of the drawing set. Rendered twice: `compact` at a fixed 1440px
 * artboard (it is also the texture on the study laptop, so the zoom lands on it
 * pixel-for-pixel), and responsive for the full-screen hand-off.
 */
export default function DossierCover({ compact = false }: { compact?: boolean }) {
  const block = [
    { k: "Project", v: "Halcyon Residence" },
    { k: "Location", v: `${RESIDENCE.place}, ${RESIDENCE.elevation}` },
    { k: "Issue", v: "For private viewing" },
    { k: "Date", v: "23 November 2026" },
    { k: "Sheets", v: `${SHEETS[0].code} to ${SHEETS[SHEETS.length - 1].code}` },
  ];
  return (
    <div className={`relative flex h-full w-full flex-col bg-vellum text-ink ${compact ? "p-[34px]" : "p-[clamp(14px,2.4vw,34px)] pt-[clamp(64px,7vw,88px)]"}`}>
      <div className="relative flex h-full w-full flex-col border border-ink/70">
        <div className={`grid flex-1 ${compact ? "grid-cols-[1.05fr_1fr]" : "grid-cols-1 md:grid-cols-[1.05fr_1fr]"}`}>
          <div className={`flex flex-col justify-between ${compact ? "p-[44px]" : "p-[clamp(18px,3.2vw,44px)]"}`}>
            <div>
              <p className={`font-semi text-slate ${compact ? "text-[19px]" : "text-[clamp(0.8rem,1.3vw,1.2rem)]"}`}>Drawing set</p>
              <h2
                className={`font-wide mt-3 font-semibold leading-[0.9] tracking-[-0.01em] ${
                  compact ? "text-[132px]" : "text-[clamp(3rem,9vw,8.25rem)]"
                }`}
              >
                Halcyon
              </h2>
              <p className={`mt-5 max-w-[24ch] leading-snug text-walnut ${compact ? "text-[30px]" : "text-[clamp(1.15rem,2vw,1.9rem)]"}`}>
                Residence on the north shore of {RESIDENCE.place}
              </p>
            </div>
            <ol className={`grid gap-y-2 ${compact ? "mt-10 text-[19px]" : "mt-8 text-[clamp(0.85rem,1.2vw,1.1rem)]"}`}>
              {SHEETS.map((s) => (
                <li key={s.code} className="flex items-baseline gap-4 border-b border-ink/15 pb-2">
                  <span className="font-semi tabular w-[4.5em] shrink-0 text-slate">{s.code}</span>
                  <span>{s.title}</span>
                </li>
              ))}
            </ol>
          </div>
          <div className={`relative ${compact ? "block" : "hidden md:block"} border-l border-ink/20`}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/drawings/axonometric.png" alt="Axonometric drawing of Halcyon" className="absolute inset-0 m-auto h-[88%] w-[92%] object-contain" />
          </div>
        </div>
        <dl className={`grid grid-cols-2 border-t border-ink/70 ${compact ? "grid-cols-5" : "md:grid-cols-5"}`}>
          {block.map((b, i) => (
            <div
              key={b.k}
              className={`${i > 0 ? "border-l" : ""} border-ink/30 ${compact ? "px-5 py-3" : "px-[clamp(10px,1.4vw,20px)] py-[clamp(6px,0.9vw,12px)]"}`}
            >
              <dt className={`font-semi text-slate ${compact ? "text-[14px]" : "text-[0.68rem]"}`}>{b.k}</dt>
              <dd className={`mt-0.5 ${compact ? "text-[19px]" : "text-[clamp(0.85rem,1.1vw,1.05rem)]"}`}>{b.v}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}
