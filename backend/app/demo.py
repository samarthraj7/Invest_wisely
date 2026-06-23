"""Generates a placeholder pitch deck (PDF) so the pipeline can be exercised
end-to-end before a real deck is supplied. Used by `analyze_deck.py --demo`.
"""
from __future__ import annotations

from pathlib import Path

_SLIDES = [
    ("NimbusGrid", "AI-driven load balancing for industrial battery storage sites.\nSeed round."),
    ("Problem", "Grid-storage operators waste energy and money with manual dispatch."),
    ("Solution", "Real-time AI dispatch. Reduces grid-storage operating costs by 30%."),
    ("Market", "Targeting $48B grid-storage software market by 2030."),
    ("Traction", "$1.2M ARR with 8 enterprise pilots."),
    ("Technology", "Proprietary forecasting model is 10x more accurate."),
    ("Competition", "No direct competitor offers real-time AI dispatch.\nNamed: Stem Inc, Fluence."),
    ("Business model", "Per-site SaaS subscription + usage."),
    ("Team", "Dana Okafor — CEO & Co-founder.\nMarc Liang — CTO & Co-founder."),
    ("Ask", "Raising $4M seed at $20M post-money."),
]


def generate_demo_deck(out_dir: str | Path) -> Path:
    import fitz  # PyMuPDF

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "demo_nimbusgrid_deck.pdf"

    doc = fitz.open()
    for title, body in _SLIDES:
        page = doc.new_page(width=720, height=540)
        page.insert_text((48, 90), title, fontsize=34, fontname="helv")
        page.insert_text((48, 160), body, fontsize=18, fontname="helv")
    doc.save(str(path))
    doc.close()
    return path
