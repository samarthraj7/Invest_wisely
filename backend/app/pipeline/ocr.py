"""Step 1b - OCR fallback for image-only / scanned decks.

Runs right after parsing. For PDF pages that have embedded images but little or
no selectable text, we render the page to an image and recover the text with an
OCR engine:

  * "tesseract" - local, free (needs the Tesseract binary + pytesseract + Pillow)
  * "vision"    - Claude vision via the existing ANTHROPIC_API_KEY (no native deps)
  * "auto"      - Tesseract if available, otherwise Claude vision

OCR is best-effort: any failure degrades gracefully and leaves the original
(empty) text plus the standard image-only warning. Cost is bounded by
`ocr_max_pages`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from ..config import get_settings
from ..obs import logger, preview
from .parse import IMAGE_ONLY_WARNING, ParsedDeck

ProgressCb = Optional[Callable[[int, int], None]]

# Cap the rendered image's longest side. Claude downsizes anything above ~1568px
# anyway, so this keeps both Tesseract accuracy and vision token cost in check.
_MAX_RENDER_PX = 1500


def candidate_pages(deck: ParsedDeck, min_chars: int) -> list[int]:
    """Indices (0-based into deck.slides) of pages worth OCR-ing: they carry
    images but little extractable text."""
    out = []
    for idx, s in enumerate(deck.slides):
        if s.image_count > 0 and len(s.text.strip()) < min_chars:
            out.append(idx)
    return out


def maybe_run_ocr(deck: ParsedDeck, path: str | Path, on_progress: ProgressCb = None) -> dict:
    """Recover text for image-only pages in place. Returns a small info dict.

    Mutates ``deck`` (slide text + warnings). Never raises.
    """
    settings = get_settings()
    info = {"attempted": False, "engine": None, "recovered_pages": 0, "candidates": 0}

    if settings.ocr_engine == "off" or deck.kind != "pdf":
        return info

    cands = candidate_pages(deck, settings.ocr_min_chars_per_page)
    info["candidates"] = len(cands)
    if not cands:
        return info

    engine = _select_engine(settings.ocr_engine)
    info["engine"] = engine
    logger.info("OCR: %d image-only page(s) detected; engine=%s (pref=%s)",
                len(cands), engine, settings.ocr_engine)
    if engine is None:
        # No usable engine; keep the image-only warning and add a hint.
        logger.warning("OCR: no usable engine. Set ANTHROPIC_API_KEY (vision) or install Tesseract.")
        deck.warnings.append(
            "OCR was skipped: no OCR engine available. Set ANTHROPIC_API_KEY for "
            "vision OCR, or install Tesseract for local OCR (see README)."
        )
        return info

    info["attempted"] = True
    capped = cands[: settings.ocr_max_pages]

    images = _render_pages(path, capped)
    recovered = 0
    for n, (idx, png) in enumerate(zip(capped, images), start=1):
        if on_progress:
            on_progress(n, len(capped))
        page_no = deck.slides[idx].page
        if png is None:
            logger.warning("OCR p.%d: could not render page image", page_no)
            continue
        text = _ocr_one(png, engine)
        ok = bool(text) and len(text.strip()) >= settings.ocr_min_chars_per_page
        logger.info("OCR p.%d (%s, %d chars)%s: %s",
                    page_no, engine, len(text or ""),
                    "" if ok else "  [too little -> ignored]", preview(text))
        if ok:
            deck.slides[idx].text = text.strip()
            deck.slides[idx].ocr = True
            recovered += 1

    info["recovered_pages"] = recovered
    logger.info("OCR: recovered text on %d/%d page(s)", recovered, len(capped))
    _update_warnings(deck, engine, recovered, len(cands), settings.ocr_max_pages)
    return info


def _select_engine(pref: str) -> Optional[str]:
    if pref == "tesseract":
        return "tesseract" if _tesseract_available() else None
    if pref == "vision":
        return "vision" if _vision_available() else None
    # auto: free local first, then vision
    if _tesseract_available():
        return "tesseract"
    if _vision_available():
        return "vision"
    return None


def _tesseract_available() -> bool:
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # noqa: F401

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _vision_available() -> bool:
    from ..clients.llm import get_llm

    return get_llm().live


def _render_pages(path: str | Path, indices: list[int]) -> list[Optional[bytes]]:
    """Render the given 0-based page indices to PNG bytes via PyMuPDF."""
    try:
        import fitz  # PyMuPDF
    except Exception:
        return [None] * len(indices)

    out: list[Optional[bytes]] = []
    try:
        doc = fitz.open(path)
    except Exception:
        return [None] * len(indices)
    try:
        for idx in indices:
            try:
                page = doc[idx]
                longest = max(page.rect.width, page.rect.height) or 1.0
                zoom = min(2.0, _MAX_RENDER_PX / longest)
                zoom = max(zoom, 1.0)
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
                out.append(pix.tobytes("png"))
            except Exception:
                out.append(None)
    finally:
        doc.close()
    return out


def _ocr_one(png: bytes, engine: str) -> str:
    if engine == "tesseract":
        return _tesseract_ocr(png)
    if engine == "vision":
        from ..clients.llm import get_llm

        return get_llm().ocr_image(png, media_type="image/png")
    return ""


def _tesseract_ocr(png: bytes) -> str:
    try:
        import io

        import pytesseract  # type: ignore
        from PIL import Image

        img = Image.open(io.BytesIO(png))
        return (pytesseract.image_to_string(img) or "").strip()
    except Exception:
        return ""


def _update_warnings(
    deck: ParsedDeck, engine: str, recovered: int, candidates: int, cap: int
) -> None:
    if recovered > 0 and deck.total_chars >= 40:
        # We recovered real text; the original "image-only" warning is now stale.
        deck.warnings[:] = [w for w in deck.warnings if w != IMAGE_ONLY_WARNING]
        label = "local Tesseract" if engine == "tesseract" else "Claude vision"
        note = (
            f"Recovered text from {recovered} image-only page(s) via OCR ({label}). "
            "Treat OCR-extracted figures as lower-confidence and verify key numbers."
        )
        if candidates > cap:
            note += f" Only the first {cap} of {candidates} image pages were OCR'd (cost cap)."
        deck.warnings.append(note)
    elif recovered == 0:
        deck.warnings.append(
            f"OCR ran but recovered no usable text from {candidates} image page(s); "
            "the deck may be low-resolution or non-textual."
        )
