"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { health, listDecks, runDemo, uploadDeck } from "@/lib/api";
import type { DeckListItem } from "@/lib/types";

const REC_STYLE: Record<string, string> = {
  invest: "bg-emerald-50 text-emerald-700 border-emerald-200",
  pass: "bg-red-50 text-red-700 border-red-200",
  more_diligence: "bg-amber-50 text-amber-700 border-amber-200",
};

const STATUS_LABEL: Record<string, string> = {
  pending: "Queued",
  parsing: "Parsing deck",
  understanding: "Reading deck",
  extracting: "Extracting team",
  researching: "Researching",
  analyzing: "Analyzing",
  done: "Done",
  error: "Error",
};

function recLabel(r: string) {
  return r === "more_diligence" ? "More diligence" : r ? r[0].toUpperCase() + r.slice(1) : "—";
}

export default function Dashboard() {
  const [decks, setDecks] = useState<DeckListItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const [mock, setMock] = useState<boolean | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      setDecks(await listDecks());
    } catch (e) {
      setErr("Can't reach the API. Start the backend on :8000.");
    }
  }, []);

  useEffect(() => {
    refresh();
    health().then((h) => setMock(h.mock_mode)).catch(() => setMock(null));
    const t = setInterval(refresh, 2500);
    return () => clearInterval(t);
  }, [refresh]);

  const onFile = useCallback(
    async (file: File) => {
      setBusy(true);
      setErr(null);
      try {
        await uploadDeck(file);
        await refresh();
      } catch (e) {
        setErr("Upload failed. Is the backend running?");
      } finally {
        setBusy(false);
      }
    },
    [refresh]
  );

  const onDemo = async () => {
    setBusy(true);
    setErr(null);
    try {
      await runDemo();
      await refresh();
    } catch {
      setErr("Couldn't start demo. Is the backend running?");
    } finally {
      setBusy(false);
    }
  };

  const pending = decks.some((d) => !["done", "error"].includes(d.status));

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight text-ink-900">Deal flow</h1>
        <p className="max-w-2xl text-sm text-ink-600">
          Upload a startup&apos;s pitch deck and get a sharp, fully-sourced investment memo —
          team risk, real differentiation, diligence questions, and comp-based valuation reasoning.
        </p>
      </div>

      {mock && (
        <div className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <span className="mt-0.5">⚠</span>
          <div>
            <b>Mock mode.</b> The pipeline runs end-to-end with deterministic sample research.
            Add <code className="rounded bg-amber-100 px-1">ANTHROPIC_API_KEY</code> and{" "}
            <code className="rounded bg-amber-100 px-1">EXA_API_KEY</code> to{" "}
            <code className="rounded bg-amber-100 px-1">.env</code> for live analysis.
          </div>
        </div>
      )}

      {/* Upload */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          const f = e.dataTransfer.files?.[0];
          if (f) onFile(f);
        }}
        className={`card flex flex-col items-center justify-center gap-3 border-2 border-dashed px-6 py-12 text-center transition ${
          drag ? "border-brand-500 bg-brand-500/5" : "border-ink-100"
        }`}
      >
        <div className="grid h-12 w-12 place-items-center rounded-2xl bg-brand-600/10 text-brand-700">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 16V4" /><path d="m6 10 6-6 6 6" /><path d="M4 20h16" /></svg>
        </div>
        <div>
          <p className="text-sm font-semibold text-ink-900">Drop a pitch deck here</p>
          <p className="text-xs text-ink-400">PDF or PPTX · up to ~30 slides</p>
        </div>
        <div className="mt-1 flex gap-2">
          <button className="btn-primary" disabled={busy} onClick={() => inputRef.current?.click()}>
            {busy ? "Working…" : "Choose file"}
          </button>
          <button className="btn-ghost" disabled={busy} onClick={onDemo}>
            Try a demo deck
          </button>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.pptx,.ppt"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onFile(f);
          }}
        />
      </div>

      {err && <p className="text-sm text-red-600">{err}</p>}

      {/* List */}
      <div className="card overflow-hidden">
        <div className="flex items-center justify-between border-b border-ink-100 px-5 py-3.5">
          <h2 className="text-sm font-semibold text-ink-900">
            Submitted decks <span className="text-ink-400">({decks.length})</span>
          </h2>
          {pending && (
            <span className="flex items-center gap-2 text-xs text-ink-400">
              <span className="h-2 w-2 animate-pulse rounded-full bg-brand-500" /> analyzing…
            </span>
          )}
        </div>

        {decks.length === 0 ? (
          <div className="px-5 py-12 text-center text-sm text-ink-400">
            No decks yet. Upload one above or try the demo.
          </div>
        ) : (
          <ul className="divide-y divide-ink-100">
            {decks.map((d) => {
              const done = d.status === "done";
              const Row = (
                <div className="flex items-center justify-between gap-4 px-5 py-4 transition hover:bg-ink-50/60">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-ink-900">
                      {d.company_name && d.company_name !== "Unknown" ? d.company_name : d.filename}
                    </p>
                    <p className="truncate text-xs text-ink-400">{d.filename}</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {done ? (
                      <>
                        <span className={`chip border ${REC_STYLE[d.recommendation] ?? "bg-ink-100 text-ink-600 border-ink-100"}`}>
                          {recLabel(d.recommendation)}
                        </span>
                        {d.risk_rating && (
                          <span className="chip bg-ink-100 text-ink-600">risk: {d.risk_rating}</span>
                        )}
                      </>
                    ) : d.status === "error" ? (
                      <span className="chip bg-red-50 text-red-700">Error</span>
                    ) : (
                      <span className="chip bg-brand-500/10 text-brand-700">
                        <span className="mr-1 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-brand-500" />
                        {STATUS_LABEL[d.status] ?? d.status}
                      </span>
                    )}
                  </div>
                </div>
              );
              return (
                <li key={d.id}>
                  {done ? <Link href={`/report/${d.id}`}>{Row}</Link> : Row}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
