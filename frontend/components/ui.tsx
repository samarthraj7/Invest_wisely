import type { Claim, Confidence, Severity } from "@/lib/types";

const CONF_STYLE: Record<Confidence, string> = {
  high: "bg-emerald-50 text-emerald-700",
  medium: "bg-amber-50 text-amber-700",
  low: "bg-orange-50 text-orange-700",
  inconclusive: "bg-ink-100 text-ink-500",
};

const SRC_STYLE: Record<string, string> = {
  deck: "bg-brand-50 text-brand-700",
  web: "bg-sky-50 text-sky-700",
  enrichment: "bg-violet-400/10 text-violet-600",
  inference: "bg-ink-100 text-ink-500",
};

export const SEV_STYLE: Record<Severity, { dot: string; text: string; bg: string }> = {
  critical: { dot: "bg-red-600", text: "text-red-700", bg: "bg-red-50 border-red-200" },
  high: { dot: "bg-red-500", text: "text-red-600", bg: "bg-red-50/70 border-red-200" },
  medium: { dot: "bg-amber-500", text: "text-amber-700", bg: "bg-amber-50 border-amber-200" },
  low: { dot: "bg-lime-500", text: "text-lime-700", bg: "bg-lime-50 border-lime-200" },
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

export function SourceTag({ claim }: { claim: Claim }) {
  return (
    <span className="mt-1.5 flex flex-wrap items-center gap-1.5">
      <span className={`chip ${SRC_STYLE[claim.source_type] ?? "bg-ink-100 text-ink-500"}`}>
        {claim.source_type}
      </span>
      {isUrl(claim.source_ref) ? (
        <a href={claim.source_ref} target="_blank" rel="noreferrer" className="text-xs text-brand-600 underline decoration-dotted underline-offset-2 hover:text-brand-700">
          {claim.source_ref.replace(/^https?:\/\//, "").slice(0, 42)}
        </a>
      ) : (
        <span className="text-xs font-medium text-ink-400">{claim.source_ref}</span>
      )}
      <span className={`chip ${CONF_STYLE[claim.confidence]}`}>{claim.confidence}</span>
    </span>
  );
}

export function ClaimRow({ claim }: { claim: Claim }) {
  return (
    <div className="rounded-xl border border-ink-100 bg-ink-50/40 px-4 py-3 transition hover:border-ink-200">
      <p className="text-sm leading-relaxed text-ink-800">{claim.claim}</p>
      <SourceTag claim={claim} />
    </div>
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
  return <span className={`chip ${CONF_STYLE[c]}`}>research: {c}</span>;
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
