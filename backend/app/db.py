"""SQLite persistence via SQLAlchemy. Stores deck submissions, generated
reports (as JSON), and a research cache to avoid re-billing repeat lookups."""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import BACKEND_DIR, get_settings

settings = get_settings()

# Resolve sqlite path relative to backend/ regardless of cwd.
_url = settings.database_url
if _url.startswith("sqlite:///./"):
    abs_path = (BACKEND_DIR / _url.replace("sqlite:///./", "")).resolve()
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    _url = f"sqlite:///{abs_path}"

engine = create_engine(_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Base(DeclarativeBase):
    pass


class Deck(Base):
    __tablename__ = "decks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(512))
    company_name: Mapped[str] = mapped_column(String(256), default="Unknown")
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|parsing|researching|analyzing|done|error
    error: Mapped[str] = mapped_column(Text, default="")
    report_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    recommendation: Mapped[str] = mapped_column(String(32), default="")
    risk_rating: Mapped[str] = mapped_column(String(32), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class ResearchCache(Base):
    __tablename__ = "research_cache"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))  # person | company | competitor
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_utcnow)


def init_db() -> None:
    Base.metadata.create_all(engine)
