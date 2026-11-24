import SmoothScroll from "@/components/SmoothScroll";
import SiteHeader from "@/components/SiteHeader";
import Walkthrough from "@/components/walkthrough/Walkthrough";
import Dossier from "@/components/dossier/Dossier";
import Stills from "@/components/Stills";
import Viewing from "@/components/Viewing";
import Footer from "@/components/Footer";

export default function Home() {
  return (
    <>
      <SmoothScroll />
      <a
        href="#drawings"
        className="font-semi fixed left-3 top-3 z-50 -translate-y-24 rounded-full bg-[#efe9de] px-4 py-2 text-[0.85rem] text-ink transition-transform focus:translate-y-0"
      >
        Skip the walkthrough
      </a>
      <SiteHeader />
      <main>
        <Walkthrough />
        <Dossier />
        <Stills />
        <Viewing />
      </main>
      <Footer />
    </>
  );
}
