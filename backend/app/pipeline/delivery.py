"""Pitch delivery & Q&A analysis (LLM).

Derives, from the pitch transcript, how the founders communicated: clarity,
narrative structure, how they handled cross-questions (with the actual Q&A
captured), and overall strengths/weaknesses.

`tone` (delivery energy/confidence) is only requested when a VIDEO was uploaded,
since vocal delivery cues come from the recording, not the words alone.
"""
from __future__ import annotations

from typing import Any

from ..clients.llm import get_llm
from ..obs import logger
from ..schemas import PitchDelivery

_SYSTEM = """You are a VC associate assessing how a startup PITCH was delivered, based on a
transcript of the founders speaking (and, if noted, a video recording). Be specific and fair.
Rules:
- Use ONLY the transcript. Quote/paraphrase real questions and answers from it.
- Judge clarity (was the idea explained understandably?), structure (logical flow?), and how
  well cross-questions were handled (direct vs evasive, data-backed vs hand-wavy).
- Capture the actual Q&A: each audience question, what the founder answered, and your
  assessment of that answer.
- If (and ONLY if) a video was provided, also assess `tone`: delivery energy, confidence,
  pacing, and composure under questioning. If no video, leave `tone` as "".
- Do not invent questions that were not asked. If there was no real Q&A, return an empty qa list.
"""

_SCHEMA = """Return ONE JSON object:
{
  "clarity": "how clearly the idea was communicated",
  "structure": "how coherent/organized the narrative was",
  "handling_of_questions": "overall: how well cross-questions were handled",
  "tone": "ONLY if video provided: energy/confidence/pacing/composure; else empty string",
  "strengths": ["delivery strengths"],
  "weaknesses": ["delivery weaknesses"],
  "qa": [{"question":"asked question","answer":"what they answered",
          "assessment":"how good the answer was","confidence":"high|medium|low|inconclusive"}],
  "notes": [{"claim":"sourced observation","source_type":"inference","source_ref":"transcript","confidence":"medium"}]
}"""


def analyze_delivery(transcript: str | None, has_video: bool) -> PitchDelivery:
    n = len((transcript or "").strip())
    if not transcript or n < 40:
        logger.info("[delivery] no usable transcript (%d chars) -> skipped", n)
        return PitchDelivery(available=False)

    llm = get_llm()
    logger.info("[delivery] transcript=%d chars, has_video=%s, llm.usable=%s", n, has_video, llm.usable)
    source = "video+transcript" if has_video else "transcript"

    # If the model isn't usable (no key / degraded mid-run), don't emit a vague
    # "unavailable" line — say exactly why, consistent with the top-of-report note.
    if not llm.usable:
        reason = llm.last_error or "live analysis was unavailable for this run"
        logger.warning("[delivery] LLM not usable -> contextual placeholder (%s)", reason)
        return PitchDelivery(
            available=True,
            source=source,
            clarity=f"Pitch delivery was not analyzed because {reason} See the note at the top of the report.",
        )

    video_note = (
        "A VIDEO was provided: assess `tone` (delivery energy/confidence/pacing/composure)."
        if has_video
        else "No video was provided: leave `tone` empty."
    )
    prompt = f"{_SCHEMA}\n\n{video_note}\n\n=== PITCH TRANSCRIPT ===\n{transcript[:14000]}"

    raw: dict[str, Any] = llm.complete_json(
        system=_SYSTEM,
        prompt=prompt,
        mock=_mock_delivery(),
        max_tokens=3000,
        label="delivery",
    )
    try:
        delivery = PitchDelivery.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        logger.error("[delivery] validation failed -> placeholder (%s)", type(exc).__name__)
        delivery = PitchDelivery.model_validate(_mock_delivery())
    delivery.available = True
    delivery.source = source
    if not has_video:
        delivery.tone = ""  # enforce: tone only with video
    logger.info("[delivery] done: %d Q&A exchange(s), tone=%s",
                len(delivery.qa), "yes" if delivery.tone else "no")
    return delivery


def _mock_delivery() -> dict[str, Any]:
    return {
        "clarity": "Pitch delivery could not be analyzed for this run (the model returned no "
                   "usable result). Re-run with live analysis for a full assessment.",
        "structure": "", "handling_of_questions": "", "tone": "",
        "strengths": [], "weaknesses": [], "qa": [], "notes": [],
    }
