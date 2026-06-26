"""Anthropic Claude client with structured-JSON helper and graceful degradation.

If no real ANTHROPIC_API_KEY is set, `complete_json` returns the provided
`mock` payload. If a real key IS set but a call fails (billing, rate limit,
outage, bad request), the client marks itself `degraded`, records a clean
human-readable reason, and falls back to `mock` instead of crashing the run.
Transient failures (429 / 5xx / timeouts) are retried with backoff first.
"""
from __future__ import annotations

import time
from typing import Any, Optional

from ..config import get_settings
from ..obs import logger

_MAX_RETRIES = 2
_BASE_DELAY_S = 1.0


class LLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None
        self._anthropic = None
        self.degraded = False
        self.last_error = ""
        if self.settings.has_llm:
            try:
                import anthropic

                self._anthropic = anthropic
                self._client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
            except Exception:  # pragma: no cover - SDK/import issues fall back to mock
                self._client = None

    @property
    def live(self) -> bool:
        return self._client is not None

    @property
    def usable(self) -> bool:
        """Live AND not degraded by a failed call this run."""
        return self.live and not self.degraded

    def _retriable(self) -> tuple:
        a = self._anthropic
        if not a:
            return tuple()
        names = ("RateLimitError", "InternalServerError", "APITimeoutError", "APIConnectionError")
        return tuple(getattr(a, n) for n in names if hasattr(a, n))

    def complete_json(
        self,
        *,
        system: str,
        prompt: str,
        mock: dict[str, Any],
        max_tokens: int = 4096,
        label: str = "llm",
    ) -> dict[str, Any]:
        """Return a JSON object from the model, or `mock` when unavailable."""
        if not self.live:
            logger.warning("[%s] LLM not live (no/placeholder API key) -> using placeholder", label)
            return mock

        logger.info("[%s] calling %s (prompt ~%d chars, max_tokens=%d)...",
                    label, self.settings.anthropic_model, len(prompt), max_tokens)

        def _attempt() -> str:
            msg = self._client.messages.create(  # type: ignore[union-attr]
                model=self.settings.anthropic_model,
                max_tokens=max_tokens,
                system=system + "\n\nRespond with a single valid JSON object and nothing else.",
                messages=[{"role": "user", "content": prompt}],
            )
            u = getattr(msg, "usage", None)
            if u is not None:
                logger.info("[%s] tokens in=%s out=%s", label,
                            getattr(u, "input_tokens", "?"), getattr(u, "output_tokens", "?"))
            return "".join(
                b.text for b in msg.content if getattr(b, "type", "") == "text"
            )

        retriable = self._retriable()
        attempt = 0
        while True:
            try:
                text = _attempt()
                result = _extract_json(text, fallback=mock)
                if result is mock:
                    logger.error("[%s] response was not valid JSON -> using placeholder. Raw head: %s",
                                 label, (text or "")[:200])
                else:
                    logger.info("[%s] parsed JSON OK (%d top-level keys)", label, len(result))
                return result
            except retriable as exc:  # transient -> backoff + retry
                attempt += 1
                logger.warning("[%s] transient error (%s), retry %d/%d",
                               label, type(exc).__name__, attempt, _MAX_RETRIES)
                if attempt > _MAX_RETRIES:
                    self._mark_degraded("Anthropic temporarily unavailable (rate limit / outage).")
                    return mock
                time.sleep(_BASE_DELAY_S * (2 ** (attempt - 1)))
            except Exception as exc:  # permanent (billing, auth, bad request) -> fail fast
                reason = _clean_error(exc)
                logger.error("[%s] LLM call FAILED (%s): %s", label, type(exc).__name__, reason)
                self._mark_degraded(reason)
                return mock

    def ocr_image(self, image_bytes: bytes, media_type: str = "image/png") -> str:
        """Transcribe visible text from a single page/slide image via Claude
        vision. Returns "" when unavailable or on failure (never raises)."""
        if not self.live:
            return ""
        import base64

        b64 = base64.standard_b64encode(image_bytes).decode("ascii")
        system = (
            "You are a precise OCR engine for startup pitch decks. Transcribe ALL "
            "visible text from the image verbatim, preserving reading order. Include "
            "headings, bullets, numbers, metrics, axis/legend labels, names, titles, "
            "and footnotes. Do NOT summarize, explain, translate, or invent text. "
            "Output only the transcribed text; if the image has no text, output nothing."
        )

        def _attempt() -> str:
            msg = self._client.messages.create(  # type: ignore[union-attr]
                model=self.settings.anthropic_model,
                max_tokens=1500,
                system=system,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": b64,
                                },
                            },
                            {"type": "text", "text": "Transcribe all text in this slide."},
                        ],
                    }
                ],
            )
            return "".join(
                b.text for b in msg.content if getattr(b, "type", "") == "text"
            ).strip()

        retriable = self._retriable()
        attempt = 0
        while True:
            try:
                return _attempt()
            except retriable:
                attempt += 1
                if attempt > _MAX_RETRIES:
                    # OCR is best-effort and independent: a failed page must NOT
                    # mark the whole client degraded (which would force the
                    # analysis to the placeholder). Just skip this page.
                    logger.warning("[ocr] vision call rate-limited/unavailable; skipping page")
                    return ""
                time.sleep(_BASE_DELAY_S * (2 ** (attempt - 1)))
            except Exception as exc:  # noqa: BLE001 - OCR must never crash the run
                logger.warning("[ocr] vision call failed (%s): %s",
                               type(exc).__name__, _clean_error(exc))
                return ""

    def _mark_degraded(self, reason: str) -> None:
        if not self.degraded:
            logger.error("LLM degraded for the rest of this run: %s", reason)
        self.degraded = True
        self.last_error = reason


def _clean_error(exc: Exception) -> str:
    """Extract a concise, user-readable reason from an Anthropic SDK error."""
    msg = getattr(exc, "message", None)
    if not msg:
        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            msg = (body.get("error") or {}).get("message")
    text = (msg or str(exc)).strip()
    low = text.lower()
    if "credit balance is too low" in low:
        return "Anthropic credit balance too low - add credits at console.anthropic.com (Plans & Billing)."
    if "authentication" in low or "invalid x-api-key" in low or "401" in low:
        return "Anthropic API key rejected - check ANTHROPIC_API_KEY in .env."
    if "model" in low and ("not found" in low or "does not exist" in low):
        return "Configured Anthropic model not available to this account - check ANTHROPIC_MODEL in .env."
    return f"Anthropic API error: {text[:160]}"


def _extract_json(text: str, fallback: dict[str, Any]) -> dict[str, Any]:
    import json

    text = (text or "").strip()
    if not text:
        return fallback

    # Strip ``` / ```json fences if present.
    if text.startswith("```"):
        nl = text.find("\n")
        if nl != -1:
            text = text[nl + 1 :]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
        text = text.strip()

    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return fallback

    candidate = text[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # Best-effort repair: balance braces/brackets for a response truncated at
    # max_tokens, and drop a trailing partial line, so a near-complete memo
    # still parses instead of collapsing to the placeholder.
    repaired = _balance_json(candidate)
    if repaired is not None:
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            return fallback
    return fallback


def _balance_json(s: str) -> Optional[str]:
    """Close unterminated strings/objects/arrays from a truncated JSON object."""
    out: list[str] = []
    stack: list[str] = []
    in_str = False
    escaped = False
    for ch in s:
        if in_str:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
            out.append(ch)
        elif ch in "}]":
            if stack and stack[-1] == ch:
                stack.pop()
            out.append(ch)
        else:
            out.append(ch)

    if in_str:
        out.append('"')
    # Remove a dangling comma / partial key before closing.
    tail = "".join(out).rstrip()
    while tail and tail[-1] in ",:":
        tail = tail[:-1].rstrip()
    for closer in reversed(stack):
        tail += closer
    return tail or None


_singleton: Optional[LLMClient] = None


def get_llm() -> LLMClient:
    global _singleton
    if _singleton is None:
        _singleton = LLMClient()
    return _singleton
