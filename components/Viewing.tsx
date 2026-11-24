"use client";

import { useState } from "react";
import Image from "next/image";

type Status = "idle" | "error" | "sent";

const MONTHS = ["December 2026", "January 2027", "February 2027", "March 2027", "Later"];

/** Private-viewing request. There is no backend yet: the form validates and confirms locally. */
export default function Viewing() {
  const [status, setStatus] = useState<Status>("idle");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const submit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const next: Record<string, string> = {};
    const name = String(fd.get("name") ?? "").trim();
    const email = String(fd.get("email") ?? "").trim();
    if (!name) next.name = "Enter your name so the estate office knows who to reply to.";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) next.email = "Enter an email address like name@example.com.";
    setErrors(next);
    if (Object.keys(next).length) {
      setStatus("error");
      return;
    }
    setStatus("sent");
  };

  const field = "mt-2 w-full border-b border-limestone/30 bg-transparent pb-2 text-[1.1rem] text-[#efe9de] outline-none transition-colors placeholder:text-slate focus:border-glow";

  return (
    <section id="viewing" data-theme="dark" aria-labelledby="viewing-title" className="relative overflow-hidden bg-ink">
      <div className="absolute inset-0">
        <Image src="/stills/dusk.webp" alt="" fill sizes="100vw" className="object-cover opacity-35" />
        <div className="absolute inset-0 bg-gradient-to-r from-ink via-ink/85 to-ink/40" />
      </div>
      <div className="relative grid gap-12 px-[var(--gutter)] py-[clamp(80px,11vw,180px)] lg:grid-cols-[1fr_1.1fr]">
        <div className="max-w-[36rem]">
          <h2 id="viewing-title" className="font-wide text-[clamp(2.2rem,5vw,4.6rem)] font-medium leading-[0.95] text-[#efe9de]">
            Arrange a private viewing
          </h2>
          <p className="mt-6 max-w-[42ch] text-[1.1rem] leading-relaxed text-[#d9d2c6]">
            Viewings are held by appointment, with the architect present. Arrival is by road through the north gate or by water to the house&apos;s own dock.
          </p>
          <dl className="mt-10 grid grid-cols-2 gap-6 border-t border-limestone/20 pt-6 text-[0.98rem]">
            <div>
              <dt className="font-semi text-[0.72rem] text-haze">Estate office</dt>
              <dd className="mt-1 text-[#efe9de]">+41 81 000 00 00</dd>
            </div>
            <div>
              <dt className="font-semi text-[0.72rem] text-haze">Location</dt>
              <dd className="mt-1 text-[#efe9de]">North shore, Lake Serein</dd>
            </div>
          </dl>
        </div>
        {status === "sent" ? (
          <div role="status" className="self-center border-l border-glow pl-6">
            <p className="font-wide text-[1.6rem] font-medium text-[#efe9de]">Request received</p>
            <p className="mt-3 max-w-[40ch] text-[1.05rem] leading-relaxed text-haze">
              The estate office replies within two working days to confirm a date and send directions.
            </p>
          </div>
        ) : (
          <form noValidate onSubmit={submit} className="grid gap-8 self-center sm:grid-cols-2" aria-describedby={status === "error" ? "form-errors" : undefined}>
            <label className="block">
              <span className="font-semi text-[0.78rem] text-haze">Name</span>
              <input name="name" autoComplete="name" className={field} aria-invalid={!!errors.name} aria-describedby={errors.name ? "err-name" : undefined} />
              {errors.name && (
                <span id="err-name" className="mt-2 block text-[0.9rem] text-glow">
                  {errors.name}
                </span>
              )}
            </label>
            <label className="block">
              <span className="font-semi text-[0.78rem] text-haze">Email</span>
              <input name="email" type="email" autoComplete="email" className={field} aria-invalid={!!errors.email} aria-describedby={errors.email ? "err-email" : undefined} />
              {errors.email && (
                <span id="err-email" className="mt-2 block text-[0.9rem] text-glow">
                  {errors.email}
                </span>
              )}
            </label>
            <label className="block">
              <span className="font-semi text-[0.78rem] text-haze">Phone (optional)</span>
              <input name="phone" type="tel" autoComplete="tel" className={field} />
            </label>
            <label className="block">
              <span className="font-semi text-[0.78rem] text-haze">Preferred month</span>
              <select name="month" className={`${field} appearance-none`} defaultValue={MONTHS[1]}>
                {MONTHS.map((m) => (
                  <option key={m} value={m} className="bg-ink">
                    {m}
                  </option>
                ))}
              </select>
            </label>
            <label className="block sm:col-span-2">
              <span className="font-semi text-[0.78rem] text-haze">Anything we should know (optional)</span>
              <textarea name="message" rows={3} className={`${field} resize-none`} />
            </label>
            <div className="flex flex-wrap items-center gap-6 sm:col-span-2">
              <button type="submit" className="font-semi rounded-full bg-[#efe9de] px-7 py-3.5 text-[0.92rem] text-ink transition-colors hover:bg-glow">
                Request a viewing
              </button>
              <p id="form-errors" className="text-[0.92rem] text-haze">
                {status === "error" ? "Check the highlighted fields." : "We reply within two working days."}
              </p>
            </div>
          </form>
        )}
      </div>
    </section>
  );
}
