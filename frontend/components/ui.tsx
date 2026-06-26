import type { Claim, Confidence, Severity } from "@/lib/types";

const CONF_DOT: Record<Confidence, string> = {
  high: "bg-emerald-500",
  medium: "bg-amber-500",
  low: "bg-orange-500",
  inconclusive: "bg-ink-300",
};

const SRC_LABEL: Record<string, string> = {
  deck: "deck",
  web: "web",
  enrichment: "profile",
  inference: "inferred",
};

export const SEV_STYLE: Record<Severity, { dot: string; text: string; bg: string; accent: string }> = {
  critical: { dot: "bg-red-600", text: "text-red-700", bg: "bg-red-50 border-red-200", accent: "border-red-500" },
  high: { dot: "bg-red-500", text: "text-red-600", bg: "bg-red-50/70 border-red-200", accent: "border-red-400" },
  medium: { dot: "bg-amber-500", text: "text-amber-700", bg: "bg-amber-50 border-amber-200", accent: "border-amber-400" },
  low: { dot: "bg-lime-500", text: "text-lime-700", bg: "bg-lime-50 border-lime-200", accent: "border-lime-400" },
};

export const REC_META: Record<string, { label: string; ring: string; bg: string; text: string; bar: string }> = {
  invest: { label: "Invest", ring: "ring-emerald-200", bg: "bg-emerald-50", text: "text-emerald-700", bar: "bg-emerald-500" },
  pass: { label: "Pass", ring: "ring-red-200", bg: "bg-red-50", text: "text-red-700", bar: "bg-red-500" },
  more_diligence: { label: "More diligence", ring: "ring-amber-200", bg: "bg-amber-50", text: "text-amber-700", bar: "bg-amber-500" },
};

export function recMeta(r: string) {
  return REC_META[r] ?? { label: r || "—", ring: "ring-ink-200", bg: "bg-ink-50", text: "text-ink-600", bar: "bg-ink-400" };
}

function isUrl(s: string) {
  return s.startsWith("http://") || s.startsWith("https://");
}

/** A subtle, inline confidence marker — a small colored dot + word, placed at the
 *  END of a point. Never a filled block. */
export function ConfidenceMark({ c, label }: { c: Confidence; label?: string }) {
  return (
    <span
      className="ml-1.5 inline-flex items-baseline gap-1 align-baseline whitespace-nowrap text-[11px] font-medium text-ink-400"
      title={`Confidence: ${c}`}
    >
      <span className={`inline-block h-1.5 w-1.5 translate-y-[-1px] rounded-full ${CONF_DOT[c]}`} />
      {label ? `${label}: ${c}` : c}
    </span>
  );
}

/** The provenance citation, rendered as quiet trailing text (source · link). */
function SourceCite({ claim }: { claim: Claim }) {
  if (!claim.source_ref) return null;
  const src = SRC_LABEL[claim.source_type] ?? claim.source_type;
  return (
    <span className="ml-1.5 inline whitespace-nowrap text-[11px] text-ink-300">
      {isUrl(claim.source_ref) ? (
        <a
          href={claim.source_ref}
          target="_blank"
          rel="noreferrer"
          className="text-brand-500/80 underline decoration-dotted underline-offset-2 hover:text-brand-600"
        >
          {src}↗
        </a>
      ) : (
        <span>{claim.source_ref}</span>
      )}
    </span>
  );
}

/** A single point: bullet dot · text · trailing citation · trailing confidence. */
export function ClaimRow({ claim }: { claim: Claim }) {
  return (
    <li className="group flex gap-2.5">
      <span className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-ink-200 transition group-hover:bg-brand-400" />
      <p className="text-[13.5px] leading-relaxed text-ink-700">
        {claim.claim}
        <SourceCite claim={claim} />
        <ConfidenceMark c={claim.confidence} />
      </p>
    </li>
  );
}

/** Renders an array of claims as a tight, clean bullet list. */
export function ClaimList({ claims }: { claims: Claim[] }) {
  if (!claims || claims.length === 0) return null;
  return (
    <ul className="space-y-1.5">
      {claims.map((c, i) => (
        <ClaimRow key={i} claim={c} />
      ))}
    </ul>
  );
}

// Back-compat: a few call sites still render <SourceTag/> on their own line.
export function SourceTag({ claim }: { claim: Claim }) {
  return (
    <span className="mt-1 flex items-center gap-1.5 text-[11px] text-ink-300">
      <SourceCite claim={claim} />
      <ConfidenceMark c={claim.confidence} />
    </span>
  );
}

export function Section({
  id,
  n,
  title,
  children,
}: {
  id: string;
  n: number;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="card scroll-mt-24 p-6 animate-fade-up">
      <h2 className="section-title">
        <span className="grid h-7 w-7 place-items-center rounded-lg gradient-brand text-xs font-bold text-white">
          {n}
        </span>
        {title}
      </h2>
      <div className="mt-4 space-y-3">{children}</div>
    </section>
  );
}

export function ConfidenceBadge({ c }: { c: Confidence }) {
  return <ConfidenceMark c={c} label="research" />;
}

type BannerKind = "warning" | "info" | "error";
const BANNER_STYLE: Record<BannerKind, string> = {
  warning: "border-amber-200 bg-amber-50 text-amber-900",
  info: "border-brand-100 bg-brand-50 text-brand-700",
  error: "border-red-200 bg-red-50 text-red-800",
};

export function Banner({
  kind = "info",
  title,
  children,
}: {
  kind?: BannerKind;
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`flex items-start gap-3 rounded-2xl border px-4 py-3 text-sm ${BANNER_STYLE[kind]}`}>
      <svg className="mt-0.5 shrink-0" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" /><path d="M12 8v5" /><path d="M12 16h.01" />
      </svg>
      <div>
        {title && <p className="font-semibold">{title}</p>}
        <div className={title ? "mt-0.5" : ""}>{children}</div>
      </div>
    </div>
  );
}
