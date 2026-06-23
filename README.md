# Invest Wisely — AI Pitch Deck Analyzer for VCs

Upload a startup's pitch deck (PDF/PPTX) and get back an analyst-grade investment
memo: team risk flags, real differentiation check, sharp diligence questions,
comp-based valuation reasoning, and a final recommendation — **every claim
traceable to a deck page or a research source.**

> Judgment-support, not an autograder. Reads like a sharp associate's memo and
> augments — does not replace — partner judgment.

## Architecture

```
Upload → Parse (PDF/PPTX) → Deck understanding (LLM) → Entity extraction
       → Research (Exa search + Proxycurl enrichment, CACHED)
       → Critical analysis (LLM, provenance-enforced) → Report → Dashboard
```

- **Backend** — Python + FastAPI. Parsing, research pipeline, analysis, SQLite storage. (`backend/`)
- **Frontend** — Next.js + Tailwind. Upload flow, report view, multi-deck dashboard. (`frontend/`)
- **Provenance** — every claim carries `source_type` (`deck`/`web`/`enrichment`/`inference`),
  `source_ref` (`deck p.X` or a URL), and a `confidence` level.
- **Mock mode** — runs end-to-end with deterministic sample research when API keys
  are placeholders, so you can demo without any keys.

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
cp ../.env.example ../.env         # fill in keys, or leave placeholders for mock mode

# Run the pipeline from the CLI (no server needed):
python analyze_deck.py --demo --export
python analyze_deck.py ../sample_decks/your_deck.pdf

# Or start the API:
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev        # http://localhost:3000
```

## API keys (`.env`)

| Key | Purpose | Get it from |
|-----|---------|-------------|
| `ANTHROPIC_API_KEY` | LLM (deck understanding + analysis) | console.anthropic.com |
| `EXA_API_KEY` | Web research / competitor + comp discovery | exa.ai |
| `PROXYCURL_API_KEY` | People enrichment (founder work history) | nubela.co/proxycurl |

Leave any key as a `PLACEHOLDER_…` value to run that step in mock mode.

## Report structure

1. Company snapshot · 2. Team analysis · 3. Competitive landscape ·
4. Red flags (ranked) · 5. Diligence questions · 6. Valuation analysis ·
7. Recommendation (with named risk factors).
