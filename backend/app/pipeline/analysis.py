"""Step 5 - Critical analysis (LLM) -> InvestmentReport.

The model is given ONLY (a) structured deck facts with page numbers and
(b) research results with source URLs. The system prompt forbids citing
anything outside that set and forbids fabricating facts about real people.
Output is validated against the InvestmentReport schema.
"""
from __future__ import annotations

import json
from typing import Any

from ..clients.llm import get_llm
from ..obs import logger
from ..schemas import InvestmentReport
from .entities import Entities

_SYSTEM = """You are a sharp VC associate writing an investment memo for a partner about
ONE specific company. Everything you write must come from THIS deck and THIS research —
never from templates, prior examples, or assumptions about a "typical" startup.

ABSOLUTE GROUNDING RULES
- Analyze ONLY the company in the inputs below. Use its real name, sector, numbers, and
  people. Do NOT import facts, competitors, valuations, or phrasings from any other company.
- EVERY claim object needs source_type ("deck" | "web" | "enrichment" | "inference") and
  source_ref ("deck p.X" or a real URL from the research). Never invent URLs or pages.
- "inference" is allowed ONLY when it reasons over deck/research facts you were actually given.
- NEVER fabricate facts about a real person. If research on someone is thin/inconclusive,
  set research_confidence="inconclusive" and say so — do not guess their history.

TEAM ANALYSIS (evaluate each person as a whole, not just one angle)
- researched_background: what they have actually done — prior companies/roles, years of
  experience, education, notable achievements or exits (from research/enrichment).
- credentials: judge HARD evidence and its SIGNIFICANCE, not just its existence.
    * papers_count / patents_count / years_experience: best estimate from the research (null if unknown).
    * patent_quality: "substantive" (granted utility patent central to the product),
      "mixed", "trivial" (e.g. a basic design patent of little defensive value), or "unknown".
    * research_quality: highly-cited / strong-venue work vs. obscure or unrelated.
    * notable_achievements: 1-3 SPECIFIC items (a named paper, a granted patent, a real role/exit),
      each as a sourced claim that says why it matters (or why it's weak).
    * assessment: one line — is this a substantive track record or thin?
  Do NOT inflate: 5 obscure papers or a design patent is not the same as deep, relevant work.
- strengths: concrete positive signals for executing THIS plan (domain depth, operating/
  scaling experience, technical credibility, relevant prior wins).
- founder_market_fit: weigh their track record against the SPECIFIC future the deck proposes
  — are they credibly positioned to build and sell this, given what they've done before?
- gaps_vs_venture: specific missing experience that matters for THIS venture (and why).
- Be balanced: a strong operator with one gap is different from a first-timer with many.
- EARLY/STEALTH FOUNDERS: a thin or missing LinkedIn/public profile is NORMAL for
  pre-seed/seed founders and is NOT itself a negative. Do NOT down-rank someone just
  because little is public. Instead, read DEPTH from the enrichment "experiences"
  (roles, companies, seniority, tenure/duration) and from research/papers. Judge what
  they actually did, not how complete their profile is. Only call out inexperience when
  there is a real signal of it — never merely because data is absent (in that case set
  research_confidence="inconclusive" and say the profile is sparse, not weak).
- RESEARCH OUTPUT: weigh publication QUALITY, not just count — venue/journal strength,
  apparent citations/impact, and relevance to THIS venture. A few strong, relevant,
  well-cited papers outweigh many obscure ones; the same for patents (granted utility &
  central to the product vs. a trivial design patent).

TEAM AS A WHOLE (after judging each person, judge the founding team as ONE unit)
- team_assessment: do NOT just restate individuals. Assess how COMPLEMENTARY they are and
  whether, COMBINED, they cover the functions a company at THIS stage needs (e.g. at
  pre-seed/seed: someone who can build the product, someone who can sell/distribute, and
  genuine domain insight). 
    * rating: "strong" | "balanced" | "promising" | "incomplete" | "thin".
    * verdict: one-line headline.
    * summary: 2-4 sentences on combined strength + complementarity + stage fit.
    * covered_skills: the key functions they credibly cover between them.
    * missing_skills: important functions for this stage that look absent/thin (a solo
      technical team with no commercial DNA is a real gap; say so).
    * stage_fit: is this team composition right for where the company is now?

MARKET & DIFFERENTIATION
- Use the research to identify who the real, current competitors are (named in deck AND
  discovered), what those companies actually do today, and how this product differs.
- Stress-test the deck's "unique"/"first"/"only" claims against what competitors already ship.
- Populate competitive_landscape.discovered from research, not from memory.

VALUATION (judge whether the ask is reasonable)
- Provide real comps (from research where possible), assumptions, multiples_used, and a range.
- Explicitly assess whether the deck's ask is in line, rich, or cheap vs comps, and why.
- Never present a single number as truth; show the reasoning.

FUTURE SCOPE (where could this company realistically go?)
- future_scope: the upside case, grounded in the deck + research — adjacent products,
  new segments/geographies, platform/network effects, or expanding TAM. Be realistic,
  not promotional.
    * summary: 2-4 sentences on the realistic future potential.
    * opportunities: concrete, sourced expansion paths.
    * headwinds: what could CAP the scope (market limits, eroding moat, regulation, platform risk).
    * time_horizon: rough horizon for the upside (e.g. "3-5 years").

RECOMMENDATION (weigh many factors before concluding)
- Synthesize across team, market/differentiation, product, traction, and valuation — not a
  single factor. State the load-bearing reasons.
- recommendation = invest | pass | more_diligence; include suggested_check_size if invest,
  a risk_rating, and named risk_factors (each sourced).

CONSOLIDATED SUMMARY
- executive_summary: a 3-6 sentence partner-facing synthesis — what the company does, the
  strongest reason to be interested, the biggest risk, and the bottom-line call. This must be
  consistent with the detailed sections.

OUTPUT BUDGET (be tight — no filler, no repetition; the JSON must be COMPLETE)
- One sentence per claim. Make each point DISTINCT — never restate the same idea across
  background/strengths/fit. If a point fits two buckets, put it in the most relevant one only.
- Caps: <=3 deck_claims in snapshot, <=2 per team bucket (background/strengths/fit/gaps),
  <=2 notable_achievements, <=4 red flags, <=4 diligence questions,
  <=3 differentiation points, <=3 future opportunities, <=3 headwinds.
- Prefer fewer, higher-signal items over many weak ones. Return the FULL valid JSON.
"""


# A compact, hand-written schema beats dumping the full JSON Schema: it costs a
# fraction of the input tokens while still pinning the output shape.
_SCHEMA_HINT = """Return ONE JSON object with EXACTLY these keys. A "claim" object is
{claim, source_type:"deck"|"web"|"enrichment"|"inference", source_ref, confidence:"high"|"medium"|"low"|"inconclusive"}.

{
  "executive_summary": "3-6 sentence consolidated take (what they do, strongest reason to be interested, biggest risk, bottom-line call)",
  "company_snapshot": {name, one_liner, sector, stage, location, ask, deck_claims:[claim]},
  "team_analysis": [{name, title, linkedin_url, deck_claims:[claim],
                     credentials:{years_experience:int|null, papers_count:int|null, patents_count:int|null,
                                  patent_quality:"substantive"|"mixed"|"trivial"|"unknown",
                                  research_quality:"...", notable_achievements:[claim], assessment:"..."},
                     researched_background:[claim], strengths:[claim],
                     founder_market_fit:[claim], gaps_vs_venture:[claim],
                     research_confidence:"high"|"medium"|"low"|"inconclusive"}],
  "team_assessment": {rating:"strong"|"balanced"|"promising"|"incomplete"|"thin", verdict, summary,
                      covered_skills:[str], missing_skills:[str], stage_fit},
  "competitive_landscape": {named_in_deck:[{name, relationship, note:claim}],
                            discovered:[{name, relationship, note:claim}],
                            differentiation_assessment:[claim]},
  "red_flags": [{title, severity:"critical"|"high"|"medium"|"low", reasoning:claim}],
  "diligence_questions": [{question, targets_gap}],
  "valuation": {comps:[{company, detail, source:claim}], assumptions:[str],
                multiples_used, range_low, range_high, deck_ask, ask_vs_comps:[claim]},
  "future_scope": {summary, opportunities:[claim], headwinds:[claim], time_horizon},
  "recommendation": {recommendation:"invest"|"pass"|"more_diligence", suggested_check_size,
                     risk_rating, risk_factors:[claim], rationale}
}
Use null for unknown optional strings. Never invent URLs — only cite source_ref values present in the inputs or "deck p.X"."""


def _trim(results: list, n: int = 3, snippet: int = 320) -> list:
    """Shrink a list of search results to the few fields the analyst needs."""
    out = []
    for r in (results or [])[:n]:
        if isinstance(r, dict):
            out.append(
                {
                    "title": (r.get("title") or "")[:140],
                    "url": r.get("url") or "",
                    "snippet": (r.get("snippet") or "")[:snippet],
                }
            )
    return out


def _compact_research(research: dict[str, Any]) -> dict[str, Any]:
    """Strip the research bundle down to citeable signal before sending to the
    LLM. This is the single biggest lever on input-token cost."""
    company = research.get("company", {}) or {}
    people = []
    for p in research.get("people", []) or []:
        enr = p.get("enrichment") or {}
        enrichment = None
        if enr and enr.get("found"):
            enrichment = {
                "found": True,
                "headline": (enr.get("headline") or "")[:200],
                "summary": (enr.get("summary") or "")[:300],
                "source_url": enr.get("source_url"),
                "experiences": [
                    {
                        "title": (e.get("title") or "")[:120],
                        "company": (e.get("company") or "")[:120],
                        # tenure/duration matters for judging DEPTH on thin profiles
                        "starts_at": e.get("starts_at") or e.get("start"),
                        "ends_at": e.get("ends_at") or e.get("end"),
                        "duration": e.get("duration"),
                        "description": (e.get("description") or "")[:200],
                    }
                    for e in (enr.get("experiences") or [])[:6]
                    if isinstance(e, dict)
                ],
                "education": [
                    {"school": (ed.get("school") or "")[:120], "degree": (ed.get("degree_name") or ed.get("degree") or "")[:120]}
                    for ed in (enr.get("education") or [])[:3]
                    if isinstance(ed, dict)
                ],
            }
        person = {
            "name": p.get("name"),
            "title": p.get("title"),
            "found": p.get("found"),
            "web_results": _trim(p.get("web_results")),
            "papers": _trim(p.get("papers")),
            "patents": _trim(p.get("patents")),
            "enrichment": enrichment,
        }
        # When the person wasn't found directly, the company's own team/about page
        # is the best place to learn who they are — mine it for THIS person.
        if p.get("company_team_signal"):
            person["company_team_page"] = _trim(p.get("company_team_signal"))
        people.append(person)
    competitors = [
        {"name": c.get("name"), "results": _trim(c.get("results"))}
        for c in (research.get("competitors", []) or [])
    ]
    return {
        "company": {
            "company": company.get("company"),
            "overview": _trim(company.get("overview")),
            "market": _trim(company.get("market")),
            "funding_comps": _trim(company.get("funding_comps")),
        },
        "people": people,
        "competitors": competitors,
    }


def analyze(
    entities: Entities,
    understanding: dict[str, Any],
    research: dict[str, Any],
) -> InvestmentReport:
    llm = get_llm()
    prompt = (
        f"{_SCHEMA_HINT}\n\n"
        f"=== STRUCTURED DECK FACTS (cite as deck p.X) ===\n{json.dumps(understanding)[:7000]}\n\n"
        f"=== RESEARCH (cite the url fields) ===\n{json.dumps(_compact_research(research))[:8000]}\n"
    )
    raw = llm.complete_json(
        system=_SYSTEM,
        prompt=prompt,
        mock=_mock_report(entities, understanding, research),
        max_tokens=8000,
        label="analysis",
    )
    try:
        report = InvestmentReport.model_validate(raw)
    except Exception as exc:
        logger.error("[analysis] schema validation failed -> placeholder (%s: %s)",
                     type(exc).__name__, str(exc)[:200])
        report = InvestmentReport.model_validate(
            _mock_report(entities, understanding, research)
        )
    # mock_mode is true if we never had a live model OR a live call failed mid-run.
    report.mock_mode = not llm.usable
    return report


def _mock_report(
    entities: Entities,
    understanding: dict[str, Any],
    research: dict[str, Any],
) -> dict[str, Any]:
    """A deck-DERIVED placeholder used only when live analysis is unavailable.

    Critically, this contains NO invented company-specific analysis. It reflects
    the actual uploaded deck (name, one-liner, claims, real people/competitors)
    and is honest that the automated analysis did not run — so a degraded run can
    never masquerade as a real, different company's memo.
    """
    company = understanding.get("company", {}) or {}
    name = company.get("name") or entities.company_name or "This company"
    people_research = {p.get("name"): p for p in research.get("people", [])}

    def deck_claim(text: str, page, conf: str = "high") -> dict[str, Any]:
        return {
            "claim": text,
            "source_type": "deck",
            "source_ref": f"deck p.{page}" if page else "deck",
            "confidence": conf,
        }

    team_analysis = []
    for person in entities.people:
        r = people_research.get(person.name, {})
        found = bool(r.get("found"))
        researched = []
        if found:
            url = (r.get("web_results") or [{}])[0].get("url", "")
            researched.append(
                {
                    "claim": f"Public results were located for {person.name}; full background "
                             "not analyzed (automated analysis unavailable).",
                    "source_type": "web",
                    "source_ref": url or "deck",
                    "confidence": "low",
                }
            )
        team_analysis.append(
            {
                "name": person.name,
                "title": person.title,
                "linkedin_url": person.linkedin_url,
                "deck_claims": [deck_claim(f"Listed as {person.title or 'team member'}", person.deck_page)],
                "researched_background": researched,
                "strengths": [],
                "founder_market_fit": [],
                "gaps_vs_venture": [],
                "research_confidence": "low" if found else "inconclusive",
            }
        )

    unavailable = {
        "claim": "Automated analysis did not run for this deck, so this section was not "
                 "generated. Re-run with working API keys for a full assessment.",
        "source_type": "inference",
        "source_ref": "deck",
        "confidence": "inconclusive",
    }

    return {
        "executive_summary": (
            f"{name}: automated analysis did not run for this deck, so this is a structural "
            "placeholder built only from the uploaded deck. See the note at the top of the "
            "report for why, then re-run for a full assessment."
        ),
        "company_snapshot": {
            "name": name,
            "one_liner": company.get("one_liner") or entities.company_one_liner,
            "sector": company.get("sector"),
            "stage": company.get("stage"),
            "location": company.get("location"),
            "ask": company.get("ask"),
            "deck_claims": [
                deck_claim(c.get("claim", ""), c.get("page"))
                for c in (understanding.get("deck_claims") or [])
                if c.get("claim")
            ],
        },
        "team_analysis": team_analysis,
        "team_assessment": {
            "rating": "",
            "verdict": "",
            "summary": "Automated team assessment did not run for this deck.",
            "covered_skills": [],
            "missing_skills": [],
            "stage_fit": "",
        },
        "competitive_landscape": {
            "named_in_deck": [
                {
                    "name": c,
                    "relationship": "named in deck",
                    "note": deck_claim(f"{c} is named by the deck as a competitor.", None),
                }
                for c in entities.competitors_named
            ],
            "discovered": [],
            "differentiation_assessment": [unavailable],
        },
        "red_flags": [],
        "diligence_questions": [],
        "valuation": {
            "comps": [],
            "assumptions": ["Automated valuation analysis did not run for this deck."],
            "multiples_used": None,
            "range_low": None,
            "range_high": None,
            "deck_ask": company.get("ask"),
            "ask_vs_comps": [unavailable],
        },
        "future_scope": {
            "summary": "Automated future-scope analysis did not run for this deck.",
            "opportunities": [],
            "headwinds": [],
            "time_horizon": "",
        },
        "recommendation": {
            "recommendation": "more_diligence",
            "suggested_check_size": None,
            "risk_rating": "Unknown",
            "risk_factors": [],
            "rationale": "This is a structural placeholder built from the uploaded deck — the "
                         "automated analysis did not complete (see the note at the top of the "
                         "report for why). Re-run once live analysis is available.",
        },
        "analyst_note": "Placeholder generated from the deck only; live analysis was unavailable.",
        "mock_mode": True,
    }
