"""Step 7 - Knowledge-graph-driven investment score + risk breakdown.

The score is NOT a flat weighted average of independent factors. It is computed
over an entity GRAPH where nodes (founders, market, traction, valuation,
legitimacy, delivery) influence each other along typed edges:

  * support edges  : a strong source lifts its target
        founders --support--> traction / legitimacy / company
        traction --support--> valuation        (traction justifies the ask)
  * pressure edges : a strong source drags its target down
        competitors --pressure--> market       (tough rivals weaken differentiation)
        risks       --pressure--> legitimacy

So "if one node is good, the next related node benefits" (and vice-versa). The
LLM only scores each node 0-100; the interlinking + the final 0-100 are
deterministic, logged Python — explainable and reproducible.
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

# Pillar importance in the overall score (renormalized over whatever is present;
# delivery is dropped when there's no pitch recording).
_PILLAR_WEIGHTS = {
    "founders": 0.26,
    "market": 0.18,
    "traction": 0.18,
    "valuation": 0.14,
    "legitimacy": 0.14,
    "delivery": 0.10,
}
_SEV_PRESSURE = {"critical": 14.0, "high": 9.0, "medium": 4.0, "low": 1.0}

_SYSTEM = """You are an investment committee scoring ONE startup you have just analyzed, using
ONLY the memo digest provided. Score each entity 0-100 for THIS company:
  80-100 exceptional / strong evidence; 60-79 solid; 40-59 mixed/unproven; 20-39 weak; 0-19 poor.
Be critical and evidence-based; thin or unverifiable claims pull scores DOWN.

IMPORTANT on founders: a sparse or missing public/LinkedIn profile is NORMAL for early
startups and is NOT a negative on its own. Judge DEPTH from their experiences (roles,
companies, tenure) and from research output (publication QUALITY/venue/citations, patent
significance), not from how public they are. Reward demonstrated, relevant work.

For competitors, output a THREAT score 0-100 (how much each threatens this startup).
Decompose risk along: legitimacy (verifiable/real?), valuation (ask justified?),
revenue (traction reality/durability), future_plan (roadmap & use-of-funds credibility),
and impact (how these combine + what would change the call). Return STRICT JSON only."""


def _schema_hint(founders: list[str], competitors: list[str], include_delivery: bool) -> str:
    delivery_line = '  "delivery": {"score":0-100,"rationale":"one line"},\n' if include_delivery else ""
    return (
        "Return ONE JSON object (scores are integers 0-100):\n{\n"
        '  "founders": [{"name":"<as given>","score":0-100,"rationale":"one line"}],\n'
        '  "market": {"score":0-100,"rationale":"one line (market size + differentiation)"},\n'
        '  "traction": {"score":0-100,"rationale":"one line"},\n'
        '  "valuation": {"score":0-100,"rationale":"one line"},\n'
        '  "legitimacy": {"score":0-100,"rationale":"one line"},\n'
        + delivery_line +
        '  "competitors": [{"name":"<as given>","threat":0-100,"rationale":"one line"}],\n'
        '  "risk": {"legitimacy":"...","valuation":"...","revenue":"...","future_plan":"...","impact":"..."},\n'
        '  "rationale": "2-3 sentence justification of the overall score"\n}\n'
        f"founders to score (in order): {founders}\n"
        f"competitors to score (in order): {competitors}"
    )


def _clamp(x: float) -> int:
    return int(round(max(0.0, min(100.0, x))))


def _claim_texts(claims, n: int = 4) -> list[str]:
    return [c.claim for c in (claims or [])[:n] if getattr(c, "claim", "")]


def _memo_digest(report: InvestmentReport) -> dict[str, Any]:
    s = report.company_snapshot
    team = []
    for m in report.team_analysis:
        cr = m.credentials
        team.append({
            "name": m.name, "title": m.title,
            "research_confidence": m.research_confidence.value,
            "credentials": {
                "years_experience": cr.years_experience,
                "papers_count": cr.papers_count, "patents_count": cr.patents_count,
                "patent_quality": cr.patent_quality, "research_quality": cr.research_quality,
                "assessment": cr.assessment,
            },
            "background": _claim_texts(m.researched_background, 3),
            "strengths": _claim_texts(m.strengths), "gaps": _claim_texts(m.gaps_vs_venture),
        })
    ta = report.team_assessment
    return {
        "company": {"name": s.name, "one_liner": s.one_liner, "sector": s.sector,
                    "stage": s.stage, "ask": s.ask},
        "executive_summary": report.executive_summary,
        "team": team,
        "team_assessment": {"rating": ta.rating, "verdict": ta.verdict,
                            "covered_skills": ta.covered_skills, "missing_skills": ta.missing_skills,
                            "stage_fit": ta.stage_fit},
        "differentiation": _claim_texts(report.competitive_landscape.differentiation_assessment),
        "valuation": {"range": f"{report.valuation.range_low} - {report.valuation.range_high}",
                      "deck_ask": report.valuation.deck_ask,
                      "ask_vs_comps": _claim_texts(report.valuation.ask_vs_comps)},
        "red_flags": [{"severity": f.severity.value, "title": f.title} for f in report.red_flags],
        "recommendation": {"call": report.recommendation.recommendation.value,
                           "risk_rating": report.recommendation.risk_rating},
        "delivery": {"available": report.delivery.available, "clarity": report.delivery.clarity,
                     "handling_of_questions": report.delivery.handling_of_questions},
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
    founders = [m.name for m in report.team_analysis if m.name]
    competitors = [c.name for c in report.competitive_landscape.named_in_deck
                   + report.competitive_landscape.discovered if c.name]

    if not llm.usable:
        logger.info("[scoring] LLM not usable -> unscored placeholder + structural graph")
        return InvestmentScore(
            overall=0, verdict="Not scored", factors=[],
            risk=RiskBreakdown(impact="Scoring did not run (live analysis unavailable)."),
            rationale="The 0-100 score was not generated because automated analysis did not run.",
            graph=_structural_graph(report), scored=False,
        )

    import json

    prompt = (f"{_schema_hint(founders, competitors, include_delivery)}\n\n"
              f"=== MEMO DIGEST ===\n{json.dumps(_memo_digest(report))[:7000]}")
    raw = llm.complete_json(system=_SYSTEM, prompt=prompt,
                            mock={"founders": [], "competitors": [], "risk": {}, "rationale": ""},
                            max_tokens=2200, label="scoring")

    # ---- base scores from the model ----
    def pillar(key: str, default: int = 50) -> tuple[int, str]:
        d = raw.get(key) or {}
        try:
            sc = _clamp(float(d.get("score", default)))
        except (TypeError, ValueError):
            sc = default
        return sc, str(d.get("rationale") or "")

    founder_scores: list[tuple[str, int, str]] = []
    for i, name in enumerate(founders):
        fin = (raw.get("founders") or [])
        item = fin[i] if i < len(fin) and isinstance(fin[i], dict) else {}
        try:
            fsc = _clamp(float(item.get("score", 50)))
        except (TypeError, ValueError):
            fsc = 50
        founder_scores.append((name, fsc, str(item.get("rationale") or "")))
    founder_avg = round(sum(s for _, s, _ in founder_scores) / len(founder_scores)) if founder_scores else 50

    # Team-AS-A-WHOLE adjustment: a strong, complementary team lifts the founder
    # pillar; missing core functions for the stage drag it down. This is what makes
    # "the team" a node distinct from the average of individuals.
    ta = report.team_assessment
    rating_adj = {"strong": 6.0, "balanced": 3.0, "promising": 2.0,
                  "incomplete": -5.0, "thin": -9.0}.get((ta.rating or "").strip().lower(), 0.0)
    gap_adj = -3.0 * min(len(ta.missing_skills), 4)
    team_adj = max(-15.0, min(10.0, rating_adj + gap_adj))
    founder_eff = _clamp(founder_avg + team_adj)

    threats: list[tuple[str, int, str]] = []
    for i, name in enumerate(competitors):
        cin = (raw.get("competitors") or [])
        item = cin[i] if i < len(cin) and isinstance(cin[i], dict) else {}
        try:
            tsc = _clamp(float(item.get("threat", 50)))
        except (TypeError, ValueError):
            tsc = 50
        threats.append((name, tsc, str(item.get("rationale") or "")))
    avg_threat = round(sum(t for _, t, _ in threats) / len(threats)) if threats else 50

    market_base, market_rat = pillar("market")
    traction_base, traction_rat = pillar("traction")
    valuation_base, valuation_rat = pillar("valuation")
    legit_base, legit_rat = pillar("legitimacy")
    delivery_base, delivery_rat = pillar("delivery") if include_delivery else (0, "")

    risk_pressure = min(30.0, sum(_SEV_PRESSURE.get(f.severity.value, 0.0) for f in report.red_flags))
    # The TEAM (as a whole) is the source of support that flows into the rest of
    # the graph — strong, complete teams lift execution-dependent pillars.
    founder_support = 0.15 * max(0, founder_eff - 60)
    delivery_support = 0.10 * max(0, delivery_base - 60) if include_delivery else 0.0

    # ---- interlinked (effective) scores ----
    # market is helped a bit by founder-market fit, hurt by competitor threat
    market_eff = _clamp(market_base - 0.4 * (avg_threat - 50) + 0.10 * max(0, founder_eff - 60))
    # traction is driven by team strength AND by market pull
    traction_eff = _clamp(traction_base + founder_support + 0.10 * (market_eff - 50))
    # legitimacy is lent by the team and clear delivery, dragged by risks
    legit_eff = _clamp(legit_base + founder_support + delivery_support - risk_pressure)
    # valuation must be justified by traction
    valuation_eff = _clamp(valuation_base + 0.20 * (traction_eff - 50))
    delivery_eff = delivery_base

    def note(base: int, eff: int, why: str) -> str:
        if eff == base:
            return ""
        return f" (adjusted {eff - base:+d} {why})"

    logger.info("[scoring] base: founders=%d market=%d traction=%d valuation=%d legit=%d | "
                "avg_threat=%d risk_pressure=%.0f", founder_avg, market_base, traction_base,
                valuation_base, legit_base, avg_threat, risk_pressure)
    logger.info("[scoring] eff:  market=%d traction=%d valuation=%d legit=%d",
                market_eff, traction_eff, valuation_eff, legit_eff)

    # ---- weighted overall over present pillars ----
    pillars = {
        "founders": (founder_eff, "Team & founders"),
        "market": (market_eff, "Market & differentiation"),
        "traction": (traction_eff, "Traction & revenue"),
        "valuation": (valuation_eff, "Valuation reasonableness"),
        "legitimacy": (legit_eff, "Company legitimacy"),
    }
    if include_delivery:
        pillars["delivery"] = (delivery_eff, "Pitch delivery")
    total_w = sum(_PILLAR_WEIGHTS[k] for k in pillars)
    overall = _clamp(sum(val * _PILLAR_WEIGHTS[k] for k, (val, _) in pillars.items()) / total_w)

    team_rat = (ta.verdict or ta.summary or
                (founder_scores[0][2] if founder_scores else "No founders were identified in the deck."))
    factors = [
        ScoreFactor(key="founders", name="Team & founders", score=founder_eff,
                    weight=round(_PILLAR_WEIGHTS["founders"] / total_w, 3),
                    rationale=team_rat + note(founder_avg, founder_eff, "for team composition")),
        ScoreFactor(key="market", name="Market & differentiation", score=market_eff,
                    weight=round(_PILLAR_WEIGHTS["market"] / total_w, 3),
                    rationale=market_rat + note(market_base, market_eff, "for competitor pressure")),
        ScoreFactor(key="traction", name="Traction & revenue", score=traction_eff,
                    weight=round(_PILLAR_WEIGHTS["traction"] / total_w, 3),
                    rationale=traction_rat + note(traction_base, traction_eff, "for founder strength")),
        ScoreFactor(key="valuation", name="Valuation reasonableness", score=valuation_eff,
                    weight=round(_PILLAR_WEIGHTS["valuation"] / total_w, 3),
                    rationale=valuation_rat + note(valuation_base, valuation_eff, "for traction support")),
        ScoreFactor(key="legitimacy", name="Company legitimacy", score=legit_eff,
                    weight=round(_PILLAR_WEIGHTS["legitimacy"] / total_w, 3),
                    rationale=legit_rat + note(legit_base, legit_eff, "for risks/founder strength")),
    ]
    if include_delivery:
        factors.append(ScoreFactor(key="delivery", name="Pitch delivery", score=delivery_eff,
                                    weight=round(_PILLAR_WEIGHTS["delivery"] / total_w, 3),
                                    rationale=delivery_rat))

    graph = _scored_graph(report, overall, founder_scores, founder_eff, team_rat,
                          market_eff, market_rat, traction_eff, valuation_eff, legit_eff,
                          delivery_eff if include_delivery else None, threats)

    risk_in = raw.get("risk") or {}
    score = InvestmentScore(
        overall=overall, verdict=_verdict(overall), factors=factors,
        risk=RiskBreakdown(
            legitimacy=str(risk_in.get("legitimacy") or ""),
            valuation=str(risk_in.get("valuation") or ""),
            revenue=str(risk_in.get("revenue") or ""),
            future_plan=str(risk_in.get("future_plan") or ""),
            impact=str(risk_in.get("impact") or ""),
        ),
        rationale=str(raw.get("rationale") or ""),
        graph=graph, scored=True,
    )
    logger.info("[scoring] OVERALL=%d (%s) from interlinked graph (%d nodes, %d edges)",
                overall, score.verdict, len(graph.nodes), len(graph.edges))
    return score


def _scored_graph(report, overall, founder_scores, founder_eff, team_rat, market_eff, market_rat,
                  traction_eff, valuation_eff, legit_eff, delivery_eff, threats) -> KnowledgeGraph:
    """Build the entity graph that the overall score was computed over.

    The links are the actual correlations used in the math: individual founders
    roll up into a TEAM node; the team supports execution-dependent pillars
    (traction, legitimacy) and founder-market fit (market); traction justifies
    valuation; competitors & risks apply pressure. Everything funnels into the
    company score, so the picture explains the number.
    """
    s = report.company_snapshot
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    def n(nid, label, ntype, score=None, weight=0.0, rationale="", detail=""):
        nodes.append(GraphNode(id=nid, label=(label or "")[:60], type=ntype, score=score,
                               weight=weight, rationale=rationale[:200], detail=detail[:140]))

    def e(src, tgt, rel, polarity, weight):
        edges.append(GraphEdge(source=src, target=tgt, relation=rel,
                               polarity=polarity, weight=round(weight, 2)))

    n("company", s.name or "This company", "company", score=overall, weight=1.0,
      rationale="Weighted blend of the linked pillars below.", detail=s.one_liner)

    # --- Team (as a whole) aggregates the individual founders ---
    ta = report.team_assessment
    team_detail = ta.rating or (f"{len(founder_scores)} founder(s)" if founder_scores else "")
    n("team", "Founding team", "team", score=founder_eff,
      weight=_PILLAR_WEIGHTS["founders"], rationale=team_rat, detail=team_detail)
    e("team", "company", "builds", "support", 0.8)
    e("team", "traction", "executes", "support", 0.4)
    e("team", "legitimacy", "lends credibility", "support", 0.4)
    e("team", "market", "founder-market fit", "support", 0.3)

    for i, (name, sc, rat) in enumerate(founder_scores):
        fid = f"founder{i}"
        n(fid, name, "founder", score=sc, weight=round(_PILLAR_WEIGHTS["founders"] / max(1, len(founder_scores)), 3),
          rationale=rat)
        e(fid, "team", "part of", "support", round(sc / 100, 2))

    n("market", s.sector or "Market", "market", score=market_eff,
      weight=_PILLAR_WEIGHTS["market"], rationale=market_rat)
    e("market", "company", "opportunity for", "support", 0.6)
    e("market", "traction", "demand pulls", "support", 0.3)

    n("traction", "Traction & revenue", "traction", score=traction_eff,
      weight=_PILLAR_WEIGHTS["traction"], rationale="Driven by team execution and market pull.")
    e("traction", "company", "proves", "support", 0.6)
    e("traction", "valuation", "justifies", "support", 0.6)

    n("valuation", s.ask or report.valuation.deck_ask or "Valuation / ask", "valuation",
      score=valuation_eff, weight=_PILLAR_WEIGHTS["valuation"], rationale="Must be supported by traction.")
    e("valuation", "company", "priced at", "support", 0.5)

    n("legitimacy", "Legitimacy", "legitimacy", score=legit_eff,
      weight=_PILLAR_WEIGHTS["legitimacy"], rationale="Lent by the team & clear delivery, dragged by risks.")
    e("legitimacy", "company", "grounds", "support", 0.7)

    if delivery_eff is not None:
        n("delivery", "Pitch delivery", "delivery", score=delivery_eff,
          weight=_PILLAR_WEIGHTS["delivery"], rationale="")
        e("delivery", "company", "communicated by", "support", 0.4)
        e("delivery", "legitimacy", "reinforces", "support", 0.3)

    for i, (name, threat, rat) in enumerate(threats[:5]):
        cid = f"comp{i}"
        n(cid, name, "competitor", score=None, rationale=rat, detail=f"threat {threat}/100")
        e(cid, "market", "competes", "pressure", round(threat / 100, 2))

    for i, f in enumerate([f for f in report.red_flags
                           if f.severity.value in ("critical", "high")][:3]):
        rid = f"risk{i}"
        n(rid, f.title, "risk", score=None, detail=f.severity.value)
        e(rid, "legitimacy", "risk", "pressure", 0.9 if f.severity.value == "critical" else 0.6)

    return KnowledgeGraph(nodes=nodes, edges=edges)


def _structural_graph(report: InvestmentReport) -> KnowledgeGraph:
    """Unscored graph (used when scoring didn't run) — still shows the entity links."""
    s = report.company_snapshot
    nodes: list[GraphNode] = [GraphNode(id="company", label=(s.name or "This company")[:60],
                                        type="company", detail=s.one_liner[:140])]
    edges: list[GraphEdge] = []
    seen = {"company"}

    def add(nid, label, ntype, rel, detail=""):
        if not label or nid in seen:
            return
        seen.add(nid)
        nodes.append(GraphNode(id=nid, label=label[:60], type=ntype, detail=detail[:140]))
        if ntype in ("competitor", "risk"):
            edges.append(GraphEdge(source=nid, target="company", relation=rel, polarity="pressure"))
        else:
            edges.append(GraphEdge(source=nid, target="company", relation=rel, polarity="support"))

    if s.sector:
        add("market", s.sector, "market", "opportunity for")
    for i, m in enumerate(report.team_analysis):
        add(f"founder{i}", m.name, "founder", "founder of", m.title or "")
    for i, c in enumerate(report.competitive_landscape.named_in_deck
                          + report.competitive_landscape.discovered):
        add(f"comp{i}", c.name, "competitor", "competes", c.relationship)
    if s.ask or report.valuation.deck_ask:
        add("valuation", s.ask or report.valuation.deck_ask or "Raise", "valuation", "priced at")
    return KnowledgeGraph(nodes=nodes, edges=edges)


# Back-compat for callers/tests that referenced the old name.
def build_graph(report: InvestmentReport) -> KnowledgeGraph:
    return _structural_graph(report)
