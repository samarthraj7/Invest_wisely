"""Step 7 - Knowledge graph + 0-100 investment score + risk breakdown.

Runs AFTER the memo is written so it can reason over the finished analysis.

Design choices for trust:
  * The OVERALL score is computed deterministically as a weighted blend of
    per-factor scores. The LLM only scores each factor (0-100) + a one-line
    rationale; the aggregation is transparent Python, not a number the model
    pulled from the air.
  * The knowledge graph is built deterministically from the report entities, so
    the links always reflect what's actually in the memo.
"""
from __future__ import annotations

from typing import Any

from ..clients.llm import get_llm
from ..obs import logger
from ..schemas import (
    GraphEdge,
    GraphNode,
    InvestmentReport,
    InvestmentScore,
    KnowledgeGraph,
    RiskBreakdown,
    ScoreFactor,
)

# (key, display name, weight). Weights sum to 1.0 with delivery; if there's no
# pitch recording, delivery is dropped and the rest are renormalized.
_FACTORS: list[tuple[str, str, float]] = [
    ("team", "Team & founders", 0.25),
    ("market", "Market & differentiation", 0.20),
    ("traction", "Traction & revenue", 0.20),
    ("valuation", "Valuation reasonableness", 0.15),
    ("legitimacy", "Company legitimacy", 0.10),
    ("delivery", "Pitch delivery", 0.10),
]

_SYSTEM = """You are an investment committee scoring ONE startup you have just analyzed.
Score each dimension 0-100 for THIS company using only the memo provided:
- 80-100 exceptional / strong evidence; 60-79 solid; 40-59 mixed/unproven; 20-39 weak; 0-19 poor.
Be critical and evidence-based; thin or unverifiable claims should pull scores DOWN.
Then decompose the risk along: legitimacy (is the company/team/claims verifiable and real?),
valuation (is the ask justified?), revenue (traction reality/durability), future_plan
(credibility of roadmap & use of funds), and impact (how these combine + what would change the call).
Return STRICT JSON only."""


def _schema_hint(include_delivery: bool) -> str:
    factors = ", ".join(f'"{k}"' for k, _, _ in _FACTORS if include_delivery or k != "delivery")
    return (
        "Return ONE JSON object:\n"
        "{\n"
        '  "factors": { ' + factors + ': each -> {"score": 0-100 int, "rationale": "one line"} },\n'
        '  "risk": {"legitimacy":"...","valuation":"...","revenue":"...","future_plan":"...","impact":"..."},\n'
        '  "rationale": "2-3 sentence justification of the overall investment score"\n'
        "}"
    )


def _claim_texts(claims, n: int = 4) -> list[str]:
    return [c.claim for c in (claims or [])[:n] if getattr(c, "claim", "")]


def _memo_digest(report: InvestmentReport) -> dict[str, Any]:
    """Compact, factual digest of the finished memo for the scorer."""
    s = report.company_snapshot
    team = []
    for m in report.team_analysis:
        cr = m.credentials
        team.append({
            "name": m.name,
            "title": m.title,
            "research_confidence": m.research_confidence.value,
            "credentials": {
                "years_experience": cr.years_experience,
                "papers_count": cr.papers_count,
                "patents_count": cr.patents_count,
                "patent_quality": cr.patent_quality,
                "assessment": cr.assessment,
            },
            "strengths": _claim_texts(m.strengths),
            "gaps": _claim_texts(m.gaps_vs_venture),
        })
    return {
        "company": {"name": s.name, "one_liner": s.one_liner, "sector": s.sector,
                    "stage": s.stage, "ask": s.ask},
        "executive_summary": report.executive_summary,
        "team": team,
        "differentiation": _claim_texts(report.competitive_landscape.differentiation_assessment),
        "competitors": [c.name for c in report.competitive_landscape.named_in_deck
                        + report.competitive_landscape.discovered],
        "valuation": {
            "range": f"{report.valuation.range_low} - {report.valuation.range_high}",
            "deck_ask": report.valuation.deck_ask,
            "ask_vs_comps": _claim_texts(report.valuation.ask_vs_comps),
        },
        "red_flags": [{"severity": f.severity.value, "title": f.title} for f in report.red_flags],
        "recommendation": {
            "call": report.recommendation.recommendation.value,
            "risk_rating": report.recommendation.risk_rating,
        },
        "delivery": {
            "available": report.delivery.available,
            "clarity": report.delivery.clarity,
            "handling_of_questions": report.delivery.handling_of_questions,
        },
    }


def _verdict(score: int) -> str:
    if score >= 78:
        return "Strong conviction"
    if score >= 62:
        return "Promising"
    if score >= 45:
        return "Mixed"
    return "Weak"


def compute_score(
    report: InvestmentReport,
    understanding: dict[str, Any],
    research: dict[str, Any],
) -> InvestmentScore:
    llm = get_llm()
    include_delivery = bool(report.delivery and report.delivery.available)
    graph = build_graph(report)

    if not llm.usable:
        logger.info("[scoring] LLM not usable -> unscored placeholder")
        return InvestmentScore(
            overall=0,
            verdict="Not scored",
            factors=[],
            risk=RiskBreakdown(impact="Scoring did not run (live analysis unavailable)."),
            rationale="The 0-100 score was not generated because automated analysis did not run.",
            graph=graph,
            scored=False,
        )

    import json

    prompt = (
        f"{_schema_hint(include_delivery)}\n\n=== MEMO DIGEST ===\n"
        f"{json.dumps(_memo_digest(report))[:7000]}"
    )
    raw = llm.complete_json(
        system=_SYSTEM,
        prompt=prompt,
        mock={"factors": {}, "risk": {}, "rationale": ""},
        max_tokens=1800,
        label="scoring",
    )

    factors_in = raw.get("factors") or {}
    active = [(k, name, w) for k, name, w in _FACTORS if include_delivery or k != "delivery"]
    total_w = sum(w for _, _, w in active) or 1.0

    factors: list[ScoreFactor] = []
    weighted_sum = 0.0
    for key, name, weight in active:
        norm_w = weight / total_w
        fi = factors_in.get(key) or {}
        try:
            sc = int(round(float(fi.get("score", 0))))
        except (TypeError, ValueError):
            sc = 0
        sc = max(0, min(100, sc))
        weighted_sum += sc * norm_w
        factors.append(ScoreFactor(
            key=key, name=name, score=sc, weight=round(norm_w, 3),
            rationale=str(fi.get("rationale") or ""),
        ))

    overall = int(round(weighted_sum))
    risk_in = raw.get("risk") or {}
    score = InvestmentScore(
        overall=overall,
        verdict=_verdict(overall),
        factors=factors,
        risk=RiskBreakdown(
            legitimacy=str(risk_in.get("legitimacy") or ""),
            valuation=str(risk_in.get("valuation") or ""),
            revenue=str(risk_in.get("revenue") or ""),
            future_plan=str(risk_in.get("future_plan") or ""),
            impact=str(risk_in.get("impact") or ""),
        ),
        rationale=str(raw.get("rationale") or ""),
        graph=graph,
        scored=True,
    )
    logger.info("[scoring] overall=%d (%s) across %d factor(s)",
                overall, score.verdict, len(factors))
    return score


def build_graph(report: InvestmentReport) -> KnowledgeGraph:
    """Deterministically link the report's entities into a small knowledge graph."""
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    seen: set[str] = set()

    def add_node(nid: str, label: str, ntype: str, detail: str = "") -> str | None:
        if not label:
            return None
        if nid in seen:
            return nid
        seen.add(nid)
        nodes.append(GraphNode(id=nid, label=label[:60], type=ntype, detail=detail[:140]))
        return nid

    s = report.company_snapshot
    company_id = add_node("company", s.name or "This company", "company", s.one_liner)

    if s.sector:
        add_node("market", s.sector, "market", "Sector / market")
        edges.append(GraphEdge(source=company_id, target="market", relation="operates in"))

    for i, m in enumerate(report.team_analysis):
        nid = add_node(f"founder{i}", m.name, "founder", m.title or "")
        if nid:
            edges.append(GraphEdge(source=nid, target=company_id, relation="founder of"))

    for i, c in enumerate(report.competitive_landscape.named_in_deck
                          + report.competitive_landscape.discovered):
        nid = add_node(f"comp{i}", c.name, "competitor", c.relationship)
        if nid:
            edges.append(GraphEdge(source=company_id, target=nid, relation="competes with"))

    if s.ask or report.valuation.deck_ask:
        add_node("valuation", s.ask or report.valuation.deck_ask or "Raise", "valuation", "Ask / valuation")
        edges.append(GraphEdge(source=company_id, target="valuation", relation="raising"))

    for i, f in enumerate([f for f in report.red_flags
                           if f.severity.value in ("critical", "high")][:3]):
        nid = add_node(f"risk{i}", f.title, "risk", f.severity.value)
        if nid:
            edges.append(GraphEdge(source=company_id, target=nid, relation="risk"))

    return KnowledgeGraph(nodes=nodes, edges=edges)
