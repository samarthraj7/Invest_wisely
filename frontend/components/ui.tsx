import type { Claim, Confidence, Severity } from "@/lib/types";

const CONF_STYLE: Record<Confidence, string> = {
  high: "bg-emerald-50 text-emerald-700",
  medium: "bg-amber-50 text-amber-700",
  low: "bg-orange-50 text-orange-700",
  inconclusive: "bg-ink-100 text-ink-600",
};

const SRC_STYLE: Record<string, string> = {
  deck: "bg-brand-500/10 text-brand-700",
  web: "bg-sky-50 text-sky-700",
  enrichment: "bg-violet-50 text-violet-700",
  inference: "bg-ink-100 text-ink-600",
};

export const SEV_STYLE: Record<Severity, { dot: string; text: string; bg: string }> = {
  critical: { dot: "bg-red-600", text: "text-red-700", bg: "bg-red-50 border-red-200" },
  high: { dot: "bg-red-500", text: "text-red-600", bg: "bg-red-50/70 border-red-200" },
  medium: { dot: "bg-amber-500", text: "text-amber-700", bg: "bg-amber-50 border-amber-200" },
  low: { dot: "bg-lime-500", text: "text-lime-700", bg: "bg-lime-50 border-lime-200" },
};

function isUrl(s: string) {
  return s.startsWith("http://") || s.startsWith("https://");
}

export function SourceTag({ claim }: { claim: Claim }) {
  return (
    <span className="mt-1.5 flex flex-wrap items-center gap-1.5">
      <span className={`chip ${SRC_STYLE[claim.source_type] ?? "bg-ink-100 text-ink-600"}`}>
        {claim.source_type}
      </span>
      {isUrl(claim.source_ref) ? (
        <a href={claim.source_ref} target="_blank" rel="noreferrer" className="text-xs text-brand-600 underline decoration-dotted underline-offset-2 hover:text-brand-700">
          {claim.source_ref.replace(/^https?:\/\//, "").slice(0, 42)}
        </a>
      ) : (
        <span className="text-xs text-ink-400">{claim.source_ref}</span>
      )}
      <span className={`chip ${CONF_STYLE[claim.confidence]}`}>{claim.confidence}</span>
    </span>
  );
}

export function ClaimRow({ claim }: { claim: Claim }) {
  return (
    <div className="rounded-xl border border-ink-100 bg-ink-50/50 px-4 py-3">
      <p className="text-sm leading-relaxed text-ink-800">{claim.claim}</p>
      <SourceTag claim={claim} />
    </div>
  );
}

export function Section({
  n,
  title,
  icon,
  children,
}: {
  n: number;
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="card p-6">
      <h2 className="section-title">
        <span className="grid h-7 w-7 place-items-center rounded-lg bg-brand-600/10 text-xs font-bold text-brand-700">
          {n}
        </span>
        {title}
      </h2>
      <div className="mt-4 space-y-3">{children}</div>
    </section>
  );
}

export function ConfidenceBadge({ c }: { c: Confidence }) {
  return <span className={`chip ${CONF_STYLE[c]}`}>research: {c}</span>;
}
