"use client";

import { useEffect, useState } from "react";
import { NAV } from "@/lib/residence";
import { scrollToY } from "@/lib/smooth";

/** Fixed header; switches ink/limestone depending on the section beneath it. */
export default function SiteHeader() {
  const [light, setLight] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const sections = Array.from(document.querySelectorAll<HTMLElement>("[data-theme]"));
    const check = () => {
      const y = 36;
      const hit = sections.find((s) => {
        const r = s.getBoundingClientRect();
        return r.top <= y && r.bottom > y;
      });
      setLight(hit?.dataset.theme === "light");
    };
    check();
    window.addEventListener("scroll", check, { passive: true });
    window.addEventListener("resize", check);
    return () => {
      window.removeEventListener("scroll", check);
      window.removeEventListener("resize", check);
    };
  }, []);

  const go = (href: string) => (e: React.MouseEvent) => {
    const el = document.querySelector<HTMLElement>(href);
    if (!el) return;
    e.preventDefault();
    setOpen(false);
    scrollToY(el.getBoundingClientRect().top + window.scrollY);
  };

  const tone = light ? "text-ink" : "text-[#efe9de]";
  return (
    <header className={`fixed inset-x-0 top-0 z-40 transition-colors duration-500 ${tone}`}>
      <div className="flex items-center justify-between px-[var(--gutter)] py-[clamp(14px,1.8vw,24px)]">
        <a href="#walkthrough" onClick={go("#walkthrough")} className="font-wide text-[0.95rem] font-semibold tracking-[0.32em]" aria-label="Halcyon, back to the start">
          HALCYON
        </a>
        <nav aria-label="Primary" className="hidden items-center gap-[clamp(18px,2.4vw,40px)] md:flex">
          {NAV.slice(0, 3).map((n) => (
            <a key={n.href} href={n.href} onClick={go(n.href)} className="font-semi text-[0.86rem] opacity-80 transition-opacity hover:opacity-100">
              {n.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          <a
            href="#viewing"
            onClick={go("#viewing")}
            className={`font-semi hidden rounded-full border px-4 py-2 text-[0.82rem] transition-colors sm:inline-block ${
              light ? "border-ink/40 hover:bg-ink hover:text-vellum" : "border-[#efe9de]/40 hover:bg-[#efe9de] hover:text-ink"
            }`}
          >
            Arrange a viewing
          </a>
          <button
            type="button"
            className="font-semi text-[0.86rem] md:hidden"
            aria-expanded={open}
            aria-controls="mobile-nav"
            onClick={() => setOpen((v) => !v)}
          >
            {open ? "Close" : "Menu"}
          </button>
        </div>
      </div>
      <nav
        id="mobile-nav"
        aria-label="Mobile"
        className={`md:hidden ${open ? "visible opacity-100" : "invisible opacity-0"} absolute inset-x-0 top-full bg-ink/95 px-[var(--gutter)] pb-6 pt-2 text-[#efe9de] backdrop-blur transition-opacity duration-300`}
      >
        <ul className="flex flex-col gap-4">
          {NAV.map((n) => (
            <li key={n.href}>
              <a href={n.href} onClick={go(n.href)} className="font-wide text-2xl font-medium">
                {n.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  );
}
