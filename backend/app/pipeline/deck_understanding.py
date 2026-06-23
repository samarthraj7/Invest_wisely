"""Step 2 - Deck understanding (LLM).

Turns raw parsed text into structured deck facts, where EVERY fact is tagged
with the page number it came from. In mock mode, returns a deterministic,
realistic structure so the rest of the pipeline can be exercised.
"""
from __future__ import annotations

from typing import Any

from ..clients.llm import get_llm
from .parse import ParsedDeck

_SYSTEM = (
    "You are a meticulous VC analyst extracting structured facts from a startup "
    "pitch deck. Extract ONLY what the deck states. For every fact, record the "
    "page number it appears on. Do not infer or embellish. If something is not "
    "in the deck, omit it."
)

_SCHEMA_HINT = """
Return JSON with this shape:
{
  "company": {"name": str, "one_liner": str, "sector": str|null,
              "stage": str|null, "location": str|null, "ask": str|null},
  "deck_claims": [{"claim": str, "page": int}],
  "market_claims": [{"claim": str, "page": int}],
  "team": [{"name": str, "title": str|null, "linkedin_url": str|null, "page": int}],
  "competitors_named": [str]
}
"""


def understand_deck(deck: ParsedDeck) -> dict[str, Any]:
    prompt = (
        f"{_SCHEMA_HINT}\n\nDECK FILENAME: {deck.filename}\n"
        f"TOTAL PAGES: {len(deck.slides)}  EMBEDDED IMAGES: {deck.total_images}\n\n"
        f"DECK CONTENT:\n{deck.full_text[:18000]}"
    )
    return get_llm().complete_json(
        system=_SYSTEM,
        prompt=prompt,
        mock=_mock_understanding(deck),
    )


def _mock_understanding(deck: ParsedDeck) -> dict[str, Any]:
    """Deterministic stand-in shaped like a real seed-stage B2B SaaS deck."""
    return {
        "company": {
            "name": "NimbusGrid",
            "one_liner": "AI-driven load balancing for industrial battery storage sites.",
            "sector": "Climate / Energy SaaS",
            "stage": "Seed",
            "location": "Austin, TX",
            "ask": "Raising $4M seed at $20M post-money",
        },
        "deck_claims": [
            {"claim": "Reduces grid-storage operating costs by 30%", "page": 3},
            {"claim": "$1.2M ARR with 8 enterprise pilots", "page": 5},
            {"claim": "Proprietary forecasting model is '10x more accurate'", "page": 6},
            {"claim": "Targeting $48B grid-storage software market by 2030", "page": 4},
        ],
        "market_claims": [
            {"claim": "Grid-storage software TAM of $48B by 2030", "page": 4},
            {"claim": "No direct competitor offers real-time AI dispatch", "page": 7},
        ],
        "team": [
            {"name": "Dana Okafor", "title": "CEO & Co-founder",
             "linkedin_url": None, "page": 9},
            {"name": "Marc Liang", "title": "CTO & Co-founder",
             "linkedin_url": None, "page": 9},
        ],
        "competitors_named": ["Stem Inc", "Fluence"],
        "_mock": True,
    }
