import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Invest Wisely — AI Pitch Deck Analyzer",
  description: "Analyst-grade investment memos from pitch decks, with traceable sources.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="font-sans">
        <header className="sticky top-0 z-20 border-b border-ink-100 bg-white/80 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3.5">
            <Link href="/" className="flex items-center gap-2.5">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-600 text-white shadow-soft">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 17l5-5 4 4 7-8" /><path d="M16 8h5v5" /></svg>
              </span>
              <span className="text-[15px] font-bold tracking-tight text-ink-900">
                Invest&nbsp;Wisely
              </span>
            </Link>
            <span className="hidden text-xs text-ink-400 sm:block">
              Judgment-support for VC diligence · every claim sourced
            </span>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
