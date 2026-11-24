import type { Metadata, Viewport } from "next";
import { Archivo, Newsreader } from "next/font/google";
import "./globals.css";

const archivo = Archivo({
  variable: "--font-archivo",
  subsets: ["latin"],
  axes: ["wdth"],
  display: "swap",
});

const newsreader = Newsreader({
  variable: "--font-newsreader",
  subsets: ["latin"],
  style: ["normal", "italic"],
  axes: ["opsz"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Halcyon — A private residence on Lake Serein",
  description:
    "Walk through Halcyon, a lakeside residence of limestone, oak and glass on the north shore of Lake Serein. Arrange a private viewing.",
  openGraph: {
    title: "Halcyon — A private residence on Lake Serein",
    description: "A walkthrough of a lakeside residence of limestone, oak and glass.",
    images: [{ url: "/stills/dusk.webp", width: 1920, height: 1080, alt: "Halcyon at dusk, seen from the lake" }],
  },
};

export const viewport: Viewport = {
  themeColor: "#0d1820",
  colorScheme: "dark",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${archivo.variable} ${newsreader.variable}`}>
      <body>{children}</body>
    </html>
  );
}
