# Sample decks

This folder ships with three **synthetic** pitch decks (fictional companies)
so you have real files to upload through the app immediately:

| File | Profile | What it's good for testing |
|------|---------|----------------------------|
| `nimbusgrid_seed_deck.pdf` | Climate / energy SaaS, seed | Overstated "unique" claim; rich ask vs. comps |
| `careloop_health_seed_deck.pdf` | Regulated healthtech, seed | Missing clinical/regulatory advisor; FDA/HIPAA gaps |
| `aether_robotics_seed_deck.pdf` | Hardware robotics, seed | All-software team on a hardware venture; pre-revenue |

Upload any of these via the web UI, or run from `backend/`:

```bash
python analyze_deck.py ../sample_decks/careloop_health_seed_deck.pdf
```

## Regenerate / add more

These are produced by `backend/make_sample_decks.py`:

```bash
cd backend
python make_sample_decks.py
```

Drop your own real decks (`.pdf` / `.pptx`) here too — anything in this folder
can be passed to the CLI or uploaded through the app.

## Note on mock mode

Without API keys the pipeline runs in **mock mode**, which returns a fixed
sample analysis (the NimbusGrid memo) regardless of which deck you upload —
it's there to exercise the end-to-end flow and UI. Add `ANTHROPIC_API_KEY` +
`EXA_API_KEY` to `.env` to get a real, deck-specific analysis.
