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
    ) -> dict[str, Any]:
        """Return a JSON object from the model, or `mock` when unavailable."""
        if not self.live:
            return mock

        def _attempt() -> str:
            msg = self._client.messages.create(  # type: ignore[union-attr]
                model=self.settings.anthropic_model,
                max_tokens=max_tokens,
                system=system + "\n\nRespond with a single valid JSON object and nothing else.",
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(
                b.text for b in msg.content if getattr(b, "type", "") == "text"
            )

        retriable = self._retriable()
        attempt = 0
        while True:
            try:
                text = _attempt()
                return _extract_json(text, fallback=mock)
            except retriable:  # transient -> backoff + retry
                attempt += 1
                if attempt > _MAX_RETRIES:
                    self._mark_degraded("Anthropic temporarily unavailable (rate limit / outage).")
                    return mock
                time.sleep(_BASE_DELAY_S * (2 ** (attempt - 1)))
            except Exception as exc:  # permanent (billing, auth, bad request) -> fail fast
                self._mark_degraded(_clean_error(exc))
                return mock

    def _mark_degraded(self, reason: str) -> None:
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

    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{") :]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return fallback
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return fallback


_singleton: Optional[LLMClient] = None


def get_llm() -> LLMClient:
    global _singleton
    if _singleton is None:
        _singleton = LLMClient()
    return _singleton
