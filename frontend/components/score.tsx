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
  company: "#4f46e5",
  team: "#10b981",
  founder: "#34d399",
  market: "#0ea5e9",
  competitor: "#f59e0b",
  valuation: "#8b5cf6",
  traction: "#14b8a6",
  legitimacy: "#6366f1",
  delivery: "#ec4899",
  risk: "#ef4444",
};

const EDGE_COLOR: Record<string, string> = {
  support: "#34d399",
  pressure: "#f87171",
  neutral: "#cbd5e1",
};

const PRIMARY = ["team", "market", "traction", "valuation", "legitimacy", "delivery"];

type GNode = KnowledgeGraph["nodes"][number];
type Pt = { x: number; y: number };

export function KnowledgeGraphView({ graph }: { graph: KnowledgeGraph }) {
  if (!graph || graph.nodes.length === 0) return null;

  const W = 760;
  const H = 540;
  const cx = W / 2;
  const cy = H / 2;
  const R1 = 138; // pillar ring
  const R2 = 232; // satellite ring

  const center = graph.nodes.find((n) => n.id === "company") ?? graph.nodes[0];
  const primaries = graph.nodes.filter((n) => n.id !== center.id && PRIMARY.includes(n.type));
  const secondaries = graph.nodes.filter((n) => n.id !== center.id && !PRIMARY.includes(n.type));

  const pos: Record<string, Pt> = { [center.id]: { x: cx, y: cy } };
  const angleOf: Record<string, number> = {};
  primaries.forEach((n, i) => {
    const a = (i / Math.max(1, primaries.length)) * 2 * Math.PI - Math.PI / 2;
    angleOf[n.id] = a;
    pos[n.id] = { x: cx + R1 * Math.cos(a), y: cy + R1 * Math.sin(a) };
  });

  // Each satellite (founder/competitor/risk) is anchored near the pillar it links to.
  const anchorOf = (id: string): string => {
    const out = graph.edges.find((e) => e.source === id);
    if (out && angleOf[out.target] != null) return out.target;
    const inc = graph.edges.find((e) => e.target === id);
    if (inc && angleOf[inc.source] != null) return inc.source;
    return center.id;
  };
  const groups: Record<string, GNode[]> = {};
  secondaries.forEach((n) => {
    const a = anchorOf(n.id);
    (groups[a] ||= []).push(n);
  });
  Object.entries(groups).forEach(([anchor, list]) => {
    const base = angleOf[anchor] ?? -Math.PI / 2;
    const spread = Math.min(0.9, 0.32 * list.length);
    list.forEach((n, i) => {
      const off = list.length === 1 ? 0 : (i / (list.length - 1) - 0.5) * spread;
      const a = base + off;
      pos[n.id] = { x: cx + R2 * Math.cos(a), y: cy + R2 * Math.sin(a) };
    });
  });

  const radOf = (n: GNode) =>
    n.id === center.id ? 30 : n.type === "team" ? 24 : PRIMARY.includes(n.type) ? 19 : 11;
  const nodeColor = (n: GNode) =>
    typeof n.score === "number" ? scoreHex(n.score) : NODE_COLOR[n.type] ?? "#94a3b8";

  return (
    <div className="overflow-x-auto rounded-2xl border border-ink-100 bg-gradient-to-b from-ink-50/60 to-white p-2">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" style={{ minWidth: 560 }}>
        <defs>
          <marker id="arrow-support" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" fill={EDGE_COLOR.support} />
          </marker>
          <marker id="arrow-pressure" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" fill={EDGE_COLOR.pressure} />
          </marker>
          <radialGradient id="gcenter" cx="50%" cy="40%" r="65%">
            <stop offset="0%" stopColor="#818cf8" />
            <stop offset="100%" stopColor="#4f46e5" />
          </radialGradient>
        </defs>

        {graph.edges.map((e, i) => {
          const a = pos[e.source];
          const b = pos[e.target];
          if (!a || !b) return null;
          const pol = e.polarity ?? "neutral";
          const col = EDGE_COLOR[pol] ?? "#cbd5e1";
          const w = 1 + 2.8 * (e.weight ?? 0.4);
          // bowed quadratic curve for a cleaner, less tangled look
          const mx = (a.x + b.x) / 2;
          const my = (a.y + b.y) / 2;
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const len = Math.hypot(dx, dy) || 1;
          const bow = 14;
          const ctrl = { x: mx - (dy / len) * bow, y: my + (dx / len) * bow };
          // trim endpoint so the arrow sits just outside the target node
          const tnode = graph.nodes.find((n) => n.id === e.target)!;
          const tr = radOf(tnode) + 5;
          const vx = b.x - ctrl.x;
          const vy = b.y - ctrl.y;
          const vlen = Math.hypot(vx, vy) || 1;
          const ex = b.x - (vx / vlen) * tr;
          const ey = b.y - (vy / vlen) * tr;
          return (
            <path
              key={i}
              d={`M${a.x},${a.y} Q${ctrl.x},${ctrl.y} ${ex},${ey}`}
              fill="none"
              stroke={col}
              strokeWidth={w}
              strokeDasharray={pol === "pressure" ? "5 4" : undefined}
              markerEnd={pol === "pressure" ? "url(#arrow-pressure)" : "url(#arrow-support)"}
              opacity={0.7}
            />
          );
        })}

        {graph.nodes.map((n) => {
          const p = pos[n.id];
          if (!p) return null;
          const isCenter = n.id === center.id;
          const color = isCenter ? "url(#gcenter)" : nodeColor(n);
          const rad = radOf(n);
          const scored = typeof n.score === "number";
          const labelMax = isCenter ? 22 : PRIMARY.includes(n.type) ? 16 : 14;
          return (
            <g key={n.id}>
              <title>
                {`${n.label}${scored ? ` — ${n.score}/100` : n.detail ? ` — ${n.detail}` : ""}${
                  n.rationale ? `\n${n.rationale}` : ""
                }`}
              </title>
              {/* white halo for separation */}
              <circle cx={p.x} cy={p.y} r={rad + 2.5} fill="#fff" />
              <circle cx={p.x} cy={p.y} r={rad} fill={color} opacity={isCenter ? 1 : 0.95} />
              {scored && (
                <text x={p.x} y={p.y + 4} textAnchor="middle" fill="#fff" style={{ fontSize: isCenter ? 16 : 12, fontWeight: 800 }}>
                  {n.score}
                </text>
              )}
              <text
                x={p.x}
                y={p.y + rad + 13}
                textAnchor="middle"
                className={isCenter ? "fill-ink-900" : "fill-ink-600"}
                style={{
                  fontSize: isCenter ? 13 : PRIMARY.includes(n.type) ? 11 : 10,
                  fontWeight: isCenter ? 700 : 500,
                  paintOrder: "stroke",
                  stroke: "#fff",
                  strokeWidth: 3,
                  strokeLinejoin: "round",
                }}
              >
                {n.label.length > labelMax ? n.label.slice(0, labelMax - 1) + "…" : n.label}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 px-2 pb-1">
        <span className="flex items-center gap-1.5 text-[11px] text-ink-400">
          <span className="inline-block h-0.5 w-5 rounded" style={{ background: EDGE_COLOR.support }} /> supports →
        </span>
        <span className="flex items-center gap-1.5 text-[11px] text-ink-400">
          <span className="inline-block h-0.5 w-5 rounded border-t border-dashed" style={{ borderColor: EDGE_COLOR.pressure }} /> pressures →
        </span>
        <span className="text-[11px] text-ink-300">· node fill = score (red→green); size = weight; hover for detail</span>
      </div>
    </div>
  );
}
