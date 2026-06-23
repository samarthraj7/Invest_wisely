"""Research cache: keyed by a normalized hash of the lookup target.

The same founder appearing across two decks, or a re-run of the same deck,
reuses cached research instead of re-billing the search/enrichment APIs.
"""
from __future__ import annotations

import datetime as dt
import hashlib
from typing import Optional

from ..config import get_settings
from ..db import ResearchCache, SessionLocal


def make_key(kind: str, *parts: str) -> str:
    norm = "|".join(p.strip().lower() for p in parts if p)
    digest = hashlib.sha256(f"{kind}:{norm}".encode()).hexdigest()[:32]
    return f"{kind}:{digest}"


def get(key: str) -> Optional[dict]:
    ttl_days = get_settings().research_cache_ttl_days
    with SessionLocal() as s:
        row = s.get(ResearchCache, key)
        if not row:
            return None
        created = row.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=dt.timezone.utc)
        age = dt.datetime.now(dt.timezone.utc) - created
        if age > dt.timedelta(days=ttl_days):
            return None
        return row.payload


def put(key: str, kind: str, payload: dict) -> None:
    with SessionLocal() as s:
        row = s.get(ResearchCache, key)
        if row:
            row.payload = payload
            row.created_at = dt.datetime.now(dt.timezone.utc)
        else:
            s.add(ResearchCache(key=key, kind=kind, payload=payload))
        s.commit()
