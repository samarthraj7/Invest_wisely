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
from ..obs import logger
from .entities import Entities, Person

# Cost guards: bound how much external research a single deck can trigger.
# A deck with a 12-person team slide should not fan out into dozens of paid
# API calls + a huge LLM prompt. These caps keep cost predictable.
MAX_PEOPLE = 6
MAX_COMPETITORS = 4
RESULTS_PER_QUERY = 3


def _is_real(results: list[dict[str, Any]]) -> bool:
    """True if a search returned at least one genuine (non-mock) hit."""
    for r in results or []:
        url = (r.get("url") or "")
        if url and "example.com/mock" not in url and "mock" not in url.lower():
            return True
    return False


def _find_person_on_web(search, person: Person, company: str) -> tuple[list[dict[str, Any]], str]:
    """Locate a person via a fallback CASCADE when the deck gives no LinkedIn URL.

    The deck often lists a founder with just a name + role. We escalate through
    progressively looser queries and stop at the first that returns real hits:

      1) "<name>" "<company>"                          (most precise)
      2) <company> team / people <name>                (find via the company site)
      3) <name> <deck keywords about them>             (last resort, by expertise)

    When the deck DOES give a LinkedIn URL we just run the rich background query.
    """
    name = person.name
    title = person.title or ""

    if person.linkedin_url:
        q = f"{name} {title} {company} background work history".strip()
        return search.search(q, num_results=RESULTS_PER_QUERY), q

    attempts = [
        (f'"{name}" "{company}"', "name+company"),
        (f"{company} team people {name} {title}".strip(), "company-people"),
    ]
    if person.keywords:
        attempts.append((f"{name} {person.keywords}", "name+deck-keywords"))
    # Always keep a generic background query as the final net.
    attempts.append((f"{name} {title} {company} background work history".strip(), "background"))

    best: list[dict[str, Any]] = []
    for q, tag in attempts:
        res = search.search(q, num_results=RESULTS_PER_QUERY)
        if not best:
            best = res
        if _is_real(res):
            logger.info("[research] person '%s' located via %s query", name, tag)
            return res, q
    logger.info("[research] person '%s' not confidently located after %d queries", name, len(attempts))
    return best, attempts[0][0]


def research_person(person: Person, company: str) -> dict[str, Any]:
    key = cache.make_key("person", person.name, company)
    cached = cache.get(key)
    if cached is not None:
        cached["_cache_hit"] = True
        return cached

    search = get_search()
    enrich = get_enrichment()

    web, query = _find_person_on_web(search, person, company)
    # Dedicated credential signals: research output and patents. These let the
    # analysis judge not just IF someone is credentialed but how substantively.
    papers = search.search(
        f"{person.name} research papers publications google scholar", num_results=RESULTS_PER_QUERY
    )
    patents = search.search(
        f"{person.name} patents inventor", num_results=RESULTS_PER_QUERY
    )
    profile = enrich.lookup(person.name, company=company, linkedin_url=person.linkedin_url)

    bundle = {
        "name": person.name,
        "title": person.title,
        "web_results": web,
        "papers": papers,
        "patents": patents,
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
