"""Anthropic Claude client with structured-JSON helper and mock fallback.

If no real ANTHROPIC_API_KEY is set, `complete_json` returns the provided
`mock` payload so the whole pipeline runs end-to-end with zero keys.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from ..config import get_settings


class LLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None
        if self.settings.has_llm:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
            except Exception:  # pragma: no cover - import/SDK issues fall back to mock
                self._client = None

    @property
    def live(self) -> bool:
        return self._client is not None

    def complete_json(
        self,
        *,
        system: str,
        prompt: str,
        mock: dict[str, Any],
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Return a JSON object from the model, or `mock` when not live."""
        if not self.live:
            return mock

        msg = self._client.messages.create(  # type: ignore[union-attr]
            model=self.settings.anthropic_model,
            max_tokens=max_tokens,
            system=system + "\n\nRespond with a single valid JSON object and nothing else.",
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")
        return _extract_json(text, fallback=mock)


def _extract_json(text: str, fallback: dict[str, Any]) -> dict[str, Any]:
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
