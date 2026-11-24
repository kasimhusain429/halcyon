import { RESIDENCE } from "@/lib/residence";

export default function Footer() {
  return (
    <footer data-theme="dark" className="border-t border-limestone/10 bg-ink px-[var(--gutter)] py-10 text-[0.92rem] text-haze">
      <div className="flex flex-col justify-between gap-6 md:flex-row md:items-end">
        <div>
          <p className="font-wide text-[clamp(2.4rem,9vw,8rem)] font-semibold leading-none tracking-[0.02em] text-[#efe9de]/90">HALCYON</p>
          <p className="mt-3">
            {RESIDENCE.place}, {RESIDENCE.coordinates}, {RESIDENCE.elevation}
          </p>
        </div>
        <p className="max-w-[44ch] md:text-right">
          All images are rendered from the architectural model. Areas are gross internal and approximate.
        </p>
      </div>
    </footer>
  );
}
