"""Step 4 - Research / enrichment (Exa search + Proxycurl), CACHED.

Builds a research bundle for the company and each person. Every item keeps the
source URL so the analysis step can cite real provenance. Cached by normalized
name+company so repeat lookups don't re-bill the APIs.
"""
from __future__ import annotations

from typing import Any

from ..clients import cache
from ..clients.enrichment import get_enrichment
from ..clients.search import get_search
from .entities import Entities, Person


def research_person(person: Person, company: str) -> dict[str, Any]:
    key = cache.make_key("person", person.name, company)
    cached = cache.get(key)
    if cached is not None:
        cached["_cache_hit"] = True
        return cached

    search = get_search()
    enrich = get_enrichment()

    query = f"{person.name} {person.title or ''} {company} background work history".strip()
    web = search.search(query, num_results=5)
    profile = enrich.lookup(person.name, company=company, linkedin_url=person.linkedin_url)

    bundle = {
        "name": person.name,
        "title": person.title,
        "web_results": web,
        "enrichment": profile,
        "found": bool(profile.get("found")) or bool([w for w in web if "mock" not in w["url"]]),
        "_cache_hit": False,
    }
    cache.put(key, "person", bundle)
    return bundle


def research_company(company: str, sector: str | None) -> dict[str, Any]:
    key = cache.make_key("company", company, sector or "")
    cached = cache.get(key)
    if cached is not None:
        cached["_cache_hit"] = True
        return cached

    search = get_search()
    bundle = {
        "company": company,
        "overview": search.search(f"{company} startup product funding", num_results=5),
        "market": search.search(f"{sector or company} market size competitors 2026", num_results=5),
        "funding_comps": search.search(
            f"{sector or company} seed round size valuation 2025 2026", num_results=5
        ),
        "_cache_hit": False,
    }
    cache.put(key, "company", bundle)
    return bundle


def research_competitor(name: str) -> dict[str, Any]:
    key = cache.make_key("competitor", name)
    cached = cache.get(key)
    if cached is not None:
        cached["_cache_hit"] = True
        return cached

    bundle = {
        "name": name,
        "results": get_search().search(f"{name} product pricing differentiation", num_results=3),
        "_cache_hit": False,
    }
    cache.put(key, "competitor", bundle)
    return bundle


def run_research(entities: Entities) -> dict[str, Any]:
    return {
        "company": research_company(entities.company_name, entities.sector),
        "people": [research_person(p, entities.company_name) for p in entities.people],
        "competitors": [research_competitor(c) for c in entities.competitors_named],
    }
