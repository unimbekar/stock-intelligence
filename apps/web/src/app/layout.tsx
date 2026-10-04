import type { Metadata } from "next";
import { IBM_Plex_Mono, Instrument_Sans } from "next/font/google";

import { Shell, ThemeBoot, ThemeSync } from "@/components/shell";
import { readProduct } from "@/lib/product";

import "./globals.css";

const sans = Instrument_Sans({
  variable: "--font-instrument",
  subsets: ["latin"],
});

const mono = IBM_Plex_Mono({
  variable: "--font-plex",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Meridian",
  description: "Local US equity research, risk, and paper-trading desk.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const product = readProduct();
  return (
    <html
      lang="en"
      className={`${sans.variable} ${mono.variable} dark h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="min-h-full">
        <ThemeBoot />
        <ThemeSync />
        <a href="#content" className="sr-only focus:not-sr-only focus:absolute focus:z-10 focus:bg-elevated focus:p-2">
          Skip to content
        </a>
        <Shell dataModeLabel={product.dataModeLabel}>
          <div id="content">{children}</div>
          <footer className="mt-10 border-t border-line pt-4 text-xs leading-5 text-muted">
            {product.disclaimer}
          </footer>
        </Shell>
      </body>
    </html>
  );
}
