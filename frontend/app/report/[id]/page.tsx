"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { exportUrl, getDeck } from "@/lib/api";
import type { ExportFormat } from "@/lib/api";
import type { DeckDetail } from "@/lib/types";
import { Banner, ClaimRow, ConfidenceBadge, recMeta, Section, SEV_STYLE, SourceTag } from "@/components/ui";

const NAV = [
  ["snapshot", "Company snapshot"],
  ["team", "Team analysis"],
  ["competition", "Competitive landscape"],
  ["flags", "Red flags"],
  ["diligence", "Diligence questions"],
  ["valuation", "Valuation"],
  ["recommendation", "Recommendation"],
] as const;

function sevRank(s: string) {
  return { critical: 0, high: 1, medium: 2, low: 3 }[s] ?? 9;
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
  if (!deck) return <Loading label="Loading report…" />;
  if (deck.status === "error")
    return <Back>Analysis failed: {deck.error || "the deck could not be parsed."}</Back>;
  if (deck.status !== "done" || !deck.report)
    return <Loading label={`Analyzing “${deck.filename}”…`} sub="This page updates automatically." />;

  const r = deck.report;
  const s = r.company_snapshot;
  const rec = r.recommendation;
  const meta = recMeta(rec.recommendation);
  const hasDelivery = !!(r.delivery && r.delivery.available);
  const sevCounts = r.red_flags.reduce<Record<string, number>>((a, f) => {
    a[f.severity] = (a[f.severity] || 0) + 1;
    return a;
  }, {});

  return (
    <div className="space-y-6">
      {/* Top bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <Link href="/" className="inline-flex items-center gap-1.5 text-sm text-ink-500 hover:text-ink-900">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m15 18-6-6 6-6" /></svg>
          Deal flow
        </Link>
        <div className="flex items-center gap-2">
          <span className="mr-1 hidden text-xs font-medium text-ink-400 sm:inline">Export</span>
          {(["pdf", "docx", "html"] as ExportFormat[]).map((f) => (
            <a key={f} href={exportUrl(deck.id, f)} target="_blank" rel="noreferrer" className="btn-ghost px-3 py-2 text-xs uppercase">
              {f}
            </a>
          ))}
          <button onClick={() => window.print()} className="btn-primary px-3 py-2 text-xs">Print</button>
        </div>
      </div>

      {/* Banners */}
      {r.mock_mode && (
        <Banner kind="warning" title="Sample analysis (not deck-specific)">
          {r.warnings[0] ?? "Running in mock mode — add API keys with credits for real analysis."}
        </Banner>
      )}
      {!r.mock_mode && r.warnings.length > 0 && (
        <Banner kind="warning" title="Data-quality notes">
          <ul className="list-disc space-y-0.5 pl-5">
            {r.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </Banner>
      )}

      {/* Hero */}
      <div className="card overflow-hidden">
        <div className="gradient-brand px-6 py-5 text-white">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <h1 className="text-2xl font-bold tracking-tight">{s.name}</h1>
              <p className="mt-1 max-w-xl text-sm text-white/85">{s.one_liner}</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {[s.sector, s.stage, s.location].filter(Boolean).map((t) => (
                  <span key={t} className="chip bg-white/15 text-white backdrop-blur">{t}</span>
                ))}
              </div>
            </div>
            <div className="shrink-0 rounded-2xl bg-white/15 p-4 text-center backdrop-blur">
              <p className="text-[10px] uppercase tracking-wider text-white/70">Recommendation</p>
              <p className="mt-1 text-xl font-bold">{meta.label}</p>
              <p className="mt-0.5 text-xs text-white/80">Risk: {rec.risk_rating}</p>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 divide-x divide-ink-100 border-t border-ink-100 sm:grid-cols-4">
          <HeroStat label="Ask" value={s.ask ?? "—"} />
          <HeroStat label="Val range" value={`${r.valuation.range_low ?? "?"}–${r.valuation.range_high ?? "?"}`} />
          <HeroStat label="Check size" value={rec.suggested_check_size ?? "—"} />
          <HeroStat
            label="Red flags"
            value={
              <span className="flex items-center gap-1">
                {(["critical", "high", "medium", "low"] as const)
                  .filter((k) => sevCounts[k])
                  .map((k) => (
                    <span key={k} className={`chip ${SEV_STYLE[k].bg} ${SEV_STYLE[k].text}`}>
                      {sevCounts[k]} {k}
                    </span>
                  ))}
                {r.red_flags.length === 0 && "none"}
              </span>
            }
          />
        </div>
      </div>

      {/* Consolidated summary */}
      {r.executive_summary && (
        <div className="card border-l-4 border-brand-500 px-5 py-4">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-brand-600">
            Consolidated summary
          </p>
          <p className="text-sm leading-relaxed text-ink-800">{r.executive_summary}</p>
        </div>
      )}

      {/* Two-column: sticky nav + content */}
      <div className="grid gap-6 lg:grid-cols-[200px_1fr]">
        <nav className="hidden lg:block print:hidden">
          <div className="sticky top-24 space-y-1">
            {NAV.map(([id, label], i) => (
              <a key={id} href={`#${id}`} className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm text-ink-500 transition hover:bg-ink-50 hover:text-ink-900">
                <span className="text-xs font-semibold text-ink-300">{i + 1}</span>
                {label}
              </a>
            ))}
            {hasDelivery && (
              <a href="#delivery" className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm text-ink-500 transition hover:bg-ink-50 hover:text-ink-900">
                <span className="text-xs font-semibold text-ink-300">{NAV.length + 1}</span>
                Pitch delivery
              </a>
            )}
          </div>
        </nav>

        <div className="space-y-6">
          <Section id="snapshot" n={1} title="Company snapshot">
            {s.deck_claims.length === 0 ? (
              <p className="text-sm text-ink-400">No explicit claims extracted.</p>
            ) : (
              s.deck_claims.map((c, i) => <ClaimRow key={i} claim={c} />)
            )}
          </Section>

          <Section id="team" n={2} title="Team analysis">
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
                <div className="mt-3 space-y-3">
                  {(m.researched_background?.length ?? 0) > 0 && (
                    <div>
                      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-ink-400">
                        Background &amp; experience
                      </p>
                      <div className="space-y-2">
                        {m.researched_background.map((c, k) => (
                          <ClaimRow key={`b${k}`} claim={c} />
                        ))}
                      </div>
                    </div>
                  )}

                  {(m.strengths?.length ?? 0) > 0 &&
                    m.strengths.map((c, k) => (
                      <div key={`s${k}`} className="rounded-xl border border-emerald-200 bg-emerald-50/60 px-4 py-3">
                        <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Strength</p>
                        <p className="mt-1 text-sm text-ink-800">{c.claim}</p>
                        <SourceTag claim={c} />
                      </div>
                    ))}

                  {(m.founder_market_fit?.length ?? 0) > 0 &&
                    m.founder_market_fit.map((c, k) => (
                      <div key={`f${k}`} className="rounded-xl border border-violet-200 bg-violet-50/60 px-4 py-3">
                        <p className="text-xs font-semibold uppercase tracking-wide text-violet-700">Founder–market fit</p>
                        <p className="mt-1 text-sm text-ink-800">{c.claim}</p>
                        <SourceTag claim={c} />
                      </div>
                    ))}

                  {(m.gaps_vs_venture?.length ?? 0) > 0 &&
                    m.gaps_vs_venture.map((c, k) => (
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

          <Section id="competition" n={3} title="Competitive landscape">
            <div className="grid gap-2 sm:grid-cols-2">
              {r.competitive_landscape.named_in_deck.map((c, i) => (
                <div key={`n${i}`} className="rounded-xl border border-ink-100 px-4 py-3">
                  <p className="text-sm font-semibold text-ink-900">
                    {c.name} <span className="chip bg-brand-50 text-brand-700">{c.relationship}</span>
                  </p>
                  <SourceTag claim={c.note} />
                </div>
              ))}
              {r.competitive_landscape.discovered.map((c, i) => (
                <div key={`d${i}`} className="rounded-xl border border-ink-100 px-4 py-3">
                  <p className="text-sm font-semibold text-ink-900">
                    {c.name} <span className="chip bg-sky-50 text-sky-700">discovered</span>
                  </p>
                  <SourceTag claim={c.note} />
                </div>
              ))}
            </div>
            <p className="pt-2 text-xs font-semibold uppercase tracking-wide text-ink-400">Differentiation check</p>
            {r.competitive_landscape.differentiation_assessment.map((c, i) => (
              <ClaimRow key={i} claim={c} />
            ))}
          </Section>

          <Section id="flags" n={4} title="Red flags">
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

          <Section id="diligence" n={5} title="Suggested diligence questions">
            <ol className="space-y-2">
              {r.diligence_questions.map((q, i) => (
                <li key={i} className="flex gap-3 rounded-xl border border-ink-100 px-4 py-3">
                  <span className="grid h-6 w-6 shrink-0 place-items-center rounded-lg bg-brand-50 text-xs font-bold text-brand-700">
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

          <Section id="valuation" n={6} title="Valuation analysis">
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
            <div className="rounded-xl border border-ink-100 bg-ink-50/40 px-4 py-3">
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

          <Section id="recommendation" n={7} title="Recommendation">
            <div className={`rounded-xl border px-4 py-4 ${meta.bg} ${meta.ring} ring-1`}>
              <div className="flex flex-wrap items-center gap-3">
                <span className={`inline-flex items-center gap-2 rounded-xl px-3 py-1.5 text-sm font-bold text-white ${meta.bar}`}>
                  {meta.label}
                </span>
                <span className="chip bg-white/70 text-ink-700">Risk: {rec.risk_rating}</span>
                {rec.suggested_check_size && (
                  <span className="chip bg-white/70 text-ink-700">Check: {rec.suggested_check_size}</span>
                )}
              </div>
              <p className="mt-3 text-sm text-ink-700">{rec.rationale}</p>
            </div>
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-400">Named risk factors</p>
            {rec.risk_factors.map((c, i) => (
              <ClaimRow key={i} claim={c} />
            ))}
          </Section>

          {hasDelivery && r.delivery && (
            <Section id="delivery" n={NAV.length + 1} title="Pitch delivery & Q&A">
              {r.delivery.source && (
                <span className="chip bg-ink-100 text-ink-600">source: {r.delivery.source}</span>
              )}
              <div className="grid gap-3 sm:grid-cols-2">
                {r.delivery.clarity && <DeliveryCell label="Clarity" value={r.delivery.clarity} />}
                {r.delivery.structure && <DeliveryCell label="Structure" value={r.delivery.structure} />}
                {r.delivery.handling_of_questions && (
                  <DeliveryCell label="Handling of cross-questions" value={r.delivery.handling_of_questions} />
                )}
                {r.delivery.tone && <DeliveryCell label="Tone (from video)" value={r.delivery.tone} />}
              </div>

              {(r.delivery.strengths.length > 0 || r.delivery.weaknesses.length > 0) && (
                <div className="grid gap-3 sm:grid-cols-2">
                  {r.delivery.strengths.length > 0 && (
                    <div className="rounded-xl border border-emerald-100 bg-emerald-50/50 px-4 py-3">
                      <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Delivery strengths</p>
                      <ul className="mt-2 space-y-1 text-sm text-ink-700">
                        {r.delivery.strengths.map((x, i) => <li key={i}>• {x}</li>)}
                      </ul>
                    </div>
                  )}
                  {r.delivery.weaknesses.length > 0 && (
                    <div className="rounded-xl border border-amber-100 bg-amber-50/50 px-4 py-3">
                      <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">Delivery weaknesses</p>
                      <ul className="mt-2 space-y-1 text-sm text-ink-700">
                        {r.delivery.weaknesses.map((x, i) => <li key={i}>• {x}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {r.delivery.qa.length > 0 && (
                <div className="space-y-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-ink-400">Questions &amp; answers</p>
                  {r.delivery.qa.map((q, i) => (
                    <div key={i} className="rounded-xl border border-ink-100 bg-white px-4 py-3">
                      <p className="text-sm font-medium text-ink-900">Q. {q.question}</p>
                      {q.answer && <p className="mt-1 text-sm text-ink-600"><span className="font-medium text-ink-500">A.</span> {q.answer}</p>}
                      {q.assessment && (
                        <p className="mt-2 flex items-start gap-2 text-xs text-ink-500">
                          <span className="chip bg-ink-100 text-ink-600">{q.confidence}</span>
                          <span>{q.assessment}</span>
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </Section>
          )}

          <p className="rounded-2xl bg-ink-100/60 px-4 py-3 text-center text-xs text-ink-500">{r.analyst_note}</p>
        </div>
      </div>
    </div>
  );
}

function HeroStat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="px-4 py-3">
      <p className="text-[10px] uppercase tracking-wider text-ink-400">{label}</p>
      <div className="mt-0.5 text-sm font-semibold text-ink-900">{value}</div>
    </div>
  );
}

function DeliveryCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-ink-100 bg-white px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-ink-400">{label}</p>
      <p className="mt-1 text-sm text-ink-700">{value}</p>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-ink-100 px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-ink-400">{label}</p>
      <p className="mt-1 text-sm font-semibold text-ink-900">{value}</p>
    </div>
  );
}

function Loading({ label, sub }: { label: string; sub?: string }) {
  return (
    <div className="space-y-4">
      <Link href="/" className="text-sm text-ink-500 hover:text-ink-900">← Deal flow</Link>
      <div className="card flex flex-col items-center gap-3 px-6 py-16 text-center">
        <span className="h-8 w-8 animate-spin rounded-full border-2 border-ink-200 border-t-brand-500" />
        <p className="text-sm font-medium text-ink-700">{label}</p>
        {sub && <p className="text-xs text-ink-400">{sub}</p>}
      </div>
    </div>
  );
}

function Back({ children }: { children: React.ReactNode }) {
  return (
    <div className="space-y-4">
      <Link href="/" className="text-sm text-ink-500 hover:text-ink-900">← Deal flow</Link>
      <div className="card px-6 py-12 text-center text-sm text-ink-500">{children}</div>
    </div>
  );
}
