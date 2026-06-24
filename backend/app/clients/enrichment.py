"""Proxycurl people-enrichment client with mock fallback.

Given a name (+ company) or a LinkedIn URL, returns a structured profile:
work history, education, etc. Source URL is preserved for provenance.
"""
from __future__ import annotations

from typing import Any, Optional

import requests

from ..config import get_settings
from ._resilience import RateLimited, RateLimiter, with_retry

_PROFILE_ENDPOINT = "https://nubela.co/proxycurl/api/v2/linkedin"
_RESOLVE_ENDPOINT = "https://nubela.co/proxycurl/api/linkedin/profile/resolve"

# Proxycurl is rate-sensitive; keep at most ~2 req/s.
_LIMITER = RateLimiter(min_interval_s=0.5)


def _get(url: str, headers: dict[str, str], params: dict[str, Any]) -> requests.Response:
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    if resp.status_code == 429 or resp.status_code >= 500:
        raise RateLimited(f"Proxycurl {resp.status_code}")
    return resp


class EnrichmentClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def live(self) -> bool:
        return self.settings.has_enrichment

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.settings.proxycurl_api_key}"}

    def lookup(
        self,
        name: str,
        company: Optional[str] = None,
        linkedin_url: Optional[str] = None,
    ) -> dict[str, Any]:
        if not self.live:
            return _mock_profile(name, company)
        not_found = {"found": False, "name": name, "source_url": linkedin_url, "raw": {}}
        try:
            url = linkedin_url
            if not url:
                resolved = with_retry(
                    lambda: _get(
                        _RESOLVE_ENDPOINT,
                        self._headers(),
                        {"first_name": name.split()[0], "company_domain": company or ""},
                    ),
                    rate_limiter=_LIMITER,
                )
                if resolved.ok:
                    url = resolved.json().get("url")
            if not url:
                return {**not_found, "source_url": None}

            prof = with_retry(
                lambda: _get(_PROFILE_ENDPOINT, self._headers(), {"url": url}),
                rate_limiter=_LIMITER,
            )
            if not prof.ok:
                return {**not_found, "source_url": url}
            data = prof.json()
            return {
                "found": True,
                "name": name,
                "source_url": url,
                "experiences": data.get("experiences", []),
                "education": data.get("education", []),
                "headline": data.get("headline", ""),
                "raw": data,
            }
        except Exception:
            return not_found


def _mock_profile(name: str, company: Optional[str]) -> dict[str, Any]:
    return {
        "found": False,
        "mock": True,
        "name": name,
        "source_url": None,
        "experiences": [],
        "education": [],
        "headline": "",
        "note": "Set PROXYCURL_API_KEY in .env for live people enrichment.",
    }


_singleton: EnrichmentClient | None = None


def get_enrichment() -> EnrichmentClient:
    global _singleton
    if _singleton is None:
        _singleton = EnrichmentClient()
    return _singleton
