"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { exportUrl, getDeck } from "@/lib/api";
import type { ExportFormat } from "@/lib/api";
import type { DeckDetail } from "@/lib/types";
import { ClaimRow, ConfidenceBadge, Section, SEV_STYLE, SourceTag } from "@/components/ui";

const REC_STYLE: Record<string, string> = {
  invest: "bg-emerald-600",
  pass: "bg-red-600",
  more_diligence: "bg-amber-500",
};

function recLabel(r: string) {
  return r === "more_diligence" ? "More diligence" : r ? r[0].toUpperCase() + r.slice(1) : "—";
}

export default function ReportPage({ params }: { params: { id: string } }) {
  const [deck, setDeck] = useState<DeckDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let stop = false;
    const tick = async () => {
      try {
        const d = await getDeck(params.id);
        if (stop) return;
        setDeck(d);
        if (!["done", "error"].includes(d.status)) setTimeout(tick, 2000);
      } catch {
        setError("Couldn't load this report.");
      }
    };
    tick();
    return () => {
      stop = true;
    };
  }, [params.id]);

  if (error) return <Back>{error}</Back>;
  if (!deck) return <Back>Loading…</Back>;
  if (deck.status === "error")
    return <Back>Analysis failed: {deck.error || "deck could not be parsed."}</Back>;
  if (deck.status !== "done" || !deck.report)
    return <Back>Analyzing “{deck.filename}”… this page will update automatically.</Back>;

  const r = deck.report;
  const s = r.company_snapshot;
  const rec = r.recommendation;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <Link href="/" className="text-sm text-ink-400 hover:text-ink-800">
          ← Deal flow
        </Link>
        <div className="flex items-center gap-2">
          <span className="mr-1 text-xs font-medium text-ink-400">Export</span>
          {(["pdf", "docx", "html"] as ExportFormat[]).map((f) => (
            <a
              key={f}
              href={exportUrl(deck.id, f)}
              target="_blank"
              rel="noreferrer"
              className="btn-ghost px-3 py-2 text-xs uppercase"
            >
              {f}
            </a>
          ))}
          <button onClick={() => window.print()} className="btn-primary px-3 py-2 text-xs">
            Print
          </button>
        </div>
      </div>

      {r.warnings.length > 0 && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 print:hidden">
          <p className="mb-1 font-semibold">Data-quality notes</p>
          <ul className="list-disc space-y-0.5 pl-5">
            {r.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Hero */}
      <div className="card overflow-hidden">
        <div className="flex flex-col gap-4 p-6 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight text-ink-900">{s.name}</h1>
              {r.mock_mode && (
                <span className="chip bg-amber-50 text-amber-700">mock mode</span>
              )}
            </div>
            <p className="max-w-xl text-sm text-ink-600">{s.one_liner}</p>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {[s.sector, s.stage, s.location].filter(Boolean).map((t) => (
                <span key={t} className="chip bg-ink-100 text-ink-600">
                  {t}
                </span>
              ))}
            </div>
          </div>
          <div className="shrink-0 rounded-2xl border border-ink-100 bg-ink-50/60 p-4 text-center">
            <p className="text-xs uppercase tracking-wide text-ink-400">Recommendation</p>
            <p className="mt-1 flex items-center justify-center gap-2">
              <span className={`h-2.5 w-2.5 rounded-full ${REC_STYLE[rec.recommendation]}`} />
              <span className="text-lg font-bold text-ink-900">{recLabel(rec.recommendation)}</span>
            </p>
            <p className="mt-1 text-xs text-ink-500">Risk: {rec.risk_rating}</p>
          </div>
        </div>
        {s.ask && (
          <div className="border-t border-ink-100 px-6 py-3 text-sm text-ink-600">
            <b className="text-ink-900">Ask:</b> {s.ask}
          </div>
        )}
      </div>

      {/* 1 - Snapshot */}
      <Section n={1} title="Company snapshot">
        {s.deck_claims.length === 0 ? (
          <p className="text-sm text-ink-400">No explicit claims extracted.</p>
        ) : (
          s.deck_claims.map((c, i) => <ClaimRow key={i} claim={c} />)
        )}
      </Section>

      {/* 2 - Team */}
      <Section n={2} title="Team analysis">
        {r.team_analysis.map((m, i) => (
          <div key={i} className="rounded-xl border border-ink-100 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="font-semibold text-ink-900">{m.name}</p>
                <p className="text-xs text-ink-400">{m.title}</p>
              </div>
              <div className="flex items-center gap-2">
                {m.research_confidence === "inconclusive" && (
                  <span className="chip bg-orange-50 text-orange-700">not found online</span>
                )}
                <ConfidenceBadge c={m.research_confidence} />
              </div>
            </div>
            <div className="mt-3 space-y-2">
              {m.researched_background.map((c, k) => (
                <ClaimRow key={`b${k}`} claim={c} />
              ))}
              {m.gaps_vs_venture.map((c, k) => (
                <div key={`g${k}`} className="rounded-xl border border-orange-200 bg-orange-50/60 px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-orange-600">Gap vs. venture</p>
                  <p className="mt-1 text-sm text-ink-800">{c.claim}</p>
                  <SourceTag claim={c} />
                </div>
              ))}
            </div>
          </div>
        ))}
      </Section>

      {/* 3 - Competition */}
      <Section n={3} title="Competitive landscape">
        <div className="grid gap-2 sm:grid-cols-2">
          {r.competitive_landscape.named_in_deck.map((c, i) => (
            <div key={`n${i}`} className="rounded-xl border border-ink-100 bg-white px-4 py-3">
              <p className="text-sm font-semibold text-ink-900">
                {c.name} <span className="chip bg-brand-500/10 text-brand-700">{c.relationship}</span>
              </p>
              <SourceTag claim={c.note} />
            </div>
          ))}
          {r.competitive_landscape.discovered.map((c, i) => (
            <div key={`d${i}`} className="rounded-xl border border-ink-100 bg-white px-4 py-3">
              <p className="text-sm font-semibold text-ink-900">
                {c.name} <span className="chip bg-sky-50 text-sky-700">discovered</span>
              </p>
              <SourceTag claim={c.note} />
            </div>
          ))}
        </div>
        <p className="pt-2 text-xs font-semibold uppercase tracking-wide text-ink-400">
          Differentiation check
        </p>
        {r.competitive_landscape.differentiation_assessment.map((c, i) => (
          <ClaimRow key={i} claim={c} />
        ))}
      </Section>

      {/* 4 - Red flags */}
      <Section n={4} title="Red flags">
        {[...r.red_flags]
          .sort((a, b) => sevRank(a.severity) - sevRank(b.severity))
          .map((f, i) => {
            const st = SEV_STYLE[f.severity];
            return (
              <div key={i} className={`rounded-xl border px-4 py-3 ${st.bg}`}>
                <div className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${st.dot}`} />
                  <span className={`text-xs font-bold uppercase ${st.text}`}>{f.severity}</span>
                  <span className="text-sm font-semibold text-ink-900">{f.title}</span>
                </div>
                <p className="mt-1.5 text-sm text-ink-700">{f.reasoning.claim}</p>
                <SourceTag claim={f.reasoning} />
              </div>
            );
          })}
      </Section>

      {/* 5 - Diligence questions */}
      <Section n={5} title="Suggested diligence questions">
        <ol className="space-y-2">
          {r.diligence_questions.map((q, i) => (
            <li key={i} className="flex gap-3 rounded-xl border border-ink-100 px-4 py-3">
              <span className="grid h-6 w-6 shrink-0 place-items-center rounded-lg bg-brand-600/10 text-xs font-bold text-brand-700">
                {i + 1}
              </span>
              <div>
                <p className="text-sm text-ink-800">{q.question}</p>
                <p className="mt-1 text-xs text-ink-400">→ closes: {q.targets_gap}</p>
              </div>
            </li>
          ))}
        </ol>
      </Section>

      {/* 6 - Valuation */}
      <Section n={6} title="Valuation analysis">
        <div className="grid gap-3 sm:grid-cols-3">
          <Stat label="Comp-derived range" value={`${r.valuation.range_low ?? "?"} – ${r.valuation.range_high ?? "?"}`} />
          <Stat label="Deck ask" value={r.valuation.deck_ask ?? "—"} />
          <Stat label="Multiples used" value={r.valuation.multiples_used ?? "—"} />
        </div>
        {r.valuation.comps.length > 0 && (
          <div className="overflow-hidden rounded-xl border border-ink-100">
            <table className="w-full text-sm">
              <thead className="bg-ink-50 text-left text-xs uppercase text-ink-400">
                <tr>
                  <th className="px-4 py-2 font-medium">Comp</th>
                  <th className="px-4 py-2 font-medium">Detail</th>
                  <th className="px-4 py-2 font-medium">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-100">
                {r.valuation.comps.map((c, i) => (
                  <tr key={i}>
                    <td className="px-4 py-2 font-medium text-ink-900">{c.company}</td>
                    <td className="px-4 py-2 text-ink-600">{c.detail}</td>
                    <td className="px-4 py-2 text-xs text-ink-400">{c.source.source_ref}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="rounded-xl border border-ink-100 bg-ink-50/50 px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-400">Assumptions</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-ink-700">
            {r.valuation.assumptions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </div>
        {r.valuation.ask_vs_comps.map((c, i) => (
          <ClaimRow key={i} claim={c} />
        ))}
      </Section>

      {/* 7 - Recommendation */}
      <Section n={7} title="Recommendation">
        <div className="rounded-xl border border-ink-100 bg-ink-50/50 p-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className={`inline-flex items-center gap-2 rounded-xl px-3 py-1.5 text-sm font-bold text-white ${REC_STYLE[rec.recommendation]}`}>
              {recLabel(rec.recommendation)}
            </span>
            <span className="chip bg-red-50 text-red-700">Risk: {rec.risk_rating}</span>
            {rec.suggested_check_size && (
              <span className="chip bg-emerald-50 text-emerald-700">Check: {rec.suggested_check_size}</span>
            )}
          </div>
          <p className="mt-3 text-sm text-ink-700">{rec.rationale}</p>
        </div>
        <p className="text-xs font-semibold uppercase tracking-wide text-ink-400">Named risk factors</p>
        {rec.risk_factors.map((c, i) => (
          <ClaimRow key={i} claim={c} />
        ))}
      </Section>

      <p className="rounded-2xl bg-ink-100/60 px-4 py-3 text-center text-xs text-ink-500">
        {r.analyst_note}
      </p>
    </div>
  );
}

function sevRank(s: string) {
  return { critical: 0, high: 1, medium: 2, low: 3 }[s] ?? 9;
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-ink-100 bg-white px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-ink-400">{label}</p>
      <p className="mt-1 text-sm font-semibold text-ink-900">{value}</p>
    </div>
  );
}

function Back({ children }: { children: React.ReactNode }) {
  return (
    <div className="space-y-4">
      <Link href="/" className="text-sm text-ink-400 hover:text-ink-800">
        ← Deal flow
      </Link>
      <div className="card px-6 py-12 text-center text-sm text-ink-500">{children}</div>
    </div>
  );
}
