/*
 * Adapted from Kokonut UI "Lightbox Grid" (21st.dev) by @dorianbaffier.
 * MIT License, Copyright (c) 2025 kokonutUI. Permission is hereby granted, free of
 * charge, to any person obtaining a copy of this software ... THE SOFTWARE IS
 * PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND. (Full text: kokonutui.com)
 *
 * Changes for Halcyon: horizontal still strip instead of a grid, Halcyon palette and
 * type, square corners, captions with room + note, ink backdrop.
 */
"use client";

import { animate, type MotionValue, motion, useMotionValue, useReducedMotion, useTransform } from "motion/react";
import Image from "next/image";
import { type KeyboardEvent, type PointerEvent, type ReactNode, type Ref, useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

export type Still = { src: string; room: string; note: string; width: number; height: number };

const EASE: [number, number, number, number] = [0.23, 1, 0.32, 1];
const OPEN = { type: "spring", duration: 0.55, bounce: 0.08 } as const;
const CLOSE = { type: "spring", duration: 0.45, bounce: 0.05 } as const;
const SETTLE = { type: "spring", duration: 0.35, bounce: 0.15 } as const;
const MARGIN = 40;
const MARGIN_SMALL = 10;
const CAPTION_ROOM = 64;
const DISMISS_DISTANCE = 110;
const DISMISS_SPEED = 0.55;
const SWIPE_SPEED = 0.45;
const AXIS_LOCK = 6;

type Rect = { left: number; top: number; width: number; height: number };
type Frame = { x: number; y: number; scale: number; clip: string };

function fitRect(s: Still): Rect {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const m = vw < 640 ? MARGIN_SMALL : MARGIN;
  const k = Math.min((vw - m * 2) / s.width, (vh - m * 2 - CAPTION_ROOM) / s.height);
  const width = s.width * k;
  const height = s.height * k;
  return { left: (vw - width) / 2, top: (vh - CAPTION_ROOM - height) / 2, width, height };
}

const openClip = () => "inset(0px 0px 0px 0px)";

/** Transform + crop that make the open still look exactly like its slot in the strip. */
function thumbFrame(open: Rect, thumb: DOMRect, s: Still): Frame {
  const ir = s.width / s.height;
  const tr = thumb.width / thumb.height;
  const coverW = ir > tr ? thumb.height * ir : thumb.width;
  const scale = coverW / open.width;
  const ix = (open.width - thumb.width / scale) / 2;
  const iy = (open.height - thumb.height / scale) / 2;
  return {
    x: thumb.left + thumb.width / 2 - (open.left + open.width / 2),
    y: thumb.top + thumb.height / 2 - (open.top + open.height / 2),
    scale,
    clip: `inset(${iy}px ${ix}px ${iy}px ${ix}px)`,
  };
}

const visible = (r: DOMRect) => r.bottom > 0 && r.top < window.innerHeight && r.right > 0 && r.left < window.innerWidth;

function Btn({ label, onClick, children, className = "", buttonRef }: { label: string; onClick: () => void; children: ReactNode; className?: string; buttonRef?: Ref<HTMLButtonElement> }) {
  return (
    <button
      ref={buttonRef}
      type="button"
      aria-label={label}
      onClick={onClick}
      className={`font-semi flex h-10 items-center justify-center rounded-full border border-limestone/30 px-4 text-[0.82rem] text-[#efe9de] transition-colors hover:border-glow hover:text-glow disabled:pointer-events-none disabled:opacity-30 ${className}`}
    >
      {children}
    </button>
  );
}

type ViewerProps = {
  stills: Still[];
  index: number;
  rect: Rect;
  x: MotionValue<number>;
  y: MotionValue<number>;
  scale: MotionValue<number>;
  clip: MotionValue<string>;
  alpha: MotionValue<number>;
  fade: MotionValue<number>;
  settled: boolean;
  onClose: (v?: { x: number; y: number }) => void;
  onStep: (d: 1 | -1) => void;
};

function Viewer({ stills, index, rect, x, y, scale, clip, alpha, fade, settled, onClose, onStep }: ViewerProps) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const drag = useRef<{ id: number; sx: number; sy: number; axis: "x" | "y" | null; samples: { x: number; y: number; t: number }[] } | null>(null);
  const backdrop = useTransform(fade, (v) => v * 0.94);
  const s = stills[index];
  const hasPrev = index > 0;
  const hasNext = index < stills.length - 1;

  useEffect(() => {
    closeRef.current?.focus({ preventScroll: true });
  }, []);

  const down = (e: PointerEvent<HTMLDivElement>) => {
    if (!settled || e.button !== 0) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = { id: e.pointerId, sx: e.clientX, sy: e.clientY, axis: null, samples: [{ x: e.clientX, y: e.clientY, t: e.timeStamp }] };
  };
  const move = (e: PointerEvent<HTMLDivElement>) => {
    const d = drag.current;
    if (!d || d.id !== e.pointerId) return;
    const dx = e.clientX - d.sx;
    const dy = e.clientY - d.sy;
    if (!d.axis) {
      if (Math.hypot(dx, dy) < AXIS_LOCK) return;
      d.axis = Math.abs(dx) > Math.abs(dy) ? "x" : "y";
    }
    d.samples.push({ x: e.clientX, y: e.clientY, t: e.timeStamp });
    if (d.samples.length > 5) d.samples.shift();
    if (d.axis === "y") {
      const pull = Math.min(Math.abs(dy) / window.innerHeight, 1);
      x.set(dx);
      y.set(dy);
      scale.set(1 - pull * 0.45);
      fade.set(1 - Math.min(Math.abs(dy) / 360, 1) * 0.85);
    } else {
      const blocked = (dx > 0 && !hasPrev) || (dx < 0 && !hasNext);
      x.set(blocked ? dx * 0.25 : dx);
    }
  };
  const up = (e: PointerEvent<HTMLDivElement>) => {
    const d = drag.current;
    if (!d || d.id !== e.pointerId) return;
    drag.current = null;
    const a = d.samples[0];
    const b = d.samples.at(-1) ?? a;
    const dt = Math.max(1, b.t - a.t);
    const v = { x: (b.x - a.x) / dt, y: (b.y - a.y) / dt };
    if (d.axis === "y") {
      const dy = e.clientY - d.sy;
      if (Math.abs(dy) > DISMISS_DISTANCE || Math.abs(v.y) > DISMISS_SPEED) return onClose(v);
      animate(x, 0, SETTLE);
      animate(y, 0, SETTLE);
      animate(scale, 1, SETTLE);
      animate(fade, 1, { duration: 0.2, ease: EASE });
    } else if (d.axis === "x") {
      const dx = e.clientX - d.sx;
      const far = Math.abs(dx) > rect.width * 0.22 || Math.abs(v.x) > SWIPE_SPEED;
      if (far && dx < 0 && hasNext) onStep(1);
      else if (far && dx > 0 && hasPrev) onStep(-1);
      else animate(x, 0, SETTLE);
    }
  };
  const keys = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape") {
      e.preventDefault();
      onClose();
    } else if (e.key === "ArrowRight" && hasNext) onStep(1);
    else if (e.key === "ArrowLeft" && hasPrev) onStep(-1);
    else if (e.key === "Tab") {
      const f = Array.from(dialogRef.current?.querySelectorAll<HTMLButtonElement>("button:not(:disabled)") ?? []);
      if (e.shiftKey && document.activeElement === f[0]) {
        e.preventDefault();
        f.at(-1)?.focus();
      } else if (!e.shiftKey && document.activeElement === f.at(-1)) {
        e.preventDefault();
        f[0]?.focus();
      }
    }
  };

  return (
    <div ref={dialogRef} role="dialog" aria-modal="true" aria-label={`${s.room}. ${s.note}`} onKeyDown={keys} className="fixed inset-0 z-[100]" data-lenis-prevent>
      <motion.div aria-hidden className="absolute inset-0 bg-ink" onClick={() => onClose()} style={{ opacity: backdrop }} />
      <motion.div
        className="absolute cursor-grab touch-none select-none overflow-hidden active:cursor-grabbing"
        onPointerDown={down}
        onPointerMove={move}
        onPointerUp={up}
        onPointerCancel={up}
        onLostPointerCapture={up}
        style={{ left: rect.left, top: rect.top, width: rect.width, height: rect.height, x, y, scale, clipPath: clip, opacity: alpha, willChange: "transform, clip-path" }}
      >
        <Image alt={`${s.room}. ${s.note}`} src={s.src} width={s.width} height={s.height} sizes="100vw" draggable={false} className="pointer-events-none h-full w-full object-cover" />
      </motion.div>
      <motion.div className="pointer-events-none absolute inset-0" style={{ opacity: fade }}>
        <div className="pointer-events-auto absolute right-3 top-3 flex items-center gap-3 sm:right-5 sm:top-5">
          <span className="tabular text-[0.9rem] text-haze">
            Still {index + 1} of {stills.length}
          </span>
          <Btn buttonRef={closeRef} label="Close" onClick={() => onClose()}>
            Close
          </Btn>
        </div>
        <div className="pointer-events-auto absolute inset-x-0 flex items-baseline justify-between gap-4 px-[var(--gutter)]" style={{ top: rect.top + rect.height + 18 }}>
          <p className="min-w-0 text-[1rem] text-[#d9d2c6]">
            <span className="font-semi mr-3 text-[0.9rem] text-[#efe9de]">{s.room}</span>
            {s.note}
          </p>
          <div className="hidden shrink-0 gap-2 sm:flex">
            <Btn label="Previous still" onClick={() => hasPrev && onStep(-1)}>
              Previous
            </Btn>
            <Btn label="Next still" onClick={() => hasNext && onStep(1)}>
              Next
            </Btn>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

/** Horizontal strip of stills; each lifts out of the strip into a full view. */
export default function StillsStrip({ stills }: { stills: Still[] }) {
  const [active, setActive] = useState<number | null>(null);
  const [rect, setRect] = useState<Rect | null>(null);
  const [settled, setSettled] = useState(false);
  const [closing, setClosing] = useState(false);
  const thumbs = useRef<(HTMLButtonElement | null)[]>([]);
  const rowRef = useRef<HTMLOListElement>(null);
  const reduce = useReducedMotion();
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const scale = useMotionValue(1);
  const clip = useMotionValue(openClip());
  const alpha = useMotionValue(1);
  const fade = useMotionValue(0);

  const frameFor = useCallback(
    (i: number, open: Rect): Frame | null => {
      const t = thumbs.current[i];
      if (!t) return null;
      const box = t.getBoundingClientRect();
      return visible(box) ? thumbFrame(open, box, stills[i]) : null;
    },
    [stills],
  );

  const open = useCallback(
    (i: number) => {
      const target = fitRect(stills[i]);
      const from = frameFor(i, target);
      setActive(i);
      setRect(target);
      setClosing(false);
      setSettled(false);
      alpha.set(1);
      if (!from || reduce) {
        x.set(0);
        y.set(0);
        scale.set(1);
        clip.set(openClip());
        fade.set(0);
        alpha.set(0);
        animate(alpha, 1, { duration: 0.18 });
        animate(fade, 1, { duration: 0.18 }).then(() => setSettled(true));
        return;
      }
      x.set(from.x);
      y.set(from.y);
      scale.set(from.scale);
      clip.set(from.clip);
      fade.set(0);
      animate(x, 0, OPEN);
      animate(y, 0, OPEN);
      animate(scale, 1, OPEN);
      animate(clip, openClip(), OPEN);
      animate(fade, 1, { duration: 0.32, ease: EASE }).then(() => setSettled(true));
    },
    [alpha, clip, fade, frameFor, stills, reduce, scale, x, y],
  );

  const close = useCallback(
    (v?: { x: number; y: number }) => {
      if (active === null || !rect || closing) return;
      setClosing(true);
      const i = active;
      thumbs.current[i]?.scrollIntoView({ behavior: "instant", block: "nearest", inline: "nearest" });
      const to = frameFor(i, rect);
      const finish = () => {
        setActive(null);
        setRect(null);
        setClosing(false);
        thumbs.current[i]?.focus({ preventScroll: true });
      };
      if (!to || reduce) {
        animate(alpha, 0, { duration: 0.16 });
        animate(fade, 0, { duration: 0.16 }).then(finish);
        return;
      }
      animate(x, to.x, { ...CLOSE, velocity: (v?.x ?? 0) * 1000 });
      animate(y, to.y, { ...CLOSE, velocity: (v?.y ?? 0) * 1000 });
      animate(scale, to.scale, CLOSE);
      animate(clip, to.clip, CLOSE);
      animate(fade, 0, { duration: 0.28, ease: EASE });
      window.setTimeout(finish, 440);
    },
    [active, alpha, clip, closing, fade, frameFor, rect, reduce, scale, x, y],
  );

  const step = useCallback(
    (d: 1 | -1) => {
      if (active === null) return;
      const n = active + d;
      if (n < 0 || n >= stills.length) return;
      setActive(n);
      setRect(fitRect(stills[n]));
      thumbs.current[n]?.scrollIntoView({ behavior: "instant", block: "nearest", inline: "nearest" });
      y.set(0);
      scale.set(1);
      clip.set(openClip());
      fade.set(1);
      if (reduce) {
        x.set(0);
        alpha.set(1);
        return;
      }
      x.set(d * 72);
      alpha.set(0);
      animate(x, 0, { duration: 0.32, ease: EASE });
      animate(alpha, 1, { duration: 0.22, ease: EASE });
    },
    [active, alpha, clip, fade, stills, reduce, scale, x, y],
  );

  useEffect(() => {
    if (active === null) return;
    const root = document.documentElement;
    const prev = root.style.overflow;
    root.style.overflow = "hidden";
    const onResize = () => setRect(fitRect(stills[active]));
    window.addEventListener("resize", onResize);
    return () => {
      root.style.overflow = prev;
      window.removeEventListener("resize", onResize);
    };
  }, [active, stills]);

  const nudge = (d: number) => {
    const row = rowRef.current;
    const item = row?.querySelector("li");
    row?.scrollBy({ left: d * ((item?.clientWidth ?? 600) + 24), behavior: "smooth" });
  };

  return (
    <>
      <div className="flex justify-end gap-2 px-[var(--gutter)]">
        <Btn label="Scroll stills left" onClick={() => nudge(-1)}>
          Previous
        </Btn>
        <Btn label="Scroll stills right" onClick={() => nudge(1)}>
          Next
        </Btn>
      </div>
      <ol
        ref={rowRef}
        data-lenis-prevent
        aria-label="Stills"
        className="mt-6 flex snap-x snap-mandatory gap-6 overflow-x-auto scroll-px-[var(--gutter)] px-[var(--gutter)] pb-4 [scrollbar-width:none]"
      >
        {stills.map((s, i) => (
          <li key={s.src} className="w-[min(82vw,1180px)] shrink-0 snap-start">
            <figure>
              <button
                ref={(n) => {
                  thumbs.current[i] = n;
                }}
                type="button"
                onClick={() => open(i)}
                aria-label={`Open still: ${s.room}`}
                className="relative block aspect-[16/9] w-full cursor-zoom-in overflow-hidden bg-ink-2"
                style={{ opacity: active === i ? 0 : 1 }}
              >
                <Image src={s.src} alt="" fill sizes="(max-width: 768px) 82vw, 1180px" className="object-cover" draggable={false} />
              </button>
              <figcaption className="mt-4 flex flex-wrap items-baseline gap-x-4 gap-y-1">
                <span className="font-semi text-[0.9rem] text-[#efe9de]">{s.room}</span>
                <span className="text-[1rem] text-haze">{s.note}</span>
              </figcaption>
            </figure>
          </li>
        ))}
      </ol>
      {active !== null && rect
        ? createPortal(
            <Viewer stills={stills} index={active} rect={rect} x={x} y={y} scale={scale} clip={clip} alpha={alpha} fade={fade} settled={settled && !closing} onClose={close} onStep={step} />,
            document.body,
          )
        : null}
    </>
  );
}
