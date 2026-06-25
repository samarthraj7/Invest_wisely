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
    """Deck-DERIVED stand-in used when the LLM is unavailable.

    Contains no invented company: the name is guessed from the filename and the
    claims are the deck's own first lines. This guarantees a degraded run still
    reflects the uploaded deck rather than a hardcoded sample company.
    """
    name = _guess_name_from_filename(deck.filename)
    claims: list[dict[str, Any]] = []
    for s in deck.slides:
        for line in (s.text or "").splitlines():
            line = line.strip()
            if len(line) >= 12:
                claims.append({"claim": line[:200], "page": s.page})
            if len(claims) >= 12:
                break
        if len(claims) >= 12:
            break

    return {
        "company": {
            "name": name,
            "one_liner": claims[0]["claim"] if claims else "",
            "sector": None,
            "stage": None,
            "location": None,
            "ask": None,
        },
        "deck_claims": claims,
        "market_claims": [],
        "team": [],
        "competitors_named": [],
        "_mock": True,
    }


def _guess_name_from_filename(filename: str) -> str:
    import re

    stem = filename.rsplit(".", 1)[0]
    # Drop a leading uuid_ prefix the API adds.
    stem = re.sub(r"^[0-9a-fA-F-]{8,}_", "", stem)
    # Normalize separators to spaces first, so word boundaries work, then drop
    # common deck filler words.
    stem = re.sub(r"[-_]+", " ", stem)
    stem = re.sub(
        r"(?i)\b(pitch|deck|seed|series\s?[a-d]|round|investor|presentation|final|v\d+)\b",
        " ",
        stem,
    )
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem.title() if stem else "Unknown"
