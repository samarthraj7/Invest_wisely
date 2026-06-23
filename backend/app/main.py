"""FastAPI app: upload decks, run the analysis pipeline, browse reports."""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

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
    init_db()


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

        def on_stage(stage: str) -> None:
            with SessionLocal() as s2:
                d = s2.get(Deck, deck_id)
                if d:
                    d.status = stage if stage != "done" else "analyzing"
                    s2.commit()

        try:
            result = run_pipeline(path, on_stage=on_stage)
            deck.report_json = result.report.model_dump(mode="json")
            deck.company_name = result.company_name
            deck.recommendation = result.report.recommendation.recommendation.value
            deck.risk_rating = result.report.recommendation.risk_rating
            deck.status = "done"
        except Exception as exc:  # noqa: BLE001
            deck.status = "error"
            deck.error = str(exc)
        s.commit()


def _create_and_run(filename: str, src_path: Path, bg: BackgroundTasks) -> dict:
    deck_id = str(uuid.uuid4())
    with SessionLocal() as s:
        s.add(Deck(id=deck_id, filename=filename, status="pending"))
        s.commit()
    bg.add_task(_process, deck_id, str(src_path))
    return {"id": deck_id, "status": "pending"}


@app.post("/api/decks")
async def upload_deck(bg: BackgroundTasks, file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith((".pdf", ".pptx", ".ppt")):
        raise HTTPException(400, "Upload a .pdf or .pptx file")
    deck_id = str(uuid.uuid4())
    dest = UPLOAD_DIR / f"{deck_id}_{file.filename}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return _create_and_run(file.filename, dest, bg)


@app.post("/api/decks/demo")
def upload_demo(bg: BackgroundTasks) -> dict:
    from .demo import generate_demo_deck

    path = generate_demo_deck(UPLOAD_DIR)
    return _create_and_run(path.name, path, bg)


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
                "recommendation": d.recommendation,
                "risk_rating": d.risk_rating,
                "created_at": d.created_at.isoformat(),
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
            "created_at": d.created_at.isoformat(),
        }


@app.get("/api/decks/{deck_id}/export")
def export_deck(deck_id: str) -> FileResponse:
    with SessionLocal() as s:
        d = s.get(Deck, deck_id)
        if not d or not d.report_json:
            raise HTTPException(404, "Report not ready")
        report = InvestmentReport.model_validate(d.report_json)
    out = REPORT_DIR / f"{deck_id}"
    path, fmt = report_mod.export_pdf(report, out)
    media = "application/pdf" if fmt == "pdf" else "text/html"
    return FileResponse(str(path), media_type=media, filename=f"{d.company_name}_memo.{fmt}")
