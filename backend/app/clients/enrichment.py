"""Proxycurl people-enrichment client with mock fallback.

Given a name (+ company) or a LinkedIn URL, returns a structured profile:
work history, education, etc. Source URL is preserved for provenance.
"""
from __future__ import annotations

from typing import Any, Optional

import requests

from ..config import get_settings

_PROFILE_ENDPOINT = "https://nubela.co/proxycurl/api/v2/linkedin"
_RESOLVE_ENDPOINT = "https://nubela.co/proxycurl/api/linkedin/profile/resolve"


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
        try:
            url = linkedin_url
            if not url:
                resolved = requests.get(
                    _RESOLVE_ENDPOINT,
                    headers=self._headers(),
                    params={"first_name": name.split()[0], "company_domain": company or ""},
                    timeout=30,
                )
                if resolved.ok:
                    url = resolved.json().get("url")
            if not url:
                return {"found": False, "name": name, "source_url": None, "raw": {}}

            prof = requests.get(
                _PROFILE_ENDPOINT,
                headers=self._headers(),
                params={"url": url},
                timeout=30,
            )
            if not prof.ok:
                return {"found": False, "name": name, "source_url": url, "raw": {}}
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
            return {"found": False, "name": name, "source_url": linkedin_url, "raw": {}}


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
