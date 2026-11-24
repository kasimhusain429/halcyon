"use client";

import { useEffect, useState } from "react";
import StillsStrip, { type Still } from "./StillsStrip";

/**
 * Stills are published as their renders finish: list only the ones the server has.
 * (Checked in the browser — a server-side file check would make the dev bundler watch
 * the whole project, render output included.)
 */
export default function AvailableStills({ stills }: { stills: Still[] }) {
  const [ready, setReady] = useState<Still[] | null>(null);
  useEffect(() => {
    let live = true;
    Promise.all(stills.map((s) => fetch(s.src, { method: "HEAD" }).then((r) => r.ok, () => false))).then((ok) => {
      if (live) setReady(stills.filter((_, i) => ok[i]));
    });
    return () => {
      live = false;
    };
  }, [stills]);
  return <StillsStrip stills={ready ?? stills} />;
}
