#!/usr/bin/env python
"""CLI to run the full analysis pipeline on a deck and print/export the report.

Usage:
  python analyze_deck.py path/to/deck.pdf
  python analyze_deck.py --demo            # generate + analyze a placeholder deck
  python analyze_deck.py path/to/deck.pdf --json     # dump structured JSON
  python analyze_deck.py path/to/deck.pdf --export   # also write an HTML/PDF memo
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import get_settings  # noqa: E402
from app.db import init_db  # noqa: E402
from app.pipeline import report as report_mod  # noqa: E402
from app.pipeline.runner import run_pipeline  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Analyze a pitch deck.")
    ap.add_argument("deck", nargs="?", help="Path to a .pdf or .pptx deck")
    ap.add_argument("--demo", action="store_true", help="Generate and analyze a placeholder deck")
    ap.add_argument("--json", action="store_true", help="Print full structured JSON")
    ap.add_argument("--export", action="store_true", help="Write an HTML/PDF memo")
    args = ap.parse_args()

    init_db()
    settings = get_settings()
    mock = not (settings.has_llm and settings.has_search)
    print(f"\n{'='*60}\n  Invest Wisely — pipeline run  (mock_mode={mock})\n{'='*60}")

    if args.demo:
        from app.demo import generate_demo_deck

        deck_path = generate_demo_deck(settings.storage_dir / "uploads")
        print(f"  Generated demo deck: {deck_path}")
    elif args.deck:
        deck_path = Path(args.deck)
        if not deck_path.exists():
            sys.exit(f"File not found: {deck_path}")
    else:
        ap.error("Provide a deck path or --demo")

    result = run_pipeline(deck_path, on_stage=lambda s: print(f"  • {s}..."))
    r = result.report

    if args.json:
        print(json.dumps(r.model_dump(mode="json"), indent=2))
    else:
        rec = r.recommendation
        print(f"\n  COMPANY:  {r.company_snapshot.name} — {r.company_snapshot.one_liner}")
        print(f"  ASK:      {r.company_snapshot.ask}")
        print(f"  VAL RANGE:{r.valuation.range_low} – {r.valuation.range_high}")
        print(f"\n  RED FLAGS ({len(r.red_flags)}):")
        for f in r.red_flags:
            print(f"    [{f.severity.value.upper()}] {f.title}")
        print(f"\n  RECOMMENDATION: {rec.recommendation.value.upper()}  "
              f"(risk: {rec.risk_rating})")
        print(f"  CHECK: {rec.suggested_check_size}")
        print(f"\n  DILIGENCE QUESTIONS ({len(r.diligence_questions)}):")
        for q in r.diligence_questions:
            print(f"    - {q.question}")

    if args.export:
        out = settings.storage_dir / "reports" / f"cli_{r.company_snapshot.name}"
        path, fmt = report_mod.export_pdf(r, out)
        print(f"\n  Exported {fmt.upper()} -> {path}")

    print()


if __name__ == "__main__":
    main()
