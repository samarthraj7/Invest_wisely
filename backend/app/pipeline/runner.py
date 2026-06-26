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

from ..config import get_settings
from ..obs import logger
from ..schemas import InvestmentReport
from . import analysis, deck_understanding, delivery, entities, ocr, parse, research, scoring, transcript

StageCb = Optional[Callable[[str], None]]


@dataclass
class PipelineResult:
    report: InvestmentReport
    company_name: str


def run_pipeline(
    deck_path: str | Path,
    on_stage: StageCb = None,
    transcript_text: str | None = None,
    video_path: str | None = None,
) -> PipelineResult:
    def stage(name: str) -> None:
        logger.info(">> stage: %s", name)
        if on_stage:
            on_stage(name)

    warnings: list[str] = []
    logger.info("=== pipeline START: %s (transcript=%s video=%s) ===",
                Path(deck_path).name, bool(transcript_text), bool(video_path))

    stage("parsing")
    parsed = parse.parse_deck(deck_path)  # DeckParseError propagates (fatal)
    logger.info("parsed: %d page(s), %d chars of text, %d image(s)",
                len(parsed.slides), parsed.total_chars, parsed.total_images)

    # Pitch recording: a video can be auto-transcribed (Whisper) when no
    # transcript was supplied; tone analysis is gated on having a video.
    has_video = bool(video_path)
    pitch_transcript = (transcript_text or "").strip()
    if has_video and not pitch_transcript:
        stage("transcribing")
        pitch_transcript = transcript.transcribe_video(video_path)
        if not pitch_transcript:
            warnings.append(
                "A video was uploaded but could not be auto-transcribed (set OPENAI_API_KEY, "
                "or also upload a transcript). Delivery/tone analysis was limited."
            )
    if pitch_transcript:
        logger.info("transcript ready: %d chars", len(pitch_transcript))

    # Image-only / scanned deck? Recover text via OCR before anything else reads it.
    _s = get_settings()
    if _s.ocr_engine != "off" and ocr.candidate_pages(parsed, _s.ocr_min_chars_per_page):
        stage("ocr")
        try:
            ocr.maybe_run_ocr(parsed, deck_path)
            logger.info("post-OCR: %d chars of text across %d page(s)",
                        parsed.total_chars, len(parsed.slides))
        except Exception as exc:  # noqa: BLE001 - OCR is best-effort, never fatal
            logger.exception("OCR step raised: %s", exc)
            warnings.append(f"OCR step skipped ({exc.__class__.__name__}).")

    warnings.extend(parsed.warnings)

    stage("understanding")
    understanding = deck_understanding.understand_deck(parsed, transcript=pitch_transcript or None)
    _co = (understanding.get("company") or {})
    logger.info("understanding: company=%r sector=%r team=%d competitors=%d%s",
                _co.get("name"), _co.get("sector"),
                len(understanding.get("team") or []),
                len(understanding.get("competitors_named") or []),
                "  [PLACEHOLDER]" if understanding.get("_mock") else "")

    stage("extracting")
    ents = entities.extract_entities(understanding)
    logger.info("entities: company=%r people=%d competitors=%d",
                ents.company_name, len(ents.people), len(ents.competitors_named))
    if not ents.people:
        warnings.append(
            "No founders/leadership were identified in the deck - team analysis is limited. "
            "Confirm the team slide parsed correctly."
        )

    stage("researching")
    try:
        research_bundle = research.run_research(ents)
        logger.info("research: people=%d competitors=%d (company overview=%d results)",
                    len(research_bundle.get("people", [])),
                    len(research_bundle.get("competitors", [])),
                    len((research_bundle.get("company") or {}).get("overview", [])))
    except Exception as exc:  # noqa: BLE001 - degrade instead of failing the run
        logger.exception("research raised: %s", exc)
        warnings.append(f"Research step degraded ({exc.__class__.__name__}); proceeding with deck-only analysis.")
        research_bundle = {"company": {}, "people": [], "competitors": []}

    stage("analyzing")
    report = analysis.analyze(ents, understanding, research_bundle)

    if pitch_transcript:
        stage("delivery")
        report.delivery = delivery.analyze_delivery(pitch_transcript, has_video=has_video)

    stage("scoring")
    report.score = scoring.compute_score(report, understanding, research_bundle)

    # If a live LLM call failed mid-run, surface why (billing, etc.) at the top.
    from ..clients.llm import get_llm

    llm = get_llm()
    if llm.degraded and llm.last_error:
        warnings.insert(0, f"Live analysis unavailable - showing sample analysis. Reason: {llm.last_error}")
    report.warnings = warnings

    stage("done")
    logger.info("=== pipeline DONE: company=%r mock_mode=%s red_flags=%d warnings=%d ===",
                report.company_snapshot.name, report.mock_mode,
                len(report.red_flags), len(report.warnings))
    if report.mock_mode:
        logger.warning("RESULT IS A PLACEHOLDER (mock_mode=True). Reason: %s",
                       llm.last_error or "LLM not live (no API key)")
    return PipelineResult(report=report, company_name=report.company_snapshot.name)
