"""Exa web-search client with mock fallback.

Returns a list of {title, url, snippet} results. Every result's `url` is used
downstream as citeable provenance (source_type=web).
"""
from __future__ import annotations

from typing import Any

from ..config import get_settings


class SearchClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None
        if self.settings.has_search:
            try:
                from exa_py import Exa

                self._client = Exa(self.settings.exa_api_key)
            except Exception:  # pragma: no cover
                self._client = None

    @property
    def live(self) -> bool:
        return self._client is not None

    def search(self, query: str, num_results: int = 5) -> list[dict[str, Any]]:
        if not self.live:
            return _mock_results(query, num_results)
        try:
            res = self._client.search_and_contents(  # type: ignore[union-attr]
                query, num_results=num_results, text={"max_characters": 800}
            )
            out: list[dict[str, Any]] = []
            for r in res.results:
                out.append(
                    {
                        "title": getattr(r, "title", "") or "",
                        "url": getattr(r, "url", "") or "",
                        "snippet": (getattr(r, "text", "") or "")[:800],
                    }
                )
            return out
        except Exception:
            return _mock_results(query, num_results)


def _mock_results(query: str, n: int) -> list[dict[str, Any]]:
    return [
        {
            "title": f"[MOCK] Result {i + 1} for: {query}",
            "url": f"https://example.com/mock/{i + 1}",
            "snippet": "Mock research snippet. Set EXA_API_KEY in .env for live web research.",
        }
        for i in range(min(n, 3))
    ]


_singleton: SearchClient | None = None


def get_search() -> SearchClient:
    global _singleton
    if _singleton is None:
        _singleton = SearchClient()
    return _singleton
