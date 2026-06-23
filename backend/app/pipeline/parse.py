"""Step 1 - Deterministic deck ingestion (no LLM).

Parses PDF or PPTX into a normalized structure: per-page/slide text plus a
count of embedded images. Page numbers flow downstream as deck provenance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedSlide:
    page: int
    text: str
    image_count: int = 0


@dataclass
class ParsedDeck:
    filename: str
    kind: str  # "pdf" | "pptx"
    slides: list[ParsedSlide] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n\n".join(f"[Page {s.page}]\n{s.text}" for s in self.slides)

    @property
    def total_images(self) -> int:
        return sum(s.image_count for s in self.slides)


def parse_deck(path: str | Path) -> ParsedDeck:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _parse_pdf(path)
    if suffix in (".pptx", ".ppt"):
        return _parse_pptx(path)
    raise ValueError(f"Unsupported deck type: {suffix} (use .pdf or .pptx)")


def _parse_pdf(path: Path) -> ParsedDeck:
    import fitz  # PyMuPDF

    deck = ParsedDeck(filename=path.name, kind="pdf")
    with fitz.open(path) as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            images = len(page.get_images(full=True))
            deck.slides.append(ParsedSlide(page=i, text=text, image_count=images))
    return deck


def _parse_pptx(path: Path) -> ParsedDeck:
    from pptx import Presentation
    from pptx.util import Pt  # noqa: F401  (kept for clarity / future use)

    prs = Presentation(str(path))
    deck = ParsedDeck(filename=path.name, kind="pptx")
    for i, slide in enumerate(prs.slides, start=1):
        chunks: list[str] = []
        image_count = 0
        for shape in slide.shapes:
            if shape.has_text_frame and shape.text_frame.text.strip():
                chunks.append(shape.text_frame.text.strip())
            # shape_type 13 == PICTURE
            if getattr(shape, "shape_type", None) == 13:
                image_count += 1
        deck.slides.append(
            ParsedSlide(page=i, text="\n".join(chunks), image_count=image_count)
        )
    return deck
