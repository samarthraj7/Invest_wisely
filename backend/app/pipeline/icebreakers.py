"""On-demand common-ground / icebreaker finder.

Given a viewer's background (the investor's own, or anyone's), find GENUINE
overlaps with each founder — shared schools, past employers, cities, technical
domains, research areas, communities — and suggest natural opening lines.

This is an interactive, on-demand step (its own endpoint), not part of the main
pipeline, so you can try it with different people's backgrounds.
"""
from __future__ import annotations

from typing import Any

from ..clients.llm import get_llm
from ..obs import logger
from ..schemas import IcebreakerSet, InvestmentReport

_SYSTEM = """You help an investor find authentic common ground with startup founders before a
meeting, to break the ice naturally. You are given the VIEWER'S background and a set of
FOUNDERS with what is known about them.
Rules:
- Surface only GENUINE overlaps grounded in the provided data: shared schools/universities,
  past employers, cities/regions, technical domains, research areas, prior industries,
  communities, or notable shared experiences.
- Do NOT fabricate overlaps. If there is little or no real common ground with a founder,
  say so honestly in `note` and instead suggest a few topical openers based on that
  founder's actual work (so the user still has something genuine to open with).
- Openers should be short, specific, and natural — questions or remarks a real person would
  use, never generic flattery.
- Keep it concise. Return STRICT JSON only."""

_SCHEMA = """Return ONE JSON object:
{
  "founders": [
    {"founder":"<name>",
     "common_ground":["shared school/employer/city/domain ..."],
     "shared_interests":["..."],
     "openers":["natural opening line or question", "..."],
     "note":"if little/no overlap, say so honestly"}
  ],
  "overall":"cross-team themes or talking points worth raising"
}"""


def _founder_digest(report: InvestmentReport) -> list[dict[str, Any]]:
    out = []
    for m in report.team_analysis:
        cr = m.credentials
        out.append({
            "name": m.name,
            "title": m.title,
            "background": [c.claim for c in m.researched_background[:5] if c.claim],
            "credentials": {
                "years_experience": cr.years_experience,
                "papers_count": cr.papers_count,
                "patents_count": cr.patents_count,
                "assessment": cr.assessment,
            },
            "strengths": [c.claim for c in m.strengths[:3] if c.claim],
        })
    return out


def find_icebreakers(report: InvestmentReport, background: str) -> IcebreakerSet:
    background = (background or "").strip()
    if len(background) < 20:
        return IcebreakerSet(available=False,
                             overall="Add a bit more about your background to find common ground.")
    if not report.team_analysis:
        return IcebreakerSet(available=False,
                             overall="No founders were identified in this deck to compare against.")

    llm = get_llm()
    if not llm.usable:
        reason = llm.last_error or "live analysis is unavailable"
        return IcebreakerSet(available=False, overall=f"Could not generate icebreakers because {reason}.")

    import json

    company = report.company_snapshot.name or "the company"
    prompt = (
        f"{_SCHEMA}\n\n=== VIEWER BACKGROUND ===\n{background[:5000]}\n\n"
        f"=== FOUNDERS OF {company} ===\n{json.dumps(_founder_digest(report))[:6000]}"
    )
    sentinel: dict[str, Any] = {"founders": [], "overall": ""}
    raw = llm.complete_json(system=_SYSTEM, prompt=prompt, mock=sentinel,
                            max_tokens=2000, label="icebreakers")
    if raw is sentinel or not llm.usable:
        reason = llm.last_error or "the model returned no usable result"
        return IcebreakerSet(available=False, overall=f"Could not generate icebreakers ({reason}).")

    try:
        result = IcebreakerSet.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        logger.error("[icebreakers] validation failed (%s)", type(exc).__name__)
        return IcebreakerSet(available=False, overall="Could not parse the icebreaker result; try again.")
    result.available = True
    logger.info("[icebreakers] generated for %d founder(s)", len(result.founders))
    return result
