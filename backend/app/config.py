"""Application configuration loaded from environment / .env file."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PLACEHOLDER_PREFIX = "PLACEHOLDER_"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    exa_api_key: str = ""
    proxycurl_api_key: str = ""
    # Optional: enables auto-transcription of uploaded pitch videos via Whisper.
    openai_api_key: str = ""
    openai_transcribe_model: str = "whisper-1"

    allow_mock_mode: bool = True
    research_cache_ttl_days: int = 30

    # OCR fallback for image-only / scanned decks (PDF). Triggered only when a
    # page has images but little/no selectable text.
    #   ocr_engine: "auto" -> local Tesseract if installed, else Claude vision
    #               "vision" -> always use Claude vision (uses ANTHROPIC_API_KEY)
    #               "tesseract" -> only local Tesseract
    #               "off" -> disable OCR entirely
    ocr_engine: str = "auto"
    ocr_max_pages: int = 20          # cost guard: at most this many pages OCR'd
    ocr_min_chars_per_page: int = 30  # a page below this (with images) is a candidate

    database_url: str = "sqlite:///./storage/invest_wisely.sqlite3"
    frontend_origin: str = "http://localhost:3000"

    @staticmethod
    def _is_real(key: str) -> bool:
        return bool(key) and not key.startswith(PLACEHOLDER_PREFIX)

    @property
    def has_llm(self) -> bool:
        return self._is_real(self.anthropic_api_key)

    @property
    def has_search(self) -> bool:
        return self._is_real(self.exa_api_key)

    @property
    def has_enrichment(self) -> bool:
        return self._is_real(self.proxycurl_api_key)

    @property
    def has_openai(self) -> bool:
        return self._is_real(self.openai_api_key)

    @property
    def storage_dir(self) -> Path:
        d = BACKEND_DIR / "storage"
        d.mkdir(parents=True, exist_ok=True)
        return d


@lru_cache
def get_settings() -> Settings:
    return Settings()
