#!/usr/bin/env python
"""Generate a few realistic (synthetic) sample pitch decks as PDFs.

These are fictional companies built to exercise different analysis paths
(a climate SaaS, a regulated healthtech, and a hardware/robotics play with a
software-only team). Output goes to ../sample_decks/ so you have real files to
upload through the app.

Usage:
    python make_sample_decks.py
"""
from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

OUT_DIR = Path(__file__).resolve().parent.parent / "sample_decks"

# (filename, accent_rgb, [(title, subtitle, [bullets...]), ...])
DECKS: dict[str, tuple[tuple[float, float, float], list[tuple[str, str, list[str]]]]] = {
    "nimbusgrid_seed_deck.pdf": (
        (0.27, 0.36, 0.93),
        [
            ("NimbusGrid", "AI-driven load balancing for industrial battery storage", []),
            ("Problem", "", ["Grid-storage operators dispatch manually",
                             "Wasted energy and revenue at every site",
                             "Operators lack real-time optimization"]),
            ("Solution", "", ["Real-time AI dispatch across storage sites",
                              "Reduces grid-storage operating costs by 30%",
                              "Drop-in software, no hardware changes"]),
            ("Product", "", ["Cloud platform + on-site agent",
                             "Forecasting + dispatch optimization engine",
                             "Live dashboards and alerts"]),
            ("Market", "", ["Grid-storage software TAM of $48B by 2030",
                            "Driven by renewables + storage buildout"]),
            ("Traction", "", ["$1.2M ARR", "8 enterprise pilots",
                              "2 signed multi-year contracts"]),
            ("Business model", "", ["Per-site SaaS subscription",
                                    "Usage-based optimization fees"]),
            ("Competition", "", ["Stem Inc and Fluence named as competitors",
                                 "We claim: no direct competitor offers real-time AI dispatch"]),
            ("Team", "", ["Dana Okafor - CEO & Co-founder (ex-software, B2C)",
                          "Marc Liang - CTO & Co-founder (ML, ex-adtech)"]),
            ("Ask", "", ["Raising $4M seed at $20M post-money",
                         "18 months runway; hire sales + 2 ML engineers"]),
        ],
    ),
    "careloop_health_seed_deck.pdf": (
        (0.05, 0.65, 0.55),
        [
            ("CareLoop Health", "AI triage assistant for primary-care clinics", []),
            ("Problem", "", ["Clinics overwhelmed by patient intake",
                             "Nurses spend hours on phone triage",
                             "Patients wait days for guidance"]),
            ("Solution", "", ["AI triage chat + clinician dashboard",
                              "Routes patients to the right care level",
                              "Cuts intake workload by 40%"]),
            ("Product", "", ["Patient-facing symptom intake",
                             "Clinician review + override workflow",
                             "EHR integration (pilot with one EHR)"]),
            ("Market", "", ["US primary care software market $12B",
                            "20k independent clinics as initial segment"]),
            ("Traction", "", ["3 paid clinic pilots", "$180K ARR",
                              "92% triage agreement vs. nurse baseline (internal)"]),
            ("Regulatory", "", ["Positioned as clinical decision support",
                                "FDA pathway 'under review' (no submission yet)",
                                "No HIPAA security audit completed yet"]),
            ("Competition", "", ["Named: Zocdoc, Ada Health",
                                 "We claim deeper EHR integration"]),
            ("Team", "", ["Priya Nair - CEO (ex-consultant, first-time founder)",
                          "Tomas Reyes - CTO (ex-fintech eng lead)",
                          "No clinical/regulatory co-founder or advisor listed"]),
            ("Ask", "", ["Raising $3.5M seed at $18M post-money",
                         "Build regulatory + clinical team"]),
        ],
    ),
    "aether_robotics_seed_deck.pdf": (
        (0.55, 0.25, 0.85),
        [
            ("Aether Robotics", "Autonomous warehouse picking robots", []),
            ("Problem", "", ["Warehouse labor shortages",
                             "Picking is 60% of fulfillment cost",
                             "Existing automation is rigid and costly"]),
            ("Solution", "", ["General-purpose picking robot arm",
                              "Vision + grasp-planning software",
                              "Deploys in days, not months"]),
            ("Product", "", ["Robot hardware + control software",
                             "Cloud fleet management",
                             "Prototype v1 in lab testing"]),
            ("Market", "", ["Warehouse automation market $30B by 2030",
                            "E-commerce growth as tailwind"]),
            ("Traction", "", ["1 LOI from a regional 3PL",
                              "Prototype demonstrated in lab",
                              "No revenue yet"]),
            ("Business model", "", ["Robotics-as-a-Service (monthly per robot)",
                                    "Software attach fee"]),
            ("Competition", "", ["Named: Symbotic, Berkshire Grey",
                                 "We claim faster deployment + lower cost"]),
            ("Team", "", ["Sam Whitfield - CEO (ex-SaaS PM)",
                          "Lena Park - CTO (computer vision PhD)",
                          "Eng team is all-software; no hardware/mechanical lead"]),
            ("Ask", "", ["Raising $5M seed at $25M post-money",
                         "Build hardware team + first 10 units"]),
        ],
    ),
}


def _render(path: Path, accent: tuple[float, float, float],
            slides: list[tuple[str, str, list[str]]]) -> None:
    doc = fitz.open()
    for title, subtitle, bullets in slides:
        page = doc.new_page(width=720, height=540)
        page.draw_rect(fitz.Rect(0, 0, 720, 14), color=accent, fill=accent)
        page.insert_text((48, 96), title, fontsize=34, fontname="hebo", color=(0.1, 0.12, 0.16))
        y = 150
        if subtitle:
            page.insert_text((48, y), subtitle, fontsize=18, fontname="helv",
                             color=(0.3, 0.34, 0.4))
            y += 50
        for b in bullets:
            page.insert_text((60, y), f"\u2022  {b}", fontsize=16, fontname="helv",
                             color=(0.16, 0.2, 0.26))
            y += 34
    doc.save(str(path))
    doc.close()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, (accent, slides) in DECKS.items():
        out = OUT_DIR / name
        _render(out, accent, slides)
        print(f"  wrote {out.relative_to(OUT_DIR.parent)}  ({len(slides)} slides)")
    print(f"\nDone. {len(DECKS)} sample decks in {OUT_DIR}")


if __name__ == "__main__":
    main()
