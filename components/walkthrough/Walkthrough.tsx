"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import gsap from "gsap";
import { CHAPTERS, RESIDENCE } from "@/lib/residence";
import { scrollToY } from "@/lib/smooth";
import DossierCover from "@/components/dossier/DossierCover";
import { CameraPath } from "./path";
import type { FrameStats, RealtimeEngine } from "./engine";

/** Scroll length of the whole take, in screen heights. */
const SCREENS = 24;
/** The drawing set takes over from the laptop screen over this last stretch of the take. */
const HANDOFF: [number, number] = [0.972, 0.994];

type Timing = Record<string, { stop: number; win: [number, number] }>;

/** Where each chapter card shows (in scroll progress), from the chapter keys on the camera path. */
function chapterTiming(path: CameraPath): Timing {
  const at = path.keys.map((k, i) => ({ id: k.chapter, q: path.qOfKey(i) })).filter((c) => c.id) as { id: string; q: number }[];
  const out: Timing = {};
  at.forEach((c, i) => {
    const next = at[i + 1]?.q ?? HANDOFF[0];
    out[c.id] = { stop: c.q, win: [c.q + (i === 0 ? 0.03 : 0.004), Math.min(next - 0.01, c.q + 0.075)] };
  });
  return out;
}

const smooth = (e0: number, e1: number, x: number) => {
  const t = Math.min(1, Math.max(0, (x - e0) / (e1 - e0)));
  return t * t * (3 - 2 * t);
};

/**
 * The walk through the house, drawn live in 3D: one continuous camera take from the lake to
 * the study, driven by scroll. The section is SCREENS screens tall; the canvas stays pinned
 * while the page scrolls through it. Lenis, the 3D frame and the overlays all run on the
 * same GSAP tick, so every frame shows exactly the scroll position of that frame.
 */
export default function Walkthrough() {
  const sectionRef = useRef<HTMLElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fontProbeRef = useRef<HTMLSpanElement>(null);
  const loaderRef = useRef<HTMLDivElement>(null);
  const loaderBarRef = useRef<HTMLDivElement>(null);
  const progressRef = useRef<HTMLDivElement>(null);
  const routeRef = useRef<HTMLElement>(null);
  const heroRef = useRef<HTMLDivElement>(null);
  const coverRef = useRef<HTMLDivElement>(null);
  const hudRef = useRef<HTMLPreElement>(null);
  const cardRefs = useRef<(HTMLElement | null)[]>([]);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [active, setActive] = useState(0);

  const path = useMemo(() => new CameraPath(), []);
  const timing = useMemo(() => chapterTiming(path), [path]);
  const stops = useMemo(
    () => CHAPTERS.map((c) => ({ label: c.stop, q: timing[c.id]?.stop ?? 0 })).concat([{ label: "Drawings", q: (HANDOFF[0] + HANDOFF[1]) / 2 }]),
    [timing],
  );

  const jump = (q: number) => {
    const s = sectionRef.current;
    if (!s) return;
    const top = s.getBoundingClientRect().top + window.scrollY;
    scrollToY(top + q * (s.offsetHeight - window.innerHeight) + 2);
  };

  useEffect(() => {
    const section = sectionRef.current!;
    let engine: RealtimeEngine | null = null;
    let disposed = false;
    let lastActive = -1;
    let hudAt = 0;
    const showHud = new URLSearchParams(window.location.search).has("hud");
    if (showHud) hudRef.current?.classList.remove("hidden");

    const progressOf = () => {
      const r = section.getBoundingClientRect();
      return { q: Math.min(1, Math.max(0, -r.top / Math.max(1, section.offsetHeight - window.innerHeight))), visible: r.bottom > 0 && r.top < window.innerHeight };
    };

    const overlays = (q: number) => {
      if (heroRef.current) {
        const o = 1 - smooth(0.002, 0.018, q);
        heroRef.current.style.opacity = o.toFixed(3);
        heroRef.current.style.transform = `translate3d(0, ${(-12 * (1 - o)).toFixed(1)}px, 0)`;
        heroRef.current.style.visibility = o > 0.001 ? "visible" : "hidden";
      }
      CHAPTERS.forEach((c, i) => {
        const el = cardRefs.current[i];
        const t = timing[c.id];
        if (!el || !t) return;
        const [a, b] = t.win;
        const inA = smooth(a, a + 0.006, q);
        const outA = smooth(b - 0.005, b, q);
        const o = inA * (1 - outA);
        el.style.opacity = o.toFixed(3);
        el.style.visibility = o > 0.001 ? "visible" : "hidden";
        el.style.transform = `translate3d(0, ${(-18 * outA).toFixed(1)}px, 0)`;
        const line = el.querySelector<HTMLElement>("[data-line]");
        if (line) line.style.transform = `translate3d(0, ${(105 * (1 - smooth(a, a + 0.009, q))).toFixed(1)}%, 0)`;
        el.querySelectorAll<HTMLElement>("[data-fade]").forEach((f, k) => {
          const fo = smooth(a + 0.003 + k * 0.0015, a + 0.009 + k * 0.0015, q);
          f.style.opacity = fo.toFixed(3);
          f.style.transform = `translate3d(0, ${(14 * (1 - fo)).toFixed(1)}px, 0)`;
        });
      });
      if (routeRef.current) {
        const o = smooth(0.03, 0.045, q) * (1 - smooth(HANDOFF[0] - 0.02, HANDOFF[0], q));
        routeRef.current.style.opacity = o.toFixed(3);
        routeRef.current.style.visibility = o > 0.001 ? "visible" : "hidden";
      }
      if (progressRef.current) progressRef.current.style.transform = `scaleX(${q.toFixed(4)})`;
      if (coverRef.current) {
        const o = smooth(HANDOFF[0], HANDOFF[1], q);
        coverRef.current.style.opacity = o.toFixed(3);
        coverRef.current.style.visibility = o > 0.001 ? "visible" : "hidden";
      }
      section.dataset.theme = q > (HANDOFF[0] + HANDOFF[1]) / 2 ? "light" : "dark";
      let idx = 0;
      stops.forEach((s, i) => {
        if (q >= s.q - 0.002) idx = i;
      });
      if (idx !== lastActive) {
        lastActive = idx;
        setActive(idx);
      }
    };

    const frame = () => {
      if (!engine) return;
      const { q, visible } = progressOf();
      if (!visible) {
        engine.rest(); // off screen: draw nothing, and don't count the pause as a slow frame
        return;
      }
      engine.q = q;
      engine.tick(performance.now());
      overlays(q);
    };

    const onHud = (s: FrameStats) => {
      const now = performance.now();
      if (!hudRef.current || now - hudAt < 250) return;
      hudAt = now;
      const gpu = s.gpuMs == null ? "n/a" : `${s.gpuMs.toFixed(1)} ms`;
      hudRef.current.textContent = `${s.fps.toFixed(0)} fps  frame ${s.frameMs.toFixed(1)} ms\ngpu ${gpu}  cpu ${s.cpuMs.toFixed(1)} ms\n${s.dpr.toFixed(2)}x  ${s.calls} calls  ${(s.tris / 1e6).toFixed(2)}M tris${s.bloom ? "" : "  no glow"}`;
    };

    const onResize = () => engine?.resize(window.innerWidth, window.innerHeight);
    const onWalk = (e: Event) => {
      const id = (e as CustomEvent<string>).detail;
      const t = timing[id];
      if (t) jump(t.win[0] + 0.004);
    };

    (async () => {
      try {
        const { RealtimeEngine } = await import("./engine");
        if (disposed || !canvasRef.current) return;
        const e = await RealtimeEngine.create(canvasRef.current, (f) => {
          if (loaderBarRef.current) loaderBarRef.current.style.transform = `scaleX(${f.toFixed(3)})`;
        });
        if (disposed) {
          e.dispose();
          return;
        }
        engine = e;
        e.onLost = () => setFailed(true);
        if (showHud) e.onFrame = (_p, s) => onHud(s);
        // the name sits in the landscape: set it in the site's display face once that has loaded
        await document.fonts.ready;
        const family = fontProbeRef.current ? getComputedStyle(fontProbeRef.current).fontFamily : "sans-serif";
        e.setWordmark("HALCYON", family, 0xf4eee3);
        window.addEventListener("resize", onResize);
        gsap.ticker.add(frame);
        frame();
        setReady(true);
        if (process.env.NODE_ENV !== "production") {
          (window as unknown as { __rtEngine: RealtimeEngine }).__rtEngine = e;
        }
      } catch (err) {
        console.error(err);
        if (!disposed) setFailed(true);
      }
    })();

    window.addEventListener("halcyon:walk", onWalk);
    return () => {
      disposed = true;
      gsap.ticker.remove(frame);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("halcyon:walk", onWalk);
      engine?.dispose();
    };
  }, [timing, stops]);

  // entrance once the house is ready: the loader wipes up, the opening copy settles in
  useEffect(() => {
    if (!ready && !failed) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const tl = gsap.timeline();
    tl.to(loaderRef.current, { clipPath: "inset(0 0 100% 0)", duration: reduce ? 0 : 1.1, ease: "expo.inOut" });
    tl.from("[data-hero-copy] > *", { autoAlpha: 0, y: 10, duration: reduce ? 0 : 0.8, stagger: 0.1, ease: "power2.out" }, "-=0.35");
    tl.set(loaderRef.current, { display: "none" });
    return () => {
      tl.kill();
    };
  }, [ready, failed]);

  return (
    <section
      ref={sectionRef}
      id="walkthrough"
      data-theme="dark"
      aria-label="Walk through Halcyon"
      className="relative"
      style={{ height: failed ? "100svh" : `calc(${SCREENS * 100}svh + 100svh)` }}
    >
      <div className="sticky top-0 h-svh w-full overflow-hidden bg-ink">
        <canvas
          ref={canvasRef}
          role="img"
          aria-label="The house drawn live as you scroll: across the lake, through the pivot door, the arrival hall, great room, kitchen and study."
          className="absolute inset-0 block h-full w-full"
        />
        <span ref={fontProbeRef} className="font-wide pointer-events-none absolute opacity-0" aria-hidden>
          H
        </span>

        {failed && (
          <>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/stills/dusk.webp" alt="Halcyon at dusk, seen from the lake" className="absolute inset-0 h-full w-full object-cover" />
            <p className="absolute inset-x-0 top-[38%] px-[var(--gutter)] text-center text-[1.05rem] text-[#efe9de]">
              This browser can&apos;t draw the walkthrough in 3D. The stills and drawings below show the house.
            </p>
          </>
        )}

        {/* lens: soft vignette and a fine static grain, as if shot on a camera */}
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_55%,rgba(13,24,32,0.38)_100%)]" />
        <div className="film-grain pointer-events-none absolute inset-0 opacity-[0.06] mix-blend-overlay" />

        {/* legibility scrims */}
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-[46%] bg-gradient-to-t from-ink/80 via-ink/25 to-transparent" />
        <div className="pointer-events-none absolute inset-x-0 top-0 h-28 bg-gradient-to-b from-ink/55 to-transparent" />

        {/* hero copy */}
        <div ref={heroRef} data-hero-copy className="absolute inset-x-0 bottom-0 flex flex-col gap-6 px-[var(--gutter)] pb-[calc(var(--gutter)+8px)] md:flex-row md:items-end md:justify-between">
          <div className="max-w-[34rem]">
            <h1 className="text-[clamp(1.25rem,1.9vw,1.75rem)] leading-snug text-[#efe9de]">{RESIDENCE.tagline}</h1>
            <p className="mt-2 text-[clamp(0.95rem,1.1vw,1.05rem)] leading-relaxed text-haze">{RESIDENCE.summary}</p>
          </div>
          <div className="flex items-center gap-3 text-sm text-haze">
            <span className="font-semi">Scroll to walk through</span>
            <span className="relative block h-px w-16 overflow-hidden bg-haze/30">
              <span className="absolute inset-y-0 left-0 w-1/3 animate-[route_2.8s_var(--ease-arch)_infinite] bg-glow" />
            </span>
          </div>
        </div>

        {/* chapter cards */}
        <div className="pointer-events-none absolute inset-x-0 bottom-[calc(var(--gutter)+44px)] px-[var(--gutter)]">
          {CHAPTERS.map((c, i) => (
            <article
              key={c.id}
              ref={(el) => {
                cardRefs.current[i] = el;
              }}
              className="invisible absolute bottom-0 left-[var(--gutter)] isolate max-w-[min(31rem,86vw)] opacity-0"
            >
              <div aria-hidden className="absolute -inset-x-[18vw] -bottom-[14vh] -top-[10vh] -z-10 bg-[radial-gradient(ellipse_at_22%_70%,rgba(13,24,32,0.72),rgba(13,24,32,0.35)_45%,transparent_72%)]" />
              <h3 className="font-wide overflow-hidden text-[clamp(1.7rem,3.6vw,3.4rem)] font-medium leading-[0.98] tracking-[-0.01em] text-[#f1ece2]">
                <span data-line className="block">
                  {c.title}
                </span>
              </h3>
              <p data-fade className="mt-3 max-w-[36ch] text-[clamp(0.95rem,1.1vw,1.08rem)] leading-relaxed text-[#ddd6ca]">
                {c.body}
              </p>
              <dl data-fade className="mt-4 grid grid-cols-[repeat(auto-fit,minmax(7rem,1fr))] gap-x-6 gap-y-2 border-t border-limestone/20 pt-3">
                {c.facts.map((f) => (
                  <div key={f.term}>
                    <dt className="font-semi text-[0.72rem] text-haze">{f.term}</dt>
                    <dd className="tabular mt-0.5 text-[0.98rem] text-[#efe9de]">{f.value}</dd>
                  </div>
                ))}
              </dl>
            </article>
          ))}
        </div>

        {/* route line: the walk is one take, so its stops are shown in order */}
        <nav ref={routeRef} aria-label="Walkthrough stops" className="invisible absolute inset-x-0 bottom-0 px-[var(--gutter)] pb-[calc(var(--gutter)*0.7)] opacity-0">
          <div className="relative h-px w-full bg-limestone/20">
            <div ref={progressRef} className="absolute inset-0 origin-left bg-glow" style={{ transform: "scaleX(0)" }} />
            {stops.map((s, i) => (
              <button
                key={s.label}
                type="button"
                onClick={() => jump(s.q)}
                className="group pointer-events-auto absolute top-0 -translate-x-1/2 -translate-y-1/2 p-2"
                style={{ left: `${(s.q * 100).toFixed(2)}%` }}
                aria-current={active === i ? "step" : undefined}
                aria-label={`Go to ${s.label}`}
              >
                <span className={`block h-2 w-2 rounded-full border transition-colors duration-300 ${active >= i ? "border-glow bg-glow" : "border-limestone/50 bg-ink"}`} />
                <span
                  className={`font-semi absolute left-1/2 top-5 -translate-x-1/2 whitespace-nowrap text-[0.72rem] transition-opacity duration-300 ${
                    active === i ? "text-[#efe9de] opacity-100" : "text-haze opacity-0 md:opacity-70 md:group-hover:opacity-100"
                  }`}
                >
                  {s.label}
                </span>
              </button>
            ))}
          </div>
        </nav>

        {/* hand-off: the drawing set on the laptop becomes the page */}
        <div ref={coverRef} className="invisible absolute inset-0 z-20 opacity-0">
          <DossierCover />
        </div>

        <pre ref={hudRef} className="pointer-events-none absolute right-3 top-20 z-30 hidden rounded bg-black/55 px-2 py-1 font-mono text-[11px] leading-tight text-white/85" />

        {/* loader */}
        <div ref={loaderRef} className="absolute inset-0 z-30 flex flex-col items-center justify-center gap-6 bg-ink" style={{ clipPath: "inset(0 0 0% 0)" }}>
          <span className="font-wide text-sm tracking-[0.5em] text-limestone">HALCYON</span>
          <div className="h-px w-40 overflow-hidden bg-limestone/15">
            <div ref={loaderBarRef} className="h-full w-full origin-left bg-glow" style={{ transform: "scaleX(0)" }} />
          </div>
          <span className="text-sm text-haze">Building the house</span>
        </div>
      </div>
    </section>
  );
}
