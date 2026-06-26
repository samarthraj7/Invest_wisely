"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { deleteDeck, health, listDecks, runDemo, uploadDeck } from "@/lib/api";
import type { DeckListItem } from "@/lib/types";
import { Banner, recMeta } from "@/components/ui";

const STAGES = ["pending", "parsing", "transcribing", "ocr", "understanding", "extracting", "researching", "analyzing", "delivery", "scoring"];
const STAGE_LABEL: Record<string, string> = {
  pending: "Queued",
  parsing: "Parsing deck",
  transcribing: "Transcribing video",
  ocr: "Reading images (OCR)",
  understanding: "Reading deck",
  extracting: "Extracting team",
  researching: "Researching web",
  analyzing: "Writing memo",
  delivery: "Analyzing delivery",
  scoring: "Scoring & graph",
};

function progressPct(status: string) {
  const i = STAGES.indexOf(status);
  if (i < 0) return status === "done" ? 100 : 8;
  return Math.round(((i + 1) / (STAGES.length + 1)) * 100);
}

export default function Dashboard() {
  const [decks, setDecks] = useState<DeckListItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const [mock, setMock] = useState<boolean | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<string>("all");
  const inputRef = useRef<HTMLInputElement>(null);

  // Optional pitch-recording inputs.
  const [showExtras, setShowExtras] = useState(false);
  const [transcriptText, setTranscriptText] = useState("");
  const [transcriptFile, setTranscriptFile] = useState<File | null>(null);
  const [videoFile, setVideoFile] = useState<File | null>(null);

  const refresh = useCallback(async () => {
    try {
      setDecks(await listDecks());
      setErr(null);
    } catch {
      setErr("Can't reach the API. Start the backend:  powershell -ExecutionPolicy Bypass -File backend\\run.ps1");
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
        await uploadDeck(file, {
          transcriptText,
          transcriptFile,
          video: videoFile,
        });
        setTranscriptText("");
        setTranscriptFile(null);
        setVideoFile(null);
        await refresh();
      } catch {
        setErr("Upload failed. Is the backend running?");
      } finally {
        setBusy(false);
      }
    },
    [refresh, transcriptText, transcriptFile, videoFile]
  );

  const remove = useCallback(
    async (id: string) => {
      setDecks((prev) => prev.filter((d) => d.id !== id));
      try {
        await deleteDeck(id);
      } catch {
        refresh();
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

  const stats = useMemo(() => {
    const done = decks.filter((d) => d.status === "done");
    return {
      total: decks.length,
      invest: done.filter((d) => d.recommendation === "invest").length,
      diligence: done.filter((d) => d.recommendation === "more_diligence").length,
      pass: done.filter((d) => d.recommendation === "pass").length,
      running: decks.filter((d) => !["done", "error"].includes(d.status)).length,
    };
  }, [decks]);

  const visible = useMemo(() => {
    return decks.filter((d) => {
      const matchQ =
        !query ||
        d.company_name.toLowerCase().includes(query.toLowerCase()) ||
        d.filename.toLowerCase().includes(query.toLowerCase());
      const matchF =
        filter === "all" ||
        (filter === "running" && !["done", "error"].includes(d.status)) ||
        d.recommendation === filter;
      return matchQ && matchF;
    });
  }, [decks, query, filter]);

  return (
    <div className="space-y-8">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-3xl gradient-brand p-8 text-white shadow-glow sm:p-10">
        <div className="absolute -right-16 -top-16 h-64 w-64 rounded-full bg-white/10 blur-2xl" />
        <div className="absolute -bottom-20 -left-10 h-56 w-56 rounded-full bg-violet-400/20 blur-2xl" />
        <div className="relative max-w-2xl">
          <span className="chip bg-white/15 text-white backdrop-blur">AI diligence copilot</span>
          <h1 className="mt-3 text-3xl font-bold leading-tight tracking-tight sm:text-4xl">
            Turn a pitch deck into a sourced investment memo.
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-white/85 sm:text-base">
            Upload a deck and get team-risk flags, real differentiation checks, sharp diligence
            questions, and comp-based valuation reasoning — every claim traceable to a deck page or a
            research source.
          </p>
        </div>
      </section>

      {mock && (
        <Banner kind="warning" title="Mock mode active">
          The pipeline runs end-to-end with deterministic sample analysis, so every deck returns the
          same example memo. Add <code className="rounded bg-amber-100 px-1">ANTHROPIC_API_KEY</code> +{" "}
          <code className="rounded bg-amber-100 px-1">EXA_API_KEY</code> to{" "}
          <code className="rounded bg-amber-100 px-1">.env</code> (with Anthropic credits) for real,
          deck-specific analysis.
        </Banner>
      )}
      {err && <Banner kind="error">{err}</Banner>}

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
        className={`card card-hover flex flex-col items-center justify-center gap-3 border-2 border-dashed px-6 py-10 text-center ${
          drag ? "border-brand-500 bg-brand-50" : "border-ink-200"
        }`}
      >
        <div className="grid h-14 w-14 place-items-center rounded-2xl bg-brand-50 text-brand-600">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 16V4" /><path d="m6 10 6-6 6 6" /><path d="M4 20h16" /></svg>
        </div>
        <div>
          <p className="text-sm font-semibold text-ink-900">Drop a pitch deck to analyze</p>
          <p className="text-xs text-ink-400">PDF or PPTX · up to 30 MB · drag &amp; drop or browse</p>
        </div>
        <div className="mt-1 flex flex-wrap justify-center gap-2">
          <button className="btn-primary" disabled={busy} onClick={() => inputRef.current?.click()}>
            {busy ? "Working…" : "Choose file"}
          </button>
          <button className="btn-ghost" disabled={busy} onClick={onDemo}>
            ✨ Try a demo deck
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

      {/* Optional pitch recording */}
      <div className="card px-5 py-4">
        <button
          onClick={() => setShowExtras((v) => !v)}
          className="flex w-full items-center justify-between text-left"
        >
          <span className="flex items-center gap-2 text-sm font-semibold text-ink-800">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" /><path d="M19 10v2a7 7 0 0 1-14 0v-2" /><path d="M12 19v3" /></svg>
            Add pitch recording (optional)
            {(transcriptText || transcriptFile || videoFile) && (
              <span className="chip bg-brand-50 text-brand-700">attached</span>
            )}
          </span>
          <span className="text-xs text-ink-400">{showExtras ? "Hide" : "Show"}</span>
        </button>

        {showExtras && (
          <div className="mt-4 space-y-4">
            <p className="text-xs text-ink-400">
              A transcript deepens the company understanding and unlocks a pitch delivery / Q&amp;A
              analysis. Tone analysis runs only when a video is attached.
            </p>

            <div>
              <label className="mb-1 block text-xs font-medium text-ink-500">Transcript text</label>
              <textarea
                value={transcriptText}
                onChange={(e) => setTranscriptText(e.target.value)}
                placeholder="Paste the pitch / Q&A transcript here…"
                rows={4}
                className="input resize-y"
              />
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs font-medium text-ink-500">…or transcript file (.txt/.vtt/.srt)</label>
                <input
                  type="file"
                  accept=".txt,.vtt,.srt"
                  onChange={(e) => setTranscriptFile(e.target.files?.[0] ?? null)}
                  className="block w-full text-xs text-ink-500 file:mr-3 file:rounded-lg file:border-0 file:bg-ink-100 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-ink-700 hover:file:bg-ink-200"
                />
                {transcriptFile && <p className="mt-1 truncate text-xs text-ink-400">{transcriptFile.name}</p>}
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-ink-500">Pitch video (enables tone analysis)</label>
                <input
                  type="file"
                  accept="video/*"
                  onChange={(e) => setVideoFile(e.target.files?.[0] ?? null)}
                  className="block w-full text-xs text-ink-500 file:mr-3 file:rounded-lg file:border-0 file:bg-ink-100 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-ink-700 hover:file:bg-ink-200"
                />
                {videoFile && <p className="mt-1 truncate text-xs text-ink-400">{videoFile.name}</p>}
              </div>
            </div>
            <p className="text-xs text-ink-400">
              Then choose your deck above — the recording is attached to that analysis. Video
              auto-transcription needs an <code className="rounded bg-ink-100 px-1">OPENAI_API_KEY</code>;
              otherwise also paste a transcript.
            </p>
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <StatCard label="Decks" value={stats.total} tone="brand" />
        <StatCard label="Invest" value={stats.invest} tone="emerald" />
        <StatCard label="More diligence" value={stats.diligence} tone="amber" />
        <StatCard label="Pass" value={stats.pass} tone="red" />
        <StatCard label="Analyzing" value={stats.running} tone="ink" pulse={stats.running > 0} />
      </div>

      {/* Toolbar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-xs">
          <svg className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-400" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></svg>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search company or file…"
            className="input pl-9"
          />
        </div>
        <div className="flex flex-wrap gap-1.5">
          {[
            ["all", "All"],
            ["running", "Analyzing"],
            ["invest", "Invest"],
            ["more_diligence", "Diligence"],
            ["pass", "Pass"],
          ].map(([k, label]) => (
            <button
              key={k}
              onClick={() => setFilter(k)}
              className={`chip border px-3 py-1.5 transition ${
                filter === k
                  ? "border-brand-200 bg-brand-50 text-brand-700"
                  : "border-ink-200 bg-white text-ink-500 hover:bg-ink-50"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Deck grid */}
      {visible.length === 0 ? (
        <div className="card flex flex-col items-center gap-2 px-6 py-16 text-center">
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-ink-100 text-ink-400">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /></svg>
          </div>
          <p className="text-sm font-medium text-ink-700">
            {decks.length === 0 ? "No decks yet" : "No matches"}
          </p>
          <p className="text-xs text-ink-400">
            {decks.length === 0 ? "Upload a deck above or try the demo to see a memo." : "Adjust your search or filter."}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {visible.map((d) => (
            <DeckCard key={d.id} deck={d} onDelete={remove} />
          ))}
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  tone,
  pulse,
}: {
  label: string;
  value: number;
  tone: "brand" | "emerald" | "amber" | "red" | "ink";
  pulse?: boolean;
}) {
  const tones: Record<string, string> = {
    brand: "text-brand-600",
    emerald: "text-emerald-600",
    amber: "text-amber-600",
    red: "text-red-600",
    ink: "text-ink-700",
  };
  return (
    <div className="card px-4 py-3">
      <div className="flex items-center gap-1.5">
        {pulse && <span className="h-1.5 w-1.5 animate-pulse-ring rounded-full bg-brand-500" />}
        <p className="text-xs font-medium text-ink-400">{label}</p>
      </div>
      <p className={`mt-1 text-2xl font-bold ${tones[tone]}`}>{value}</p>
    </div>
  );
}

function DeckCard({
  deck: d,
  onDelete,
}: {
  deck: DeckListItem;
  onDelete: (id: string) => void;
}) {
  const done = d.status === "done";
  const error = d.status === "error";
  const running = !done && !error;
  const meta = recMeta(d.recommendation);
  const title = d.company_name && d.company_name !== "Unknown" ? d.company_name : d.filename;

  const when = new Date(d.created_at);
  const whenLabel = isNaN(when.getTime())
    ? ""
    : when.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });

  const body = (
    <div className="card card-hover flex h-full flex-col gap-3 p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-semibold text-ink-900">{title}</p>
          <p className="truncate text-xs text-ink-400">{d.filename}</p>
          {(d.has_transcript || d.has_video) && (
            <div className="mt-1 flex gap-1">
              {d.has_transcript && <span className="chip bg-violet-50 text-violet-700">transcript</span>}
              {d.has_video && <span className="chip bg-violet-50 text-violet-700">video</span>}
            </div>
          )}
        </div>
        {done && (
          <span className={`chip shrink-0 ring-1 ${meta.bg} ${meta.text} ${meta.ring}`}>{meta.label}</span>
        )}
        {error && <span className="chip shrink-0 bg-red-50 text-red-700">Error</span>}
      </div>

      {running && (
        <div className="mt-1">
          <div className="mb-1 flex items-center gap-2 text-xs font-medium text-brand-700">
            <span className="h-1.5 w-1.5 animate-pulse-ring rounded-full bg-brand-500" />
            {STAGE_LABEL[d.status] ?? d.status}…
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-100">
            <div className="h-full rounded-full gradient-brand transition-all duration-500" style={{ width: `${progressPct(d.status)}%` }} />
          </div>
        </div>
      )}

      {error && d.error && (
        <p className="rounded-lg bg-red-50 px-2.5 py-1.5 text-xs leading-snug text-red-700 line-clamp-3">
          {d.error}
        </p>
      )}

      <div className="mt-auto flex items-center justify-between pt-1">
        <span className="text-xs text-ink-400">{whenLabel}</span>
        {done ? (
          <span className="flex items-center gap-2">
            {d.risk_rating && <span className="chip-outline">Risk: {d.risk_rating}</span>}
            <span className="text-xs font-semibold text-brand-600">View memo →</span>
          </span>
        ) : (
          <span className="text-xs text-ink-300">{error ? "Failed" : "In progress"}</span>
        )}
      </div>
    </div>
  );

  return (
    <div className="group relative">
      {done ? <Link href={`/report/${d.id}`}>{body}</Link> : body}
      <button
        title="Remove"
        aria-label="Remove deck"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onDelete(d.id);
        }}
        className="absolute right-2 top-2 z-10 grid h-7 w-7 place-items-center rounded-full bg-white/85 text-ink-400 shadow-sm ring-1 ring-ink-200 backdrop-blur transition hover:bg-red-50 hover:text-red-600"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6 6 18" /><path d="m6 6 12 12" /></svg>
      </button>
    </div>
  );
}
