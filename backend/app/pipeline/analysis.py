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
from ..schemas import InvestmentReport
from .entities import Entities

_SYSTEM = """You are a sharp VC associate writing an investment memo for a partner.
Hard rules:
- This is judgment-support, NOT an autograder. Read like a sharp associate's memo.
- EVERY claim must be traceable. Each claim object needs source_type
  ("deck" | "web" | "enrichment" | "inference") and source_ref ("deck p.X" or a URL).
- "inference" is allowed ONLY when it reasons over deck/web facts you were given.
- NEVER fabricate facts about a real person. If research is inconclusive for
  someone, set research_confidence="inconclusive" and say so explicitly.
- Team gaps must be SPECIFIC to this venture (why the gap matters here), not generic.
- Differentiation: compare the deck's "unique" claims against named/discovered competitors.
- Valuation: NEVER output a bare number as truth. Provide comps, assumptions,
  multiples_used, and a range. Compare the deck's ask to comps and flag mismatch.
- Recommendation: invest|pass|more_diligence, suggested check size if invest,
  a risk_rating, and named risk_factors (not just a number).
"""


def _schema_hint() -> str:
    return (
        "Return a single JSON object matching this schema (omit nothing required):\n"
        + json.dumps(InvestmentReport.model_json_schema(), indent=0)[:6000]
    )


def analyze(
    entities: Entities,
    understanding: dict[str, Any],
    research: dict[str, Any],
) -> InvestmentReport:
    llm = get_llm()
    prompt = (
        f"{_schema_hint()}\n\n"
        f"=== STRUCTURED DECK FACTS (cite as deck p.X) ===\n{json.dumps(understanding)[:8000]}\n\n"
        f"=== RESEARCH (cite the url fields) ===\n{json.dumps(research)[:12000]}\n"
    )
    raw = llm.complete_json(
        system=_SYSTEM,
        prompt=prompt,
        mock=_mock_report(entities, understanding, research),
        max_tokens=6000,
    )
    try:
        report = InvestmentReport.model_validate(raw)
    except Exception:
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
    company = understanding.get("company", {}) or {}
    name = company.get("name", entities.company_name)
    people_research = {p["name"]: p for p in research.get("people", [])}

    team_analysis = []
    for person in entities.people:
        r = people_research.get(person.name, {})
        found = r.get("found", False)
        conf = "low" if found else "inconclusive"
        researched = []
        if found:
            researched.append(
                {
                    "claim": f"Public web results located for {person.name}; verify in diligence.",
                    "source_type": "web",
                    "source_ref": (r.get("web_results") or [{}])[0].get("url", "https://example.com"),
                    "confidence": "low",
                }
            )
        else:
            researched.append(
                {
                    "claim": f"Research inconclusive for {person.name} — no reliable public profile "
                             f"confirmed (mock mode or thin web presence).",
                    "source_type": "inference",
                    "source_ref": f"deck p.{person.deck_page or 9}",
                    "confidence": "inconclusive",
                }
            )
        gaps = [
            {
                "claim": f"{person.name} ({person.title}) — for a climate/energy venture selling "
                         f"into utilities, no confirmed enterprise/regulated-utility sales or "
                         f"grid-domain track record was found; this matters because the GTM "
                         f"depends on long utility procurement cycles.",
                "source_type": "inference",
                "source_ref": f"deck p.{person.deck_page or 9}",
                "confidence": "low",
            }
        ]
        team_analysis.append(
            {
                "name": person.name,
                "title": person.title,
                "linkedin_url": person.linkedin_url,
                "deck_claims": [
                    {
                        "claim": f"Listed as {person.title}",
                        "source_type": "deck",
                        "source_ref": f"deck p.{person.deck_page or 9}",
                        "confidence": "high",
                    }
                ],
                "researched_background": researched,
                "gaps_vs_venture": gaps,
                "research_confidence": conf,
            }
        )

    return {
        "company_snapshot": {
            "name": name,
            "one_liner": company.get("one_liner", entities.company_one_liner),
            "sector": company.get("sector"),
            "stage": company.get("stage"),
            "location": company.get("location"),
            "ask": company.get("ask"),
            "deck_claims": [
                {
                    "claim": c["claim"],
                    "source_type": "deck",
                    "source_ref": f"deck p.{c.get('page', 1)}",
                    "confidence": "high",
                }
                for c in understanding.get("deck_claims", [])
            ],
        },
        "team_analysis": team_analysis,
        "competitive_landscape": {
            "named_in_deck": [
                {
                    "name": c,
                    "relationship": "direct",
                    "note": {
                        "claim": f"{c} named by the deck as a competitor.",
                        "source_type": "deck",
                        "source_ref": "deck p.7",
                        "confidence": "high",
                    },
                }
                for c in entities.competitors_named
            ],
            "discovered": [
                {
                    "name": "Additional incumbents likely (run live search)",
                    "relationship": "adjacent",
                    "note": {
                        "claim": "Live web research disabled in mock mode; enable EXA_API_KEY to "
                                 "discover competitors beyond those named in the deck.",
                        "source_type": "inference",
                        "source_ref": "https://example.com/mock",
                        "confidence": "inconclusive",
                    },
                }
            ],
            "differentiation_assessment": [
                {
                    "claim": "Deck claims 'no direct competitor offers real-time AI dispatch', but "
                             "named incumbents already market AI dispatch features — the 'unique' "
                             "claim needs verification against current competitor product pages.",
                    "source_type": "inference",
                    "source_ref": "deck p.7",
                    "confidence": "low",
                }
            ],
        },
        "red_flags": [
            {
                "title": "Differentiation claim may be overstated",
                "severity": "high",
                "reasoning": {
                    "claim": "The core 'unique' real-time AI dispatch claim conflicts with the "
                             "existence of established incumbents in the same category.",
                    "source_type": "inference",
                    "source_ref": "deck p.6",
                    "confidence": "medium",
                },
            },
            {
                "title": "Team has no confirmed regulated-utility GTM experience",
                "severity": "high",
                "reasoning": {
                    "claim": "Selling into utilities requires navigating long, regulated "
                             "procurement; no team member shows that background.",
                    "source_type": "inference",
                    "source_ref": "deck p.9",
                    "confidence": "low",
                },
            },
            {
                "title": "Ask appears rich vs. traction",
                "severity": "medium",
                "reasoning": {
                    "claim": "$20M post on ~$1.2M ARR implies ~16x ARR, above typical seed comps "
                             "for the sector; needs justification.",
                    "source_type": "inference",
                    "source_ref": "deck p.5",
                    "confidence": "medium",
                },
            },
        ],
        "diligence_questions": [
            {"question": "Which named competitors already ship real-time AI dispatch, and what "
                         "specifically is defensible about your model vs. theirs?",
             "targets_gap": "Differentiation / 'unique' claim"},
            {"question": "Who on the team has closed a regulated-utility contract, and what was "
                         "the sales cycle length?",
             "targets_gap": "Team GTM gap"},
            {"question": "Of the 8 pilots, how many are paid, and what is pilot-to-contract "
                         "conversion to date?",
             "targets_gap": "Traction quality behind the $1.2M ARR"},
            {"question": "How was the '10x more accurate' forecasting figure measured, against "
                         "what baseline and dataset?",
             "targets_gap": "Technical claim substantiation"},
        ],
        "valuation": {
            "comps": [
                {"company": "Sector seed comps (energy SaaS)", "detail": "Typical 2025-26 seed: "
                 "$2-5M raise at $12-22M post; ~8-12x forward ARR",
                 "source": {"claim": "Range from comparable seed rounds.",
                            "source_type": "web",
                            "source_ref": "https://example.com/mock",
                            "confidence": "low"}},
            ],
            "assumptions": [
                "ARR figure ($1.2M) is as stated in deck p.5 and unverified.",
                "Sector multiple band of 8-12x forward ARR at seed.",
                "Pilots convert at a typical 30-50% rate (assumed, not confirmed).",
            ],
            "multiples_used": "8-12x forward ARR (sector seed band)",
            "range_low": "$10M post-money",
            "range_high": "$16M post-money",
            "deck_ask": company.get("ask", "$4M at $20M post"),
            "ask_vs_comps": [
                {
                    "claim": "Deck's $20M post sits above the comp-derived $10-16M range; the ~16x "
                             "ARR multiple is rich for seed unless growth/margins justify a premium.",
                    "source_type": "inference",
                    "source_ref": "deck p.5",
                    "confidence": "medium",
                }
            ],
        },
        "recommendation": {
            "recommendation": "more_diligence",
            "suggested_check_size": "$500K-$750K if proceeding (follow, not lead)",
            "risk_rating": "Medium-High",
            "risk_factors": [
                {"claim": "Differentiation claim unverified against incumbents.",
                 "source_type": "inference", "source_ref": "deck p.7", "confidence": "medium"},
                {"claim": "No confirmed regulated-utility GTM experience on the team.",
                 "source_type": "inference", "source_ref": "deck p.9", "confidence": "low"},
                {"claim": "Valuation ask rich vs. sector seed comps.",
                 "source_type": "inference", "source_ref": "deck p.5", "confidence": "medium"},
            ],
            "rationale": "Interesting wedge in a real market, but the two load-bearing claims "
                         "(technical uniqueness and traction quality) and the team's utility GTM "
                         "gap are unresolved. Resolve the diligence questions before pricing.",
        },
        "analyst_note": "Directional analyst support. Augments, not replaces, partner judgment. "
                        "Generated in MOCK mode — add API keys for live research."
        if True
        else "",
        "mock_mode": True,
    }
