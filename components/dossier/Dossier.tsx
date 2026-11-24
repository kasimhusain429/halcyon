"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SHEETS, MATERIALS, type Sheet } from "@/lib/drawings";
import PlanDrawing from "./PlanDrawing";
import SectionDrawing from "./SectionDrawing";

gsap.registerPlugin(ScrollTrigger);

function walkTo(id: string) {
  window.dispatchEvent(new CustomEvent("halcyon:walk", { detail: id }));
}

function Drawing({ sheet }: { sheet: Sheet }) {
  switch (sheet.drawing) {
    case "site":
      // eslint-disable-next-line @next/next/no-img-element
      return <img src="/drawings/site.svg" alt="Site plan: the house on the north shore, contours at two metres" className="h-full w-full object-contain" />;
    case "axonometric":
      // eslint-disable-next-line @next/next/no-img-element
      return <img src="/drawings/axonometric.png" alt="Axonometric drawing of the three volumes on their plinth" className="h-full w-full object-contain" />;
    case "plan":
      return <PlanDrawing onSelect={walkTo} />;
    case "section":
      return <SectionDrawing cut="ew" />;
    case "environment":
      return <SectionDrawing cut="ns" sun />;
    case "materials":
      return (
        <ul className="grid h-full grid-cols-2 content-center gap-x-[clamp(12px,2vw,28px)] gap-y-[clamp(14px,2.2vw,30px)] sm:grid-cols-4">
          {MATERIALS.map((m) => (
            <li key={m.id} className="flex flex-col">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={`/drawings/materials/${m.id}.webp`} alt="" className="aspect-square w-full object-contain" loading="lazy" />
              <span className="font-semi mt-2 text-[0.82rem] text-ink">{m.name}</span>
              <span className="text-[0.85rem] text-slate">{m.use}</span>
            </li>
          ))}
        </ul>
      );
  }
}

function SheetCard({ sheet, index }: { sheet: Sheet; index: number }) {
  return (
    <article
      data-sheet
      aria-labelledby={`sheet-${sheet.code}`}
      className="sheet relative flex w-full shrink-0 flex-col bg-vellum text-ink lg:h-full lg:w-[min(90vw,1560px)] lg:even:bg-[#dccfba]"
    >
      <div className="sheet-frame m-[clamp(10px,1.6vw,22px)] flex min-h-0 flex-1 flex-col border border-ink/70 lg:flex-row">
        <div className="flex flex-col justify-between gap-8 p-[clamp(18px,2.6vw,40px)] lg:w-[34%] lg:border-r lg:border-ink/25">
          <div>
            <h3 id={`sheet-${sheet.code}`} className="font-wide text-[clamp(1.9rem,3.2vw,3.1rem)] font-medium leading-[0.98] tracking-[-0.01em]">
              {sheet.title}
            </h3>
            <div className="mt-6 max-w-[46ch] space-y-4 text-[clamp(1rem,1.15vw,1.12rem)] leading-[1.6] text-walnut">
              {sheet.body.map((p) => (
                <p key={p.slice(0, 24)}>{p}</p>
              ))}
            </div>
          </div>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-4 border-t border-ink/25 pt-5">
            {sheet.facts.map((f) => (
              <div key={f.term}>
                <dt className="font-semi text-[0.72rem] text-slate">{f.term}</dt>
                <dd className="tabular mt-1 text-[1.05rem]">{f.value}</dd>
              </div>
            ))}
          </dl>
        </div>
        <div className="relative flex min-h-0 flex-1 flex-col">
          <div className="relative h-[min(72vw,520px)] lg:h-auto lg:min-h-0 lg:flex-1">
            <div className="absolute inset-0 p-[clamp(16px,2.4vw,40px)]">
              <Drawing sheet={sheet} />
            </div>
          </div>
          {/* title block: the drawing set is a numbered sequence */}
          <div className="grid grid-cols-[auto_1fr_auto] items-stretch border-t border-ink/70 text-[0.8rem]">
            <div className="border-r border-ink/40 px-4 py-2.5">
              <span className="font-semi block text-[0.66rem] text-slate">Sheet</span>
              <span className="font-wide tabular text-[1.05rem] font-semibold">{sheet.code}</span>
            </div>
            <div className="min-w-0 px-4 py-2.5">
              <span className="font-semi block truncate text-[0.66rem] text-slate">Halcyon Residence, Lake Serein</span>
              <span className="text-[0.95rem]">{sheet.title}</span>
            </div>
            <div className="border-l border-ink/40 px-4 py-2.5 text-right">
              <span className="font-semi block text-[0.66rem] text-slate">Scale</span>
              <span className="tabular text-[0.95rem]">{sheet.scale}</span>
            </div>
          </div>
        </div>
      </div>
      <span className="sr-only">
        Sheet {index + 1} of {SHEETS.length}
      </span>
    </article>
  );
}

/** The drawing set: a horizontal run of sheets on large screens, stacked on small ones. */
export default function Dossier() {
  const wrapRef = useRef<HTMLDivElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const mm = gsap.matchMedia();
    mm.add("(min-width: 1024px)", () => {
      const track = trackRef.current!;
      const wrap = wrapRef.current!;
      const dist = () => track.scrollWidth - window.innerWidth;
      const tween = gsap.to(track, {
        x: () => -dist(),
        ease: "none",
        scrollTrigger: {
          trigger: wrap,
          start: "top top",
          end: () => `+=${dist()}`,
          pin: true,
          scrub: 0.5,
          invalidateOnRefresh: true,
        },
      });
      return () => tween.kill();
    });
    return () => mm.revert();
  }, []);

  return (
    <section id="drawings" data-theme="light" aria-label="Drawing set" className="relative bg-[#cfd5d6]">
      <div ref={wrapRef} className="lg:h-svh lg:overflow-hidden">
        <div ref={trackRef} className="flex flex-col gap-[clamp(10px,1.4vw,18px)] p-[clamp(10px,1.4vw,18px)] pt-[72px] lg:h-full lg:w-max lg:flex-row lg:gap-0 lg:pt-[68px]">
          {SHEETS.map((s, i) => (
            <SheetCard key={s.code} sheet={s} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
