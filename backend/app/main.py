"""FastAPI app: upload decks, run the analysis pipeline, browse reports."""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .config import get_settings
from .db import Deck, SessionLocal, init_db
from .pipeline import report as report_mod
from .pipeline.runner import run_pipeline
from .schemas import InvestmentReport

settings = get_settings()
app = FastAPI(title="Invest Wisely API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = settings.storage_dir / "uploads"
REPORT_DIR = settings.storage_dir / "reports"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)


@app.on_event("startup")
def _startup() -> None:
    from .obs import logger, setup_logging

    setup_logging()
    init_db()
    logger.info(
        "startup: llm=%s search=%s enrichment=%s model=%s ocr=%s",
        settings.has_llm,
        settings.has_search,
        settings.has_enrichment,
        settings.anthropic_model,
        settings.ocr_engine,
    )


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "mock_mode": not (settings.has_llm and settings.has_search),
        "llm": settings.has_llm,
        "search": settings.has_search,
        "enrichment": settings.has_enrichment,
    }


def _process(deck_id: str, path: str) -> None:
    with SessionLocal() as s:
        deck = s.get(Deck, deck_id)
        if not deck:
            return
        transcript_text = deck.transcript_text
        video_path = deck.video_path

        def on_stage(stage: str) -> None:
            with SessionLocal() as s2:
                d = s2.get(Deck, deck_id)
                if d:
                    d.status = stage if stage != "done" else "analyzing"
                    s2.commit()

        try:
            result = run_pipeline(
                path,
                on_stage=on_stage,
                transcript_text=transcript_text,
                video_path=video_path,
            )
            deck.report_json = result.report.model_dump(mode="json")
            deck.company_name = result.company_name
            deck.recommendation = result.report.recommendation.recommendation.value
            deck.risk_rating = result.report.recommendation.risk_rating
            deck.status = "done"
        except Exception as exc:  # noqa: BLE001
            deck.status = "error"
            deck.error = str(exc)
        s.commit()


def _create_and_run(
    filename: str,
    src_path: Path,
    bg: BackgroundTasks,
    transcript_text: str | None = None,
    video_path: str | None = None,
) -> dict:
    deck_id = str(uuid.uuid4())
    with SessionLocal() as s:
        s.add(Deck(
            id=deck_id,
            filename=filename,
            status="pending",
            transcript_text=transcript_text or None,
            video_path=video_path or None,
        ))
        s.commit()
    bg.add_task(_process, deck_id, str(src_path))
    return {"id": deck_id, "status": "pending"}


MAX_UPLOAD_BYTES = 30 * 1024 * 1024  # 30 MB
MAX_VIDEO_BYTES = 500 * 1024 * 1024  # 500 MB
MAX_TRANSCRIPT_BYTES = 5 * 1024 * 1024  # 5 MB


async def _save_upload(up: UploadFile, dest: Path, max_bytes: int) -> int:
    size = 0
    with dest.open("wb") as f:
        while chunk := await up.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                f.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"'{up.filename}' is too large.")
            f.write(chunk)
    return size


@app.post("/api/decks")
async def upload_deck(
    bg: BackgroundTasks,
    file: UploadFile = File(...),
    transcript: Optional[UploadFile] = File(None),
    transcript_text: Optional[str] = Form(None),
    video: Optional[UploadFile] = File(None),
) -> dict:
    if not file.filename or not file.filename.lower().endswith((".pdf", ".pptx", ".ppt")):
        raise HTTPException(400, "Upload a .pdf or .pptx file")
    deck_id = str(uuid.uuid4())
    dest = UPLOAD_DIR / f"{deck_id}_{file.filename}"
    size = await _save_upload(file, dest, MAX_UPLOAD_BYTES)
    if size == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, "Uploaded file is empty.")

    # Optional pitch transcript: pasted text or an uploaded .txt/.vtt/.srt file.
    final_transcript = (transcript_text or "").strip()
    if transcript is not None and transcript.filename:
        from .pipeline.transcript import parse_transcript_bytes

        data = await transcript.read(MAX_TRANSCRIPT_BYTES + 1)
        if len(data) > MAX_TRANSCRIPT_BYTES:
            raise HTTPException(413, "Transcript file too large (max 5 MB).")
        parsed = parse_transcript_bytes(transcript.filename, data)
        final_transcript = (final_transcript + "\n" + parsed).strip() if final_transcript else parsed

    # Optional pitch video (used for tone analysis + optional auto-transcription).
    video_path: Optional[str] = None
    if video is not None and video.filename:
        vdest = UPLOAD_DIR / f"{deck_id}_video_{video.filename}"
        await _save_upload(video, vdest, MAX_VIDEO_BYTES)
        video_path = str(vdest)

    return _create_and_run(file.filename, dest, bg, final_transcript or None, video_path)


@app.post("/api/decks/demo")
def upload_demo(bg: BackgroundTasks) -> dict:
    from .demo import generate_demo_deck

    path = generate_demo_deck(UPLOAD_DIR)
    return _create_and_run(path.name, path, bg)


def _iso_utc(d) -> str | None:
    """Serialize a stored UTC datetime with an explicit 'Z' so browsers convert
    it to the viewer's local time instead of misreading naive UTC as local."""
    if d is None:
        return None
    import datetime as _dt

    if d.tzinfo is None:
        d = d.replace(tzinfo=_dt.timezone.utc)
    return d.astimezone(_dt.timezone.utc).isoformat().replace("+00:00", "Z")


@app.get("/api/decks")
def list_decks() -> list[dict]:
    with SessionLocal() as s:
        rows = s.query(Deck).order_by(Deck.created_at.desc()).all()
        return [
            {
                "id": d.id,
                "filename": d.filename,
                "company_name": d.company_name,
                "status": d.status,
                "error": (d.error or "")[:300],
                "recommendation": d.recommendation,
                "risk_rating": d.risk_rating,
                "has_transcript": bool(d.transcript_text),
                "has_video": bool(d.video_path),
                "created_at": _iso_utc(d.created_at),
            }
            for d in rows
        ]


@app.get("/api/decks/{deck_id}")
def get_deck(deck_id: str) -> dict:
    with SessionLocal() as s:
        d = s.get(Deck, deck_id)
        if not d:
            raise HTTPException(404, "Deck not found")
        return {
            "id": d.id,
            "filename": d.filename,
            "company_name": d.company_name,
            "status": d.status,
            "error": d.error,
            "report": d.report_json,
            "has_transcript": bool(d.transcript_text),
            "has_video": bool(d.video_path),
            "created_at": _iso_utc(d.created_at),
        }


_MEDIA = {
    "pdf": "application/pdf",
    "html": "text/html",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@app.delete("/api/decks/{deck_id}")
def delete_deck(deck_id: str) -> dict:
    with SessionLocal() as s:
        d = s.get(Deck, deck_id)
        if not d:
            raise HTTPException(404, "Deck not found")
        s.delete(d)
        s.commit()
    return {"ok": True, "id": deck_id}


class IcebreakerRequest(BaseModel):
    background: str = ""


@app.post("/api/decks/{deck_id}/icebreakers")
def icebreakers(deck_id: str, body: IcebreakerRequest) -> dict:
    """On-demand: find common ground / icebreakers between a supplied background
    (your own or anyone's) and this deck's founders."""
    from .pipeline.icebreakers import find_icebreakers

    with SessionLocal() as s:
        d = s.get(Deck, deck_id)
        if not d or not d.report_json:
            raise HTTPException(404, "Report not ready")
        report = InvestmentReport.model_validate(d.report_json)
    result = find_icebreakers(report, body.background)
    return result.model_dump(mode="json")


@app.get("/api/decks/{deck_id}/export")
def export_deck(deck_id: str, format: str = "pdf") -> FileResponse:
    fmt = format.lower()
    if fmt not in _MEDIA:
        raise HTTPException(400, "format must be one of: pdf, docx, html")
    with SessionLocal() as s:
        d = s.get(Deck, deck_id)
        if not d or not d.report_json:
            raise HTTPException(404, "Report not ready")
        report = InvestmentReport.model_validate(d.report_json)
        company = d.company_name
    out = REPORT_DIR / f"{deck_id}"
    path, actual = report_mod.export_report(report, out, fmt)
    return FileResponse(
        str(path), media_type=_MEDIA[actual], filename=f"{company}_memo.{actual}"
    )
