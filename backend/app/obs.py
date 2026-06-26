"""Lightweight observability: a single logger that prints clear, step-by-step
pipeline progress to the terminal (the uvicorn console or the CLI).

Every pipeline stage, LLM call (with token usage), OCR extraction, and failure
reason is logged here so it's obvious what the pipeline is doing and exactly
where/why it degraded.
"""
from __future__ import annotations

import logging
import sys

logger = logging.getLogger("invest_wisely")


def setup_logging(level: int = logging.INFO) -> None:
    """Attach a stdout handler once. Safe to call multiple times."""
    if logger.handlers:
        return
    # Force UTF-8 on the underlying stream where possible so non-ASCII text in
    # decks/OCR doesn't crash the Windows (cp1252) console logger.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [iw] %(message)s", "%H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False


def preview(text: str, limit: int = 600) -> str:
    """One-line-ish preview of (possibly long) text for logging."""
    text = (text or "").strip().replace("\r", " ")
    snipped = text[:limit]
    if len(text) > limit:
        snipped += f" ...(+{len(text) - limit} more chars)"
    return snipped
