"""Orchestrates the full pipeline: parse -> understand -> entities -> research
-> analyze -> report. Emits stage callbacks so the API can report progress.

Parsing failures are fatal (raised as DeckParseError). Later stages degrade
gracefully: a research outage, for example, produces an empty research bundle
plus a report-level warning rather than failing the whole run.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from ..schemas import InvestmentReport
from . import analysis, deck_understanding, entities, parse, research

StageCb = Optional[Callable[[str], None]]


@dataclass
class PipelineResult:
    report: InvestmentReport
    company_name: str


def run_pipeline(deck_path: str | Path, on_stage: StageCb = None) -> PipelineResult:
    def stage(name: str) -> None:
        if on_stage:
            on_stage(name)

    warnings: list[str] = []

    stage("parsing")
    parsed = parse.parse_deck(deck_path)  # DeckParseError propagates (fatal)
    warnings.extend(parsed.warnings)

    stage("understanding")
    understanding = deck_understanding.understand_deck(parsed)

    stage("extracting")
    ents = entities.extract_entities(understanding)
    if not ents.people:
        warnings.append(
            "No founders/leadership were identified in the deck - team analysis is limited. "
            "Confirm the team slide parsed correctly."
        )

    stage("researching")
    try:
        research_bundle = research.run_research(ents)
    except Exception as exc:  # noqa: BLE001 - degrade instead of failing the run
        warnings.append(f"Research step degraded ({exc.__class__.__name__}); proceeding with deck-only analysis.")
        research_bundle = {"company": {}, "people": [], "competitors": []}

    stage("analyzing")
    report = analysis.analyze(ents, understanding, research_bundle)

    # If a live LLM call failed mid-run, surface why (billing, etc.) at the top.
    from ..clients.llm import get_llm

    llm = get_llm()
    if llm.degraded and llm.last_error:
        warnings.insert(0, f"Live analysis unavailable - showing sample analysis. Reason: {llm.last_error}")
    report.warnings = warnings

    stage("done")
    return PipelineResult(report=report, company_name=report.company_snapshot.name)
