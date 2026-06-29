"""Step 3 - Entity extraction & normalization (deterministic).

Dedupes/cleans the people + company that understanding produced, so research
runs once per unique entity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Person:
    name: str
    title: Optional[str] = None
    linkedin_url: Optional[str] = None
    deck_page: Optional[int] = None
    # A few words the deck uses about this person (expertise / prior employers /
    # domain). Used as a last-resort search signal when no LinkedIn link is given.
    keywords: Optional[str] = None


@dataclass
class Entities:
    company_name: str
    company_one_liner: str
    sector: Optional[str] = None
    people: list[Person] = field(default_factory=list)
    competitors_named: list[str] = field(default_factory=list)


def _norm_name(name: str) -> str:
    return " ".join(name.strip().split()).title()


def extract_entities(understanding: dict[str, Any]) -> Entities:
    company = understanding.get("company", {}) or {}
    ents = Entities(
        company_name=company.get("name") or "Unknown",
        company_one_liner=company.get("one_liner") or "",
        sector=company.get("sector"),
        competitors_named=list(dict.fromkeys(understanding.get("competitors_named", []) or [])),
    )

    seen: set[str] = set()
    for raw in understanding.get("team", []) or []:
        name = _norm_name(raw.get("name", ""))
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        ents.people.append(
            Person(
                name=name,
                title=raw.get("title"),
                linkedin_url=raw.get("linkedin_url"),
                deck_page=raw.get("page"),
                keywords=raw.get("keywords") or raw.get("bio") or raw.get("description"),
            )
        )
    return ents
