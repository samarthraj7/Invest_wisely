import type { InvestmentScore, KnowledgeGraph } from "@/lib/types";

function scoreHex(v: number): string {
  if (v >= 78) return "#10b981"; // emerald
  if (v >= 62) return "#6366f1"; // indigo
  if (v >= 45) return "#f59e0b"; // amber
  return "#ef4444"; // red
}

export function ScoreGauge({ score }: { score: number; }) {
  const r = 52;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score)) / 100;
  const hex = scoreHex(score);
  return (
    <svg width="132" height="132" viewBox="0 0 132 132" className="shrink-0">
      <circle cx="66" cy="66" r={r} fill="none" stroke="#e2e8f0" strokeWidth="10" />
      <circle
        cx="66"
        cy="66"
        r={r}
        fill="none"
        stroke={hex}
        strokeWidth="10"
        strokeLinecap="round"
        strokeDasharray={c}
        strokeDashoffset={c * (1 - pct)}
        transform="rotate(-90 66 66)"
        style={{ transition: "stroke-dashoffset 700ms ease" }}
      />
      <text x="66" y="62" textAnchor="middle" className="fill-ink-900" style={{ fontSize: 30, fontWeight: 800 }}>
        {score}
      </text>
      <text x="66" y="82" textAnchor="middle" className="fill-ink-400" style={{ fontSize: 12 }}>
        / 100
      </text>
    </svg>
  );
}

export function FactorBars({ factors }: { factors: InvestmentScore["factors"] }) {
  if (!factors || factors.length === 0) return null;
  return (
    <div className="space-y-3">
      {factors.map((f) => (
        <div key={f.key}>
          <div className="flex items-baseline justify-between gap-2 text-[13px]">
            <span className="font-medium text-ink-800">{f.name}</span>
            <span className="shrink-0 text-ink-400">
              <span className="font-semibold text-ink-700">{f.score}</span>/100
              <span className="ml-1.5 text-[11px] text-ink-300">· wt {Math.round(f.weight * 100)}%</span>
            </span>
          </div>
          <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-ink-100">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{ width: `${f.score}%`, background: scoreHex(f.score) }}
            />
          </div>
          {f.rationale && <p className="mt-1 text-[12px] leading-relaxed text-ink-500">{f.rationale}</p>}
        </div>
      ))}
    </div>
  );
}

const RISK_AXES: { key: keyof InvestmentScore["risk"]; label: string }[] = [
  { key: "legitimacy", label: "Legitimacy" },
  { key: "valuation", label: "Valuation" },
  { key: "revenue", label: "Revenue" },
  { key: "future_plan", label: "Future plan" },
  { key: "impact", label: "Overall impact" },
];

export function RiskBreakdownView({ risk }: { risk: InvestmentScore["risk"] }) {
  const rows = RISK_AXES.filter((a) => risk[a.key]);
  if (rows.length === 0) return null;
  return (
    <div className="divide-y divide-ink-100 overflow-hidden rounded-xl border border-ink-100">
      {rows.map((a) => (
        <div key={a.key} className="grid grid-cols-[120px_1fr] gap-3 px-4 py-2.5">
          <span className="text-xs font-semibold uppercase tracking-wide text-ink-400">{a.label}</span>
          <span className="text-[13px] leading-relaxed text-ink-700">{risk[a.key]}</span>
        </div>
      ))}
    </div>
  );
}

const NODE_COLOR: Record<string, string> = {
  company: "#6366f1",
  founder: "#10b981",
  market: "#0ea5e9",
  competitor: "#f59e0b",
  valuation: "#8b5cf6",
  traction: "#14b8a6",
  risk: "#ef4444",
};

const EDGE_COLOR: Record<string, string> = {
  support: "#34d399",
  pressure: "#f87171",
  neutral: "#cbd5e1",
};

export function KnowledgeGraphView({ graph }: { graph: KnowledgeGraph }) {
  if (!graph || graph.nodes.length === 0) return null;
  const W = 680;
  const H = 440;
  const cx = W / 2;
  const cy = H / 2;
  const R = 168;

  const center = graph.nodes.find((n) => n.id === "company") ?? graph.nodes[0];
  const others = graph.nodes.filter((n) => n.id !== center.id);
  const pos: Record<string, { x: number; y: number }> = { [center.id]: { x: cx, y: cy } };
  others.forEach((n, i) => {
    const angle = (i / Math.max(1, others.length)) * 2 * Math.PI - Math.PI / 2;
    pos[n.id] = { x: cx + R * Math.cos(angle), y: cy + R * Math.sin(angle) };
  });

  const nodeColor = (n: KnowledgeGraph["nodes"][number]) =>
    typeof n.score === "number" ? scoreHex(n.score) : NODE_COLOR[n.type] ?? "#94a3b8";

  return (
    <div className="overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" style={{ minWidth: 520 }}>
        {graph.edges.map((e, i) => {
          const a = pos[e.source];
          const b = pos[e.target];
          if (!a || !b) return null;
          const col = EDGE_COLOR[e.polarity ?? "neutral"] ?? "#cbd5e1";
          const w = 1 + 2.5 * (e.weight ?? 0.4);
          return (
            <g key={i}>
              <line
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke={col}
                strokeWidth={w}
                strokeDasharray={e.polarity === "pressure" ? "4 3" : undefined}
                opacity={0.75}
              />
            </g>
          );
        })}
        {graph.nodes.map((n) => {
          const p = pos[n.id];
          if (!p) return null;
          const isCenter = n.id === center.id;
          const color = nodeColor(n);
          const rad = isCenter ? 26 : typeof n.score === "number" ? 18 : 13;
          const scored = typeof n.score === "number";
          return (
            <g key={n.id}>
              <title>
                {`${n.label}${scored ? ` — ${n.score}/100` : n.detail ? ` — ${n.detail}` : ""}${
                  n.rationale ? `\n${n.rationale}` : ""
                }`}
              </title>
              <circle cx={p.x} cy={p.y} r={rad} fill={color} opacity={isCenter ? 1 : 0.92} />
              {scored && (
                <text x={p.x} y={p.y + 4} textAnchor="middle" fill="#fff" style={{ fontSize: isCenter ? 15 : 12, fontWeight: 700 }}>
                  {n.score}
                </text>
              )}
              <text
                x={p.x}
                y={p.y + rad + 13}
                textAnchor="middle"
                className={isCenter ? "fill-ink-900" : "fill-ink-600"}
                style={{ fontSize: isCenter ? 13 : 11, fontWeight: isCenter ? 700 : 500 }}
              >
                {n.label.length > 20 ? n.label.slice(0, 19) + "…" : n.label}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1">
        <span className="flex items-center gap-1.5 text-[11px] text-ink-400">
          <span className="inline-block h-0.5 w-4" style={{ background: EDGE_COLOR.support }} /> supports
        </span>
        <span className="flex items-center gap-1.5 text-[11px] text-ink-400">
          <span className="inline-block h-0.5 w-4 border-t border-dashed" style={{ borderColor: EDGE_COLOR.pressure }} /> pressures
        </span>
        <span className="text-[11px] text-ink-300">· node color = score (red→green); ring size = weight</span>
      </div>
    </div>
  );
}
