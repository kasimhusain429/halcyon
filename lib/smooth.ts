import type Lenis from "lenis";

/** Module-level handle on the page's Lenis instance (set by <SmoothScroll />). */
let instance: Lenis | null = null;

export function setLenis(l: Lenis | null) {
  instance = l;
}

export function getLenis() {
  return instance;
}

/** Scroll to an absolute document offset, smoothly when Lenis is running. */
export function scrollToY(y: number, immediate = false) {
  if (instance) instance.scrollTo(y, { immediate, duration: immediate ? 0 : 1.6 });
  else window.scrollTo({ top: y, behavior: immediate ? "auto" : "smooth" });
}
