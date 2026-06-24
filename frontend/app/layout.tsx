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
        <header className="sticky top-0 z-30 border-b border-ink-100 bg-white/70 backdrop-blur-xl">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
            <Link href="/" className="group flex items-center gap-2.5">
              <span className="grid h-9 w-9 place-items-center rounded-xl gradient-brand text-white shadow-glow transition group-hover:scale-105">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 17l5-5 4 4 7-8" /><path d="M16 8h5v5" /></svg>
              </span>
              <span className="flex flex-col leading-none">
                <span className="text-[15px] font-bold tracking-tight text-ink-900">Invest&nbsp;Wisely</span>
                <span className="text-[10px] font-medium uppercase tracking-wider text-ink-400">VC diligence copilot</span>
              </span>
            </Link>
            <nav className="flex items-center gap-1.5">
              <Link href="/" className="rounded-lg px-3 py-1.5 text-sm font-medium text-ink-600 hover:bg-ink-50 hover:text-ink-900">
                Deal flow
              </Link>
              <a href="https://github.com/samarthraj7/Invest_wisely" target="_blank" rel="noreferrer" className="rounded-lg px-3 py-1.5 text-sm font-medium text-ink-600 hover:bg-ink-50 hover:text-ink-900">
                GitHub
              </a>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        <footer className="mx-auto max-w-6xl px-6 py-10 text-center text-xs text-ink-400">
          Directional analyst support — augments, not replaces, partner judgment. Every claim is sourced.
        </footer>
      </body>
    </html>
  );
}
