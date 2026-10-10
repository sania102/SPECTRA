import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SPECTRA — Information Blind-Spot Intelligence",
  description: "Search wider. See what you're missing. SPECTRA investigates a question across Google Search, News, Trends, Scholar, Jobs, Shopping, YouTube and Patents via SerpApi and shows where the signals disagree.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <div className="aurora" aria-hidden>
          <div className="blob b1" /><div className="blob b2" /><div className="blob b3" /><div className="grid-fade" />
        </div>
        {children}
      </body>
    </html>
  );
}
