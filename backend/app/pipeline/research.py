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

# Cost guards: bound how much external research a single deck can trigger.
# A deck with a 12-person team slide should not fan out into dozens of paid
# API calls + a huge LLM prompt. These caps keep cost predictable.
MAX_PEOPLE = 6
MAX_COMPETITORS = 4
RESULTS_PER_QUERY = 3


def research_person(person: Person, company: str) -> dict[str, Any]:
    key = cache.make_key("person", person.name, company)
    cached = cache.get(key)
    if cached is not None:
        cached["_cache_hit"] = True
        return cached

    search = get_search()
    enrich = get_enrichment()

    query = f"{person.name} {person.title or ''} {company} background work history".strip()
    web = search.search(query, num_results=RESULTS_PER_QUERY)
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
        "overview": search.search(f"{company} startup product funding", num_results=RESULTS_PER_QUERY),
        "market": search.search(
            f"{sector or company} market size competitors 2026", num_results=RESULTS_PER_QUERY
        ),
        "funding_comps": search.search(
            f"{sector or company} seed round size valuation 2025 2026", num_results=RESULTS_PER_QUERY
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
        "results": get_search().search(
            f"{name} product pricing differentiation", num_results=RESULTS_PER_QUERY
        ),
        "_cache_hit": False,
    }
    cache.put(key, "competitor", bundle)
    return bundle


def run_research(entities: Entities) -> dict[str, Any]:
    people = entities.people[:MAX_PEOPLE]
    competitors = entities.competitors_named[:MAX_COMPETITORS]
    return {
        "company": research_company(entities.company_name, entities.sector),
        "people": [research_person(p, entities.company_name) for p in people],
        "competitors": [research_competitor(c) for c in competitors],
    }
