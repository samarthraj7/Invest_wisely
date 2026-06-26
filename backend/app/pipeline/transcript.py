"""Pitch-recording ingestion.

Two inputs are supported:
  * a text transcript (.txt / .vtt / .srt, or pasted text) -> cleaned to plain text
  * a pitch video -> optionally auto-transcribed via OpenAI Whisper when an
    OPENAI_API_KEY is configured (otherwise the user should also supply a transcript)

Everything here is best-effort and never raises into the pipeline.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from ..config import get_settings
from ..obs import logger, preview

_TS_LINE = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?([.,]\d{1,3})?\s*-->")
_CUE_NUM = re.compile(r"^\d+$")
_SPEAKER = re.compile(r"^\s*([A-Z][A-Za-z .'-]{1,30}):\s")


def parse_transcript_text(raw: str) -> str:
    """Normalize a transcript supplied as .txt / .vtt / .srt / pasted text."""
    if not raw:
        return ""
    lines: list[str] = []
    for line in raw.replace("\r", "").split("\n"):
        s = line.strip()
        if not s:
            continue
        if s.upper().startswith("WEBVTT"):
            continue
        if _TS_LINE.match(s):  # "00:00:01.000 --> 00:00:04.000"
            continue
        if _CUE_NUM.match(s):  # bare subtitle index
            continue
        s = re.sub(r"<[^>]+>", "", s)  # strip vtt inline tags
        lines.append(s)
    # Collapse duplicate consecutive lines (common in auto-captions).
    out: list[str] = []
    for s in lines:
        if not out or out[-1] != s:
            out.append(s)
    return "\n".join(out).strip()


def parse_transcript_bytes(filename: str, data: bytes) -> str:
    try:
        raw = data.decode("utf-8-sig", errors="replace")
    except Exception:
        raw = data.decode("latin-1", errors="replace")
    return parse_transcript_text(raw)


def transcribe_video(video_path: str | Path) -> str:
    """Transcribe a pitch video's audio via OpenAI Whisper, if configured.

    Returns "" when no OPENAI_API_KEY is set or on any failure (the caller then
    relies on a separately-uploaded transcript).
    """
    settings = get_settings()
    if not settings.has_openai:
        logger.info("[transcribe] no OPENAI_API_KEY set; skipping video transcription")
        return ""
    path = Path(video_path)
    if not path.exists():
        return ""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        logger.info("[transcribe] sending %s to %s...", path.name, settings.openai_transcribe_model)
        with path.open("rb") as f:
            resp = client.audio.transcriptions.create(
                model=settings.openai_transcribe_model, file=f
            )
        text = getattr(resp, "text", "") or ""
        logger.info("[transcribe] got %d chars: %s", len(text), preview(text, 200))
        return text.strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[transcribe] failed (%s): %s", type(exc).__name__, str(exc)[:200])
        return ""
