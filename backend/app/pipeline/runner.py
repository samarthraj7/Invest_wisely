"""Orchestrates the full pipeline: parse -> understand -> entities -> research
-> analyze -> report. Emits stage callbacks so the API can report progress.
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

    stage("parsing")
    parsed = parse.parse_deck(deck_path)

    stage("understanding")
    understanding = deck_understanding.understand_deck(parsed)

    stage("extracting")
    ents = entities.extract_entities(understanding)

    stage("researching")
    research_bundle = research.run_research(ents)

    stage("analyzing")
    report = analysis.analyze(ents, understanding, research_bundle)

    stage("done")
    return PipelineResult(report=report, company_name=report.company_snapshot.name)
