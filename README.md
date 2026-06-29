# Invest Wisely — AI Pitch Deck Analyzer for VCs

Upload a startup's pitch deck (and, optionally, a pitch recording or transcript) and
get back an **analyst-grade investment memo**: a deck-grounded company snapshot, a
deep team work-up, a real differentiation check, sharp diligence questions,
comp-based valuation reasoning, a pitch-delivery read, a future-scope outlook, and a
single **0–100 investment score** computed over an entity **knowledge graph** — with
**every claim traceable** to a deck page or a research source.

> Judgment-support, not an autograder. It reads like a sharp associate's memo and
> augments — it does not replace — partner judgment.

---

## What it does

1. **Ingests the deck** — PDF or PPTX. If a deck is image-only/scanned, an **OCR layer**
   (Tesseract or Claude Vision) recovers the text so the analysis isn't starved.
2. **Optional pitch recording** — paste a transcript or upload a video. Video is
   transcribed (OpenAI Whisper) and gets a **tone** read; a transcript alone still
   powers a clarity / structure / cross-question (Q&A) **delivery** analysis.
3. **Understands the deck** — an LLM extracts structured, page-cited facts (company,
   market, team, competitors).
4. **Researches the people & company** — web search (Exa) + people enrichment
   (Proxycurl). Founders are looked up even with **no LinkedIn link in the deck** via a
   search **fallback cascade** (see below), and we pull **papers** and **patents** to
   judge credential *depth*, not just existence.
5. **Writes the critical analysis** — a provenance-enforced LLM pass produces the memo:
   team (per-person **and** as-a-whole), competitive differentiation, red flags,
   diligence questions, valuation, future scope, and a recommendation.
6. **Scores it on a knowledge graph** — entities (team, market, traction, valuation,
   legitimacy, delivery, competitors, risks) are linked and the **0–100 score is
   computed over those links**, not as a flat average.
7. **Common ground / icebreakers** — paste your (or anyone's) background and get genuine
   shared history with each founder plus natural openers.
8. **Exports** — PDF / DOCX / HTML, or print.

### Highlights of the analysis logic

- **Founder search fallback cascade** — when the deck gives no LinkedIn URL, we escalate:
  `"<name>" "<company>"` → `<company> team people <name>` → `<name> <deck keywords about them>`
  → generic background, stopping at the first query that returns real hits.
- **Team as a whole** — beyond per-person notes, the team is judged as *one unit*:
  complementarity, the skills they cover vs. what's missing, and fit for the company's
  **stage**. This feeds the score (a strong, complete team lifts execution-dependent
  pillars; missing core functions drag them down).
- **Interlinked, graph-driven score** — individual founders roll up into a **team** node
  that *supports* traction, legitimacy and founder–market fit; market demand *pulls*
  traction; traction *justifies* valuation; competitors and risks apply *pressure*.
  Each LLM-scored node (0–100) is adjusted by these typed edges, and the company score is
  the weighted blend of the resulting effective pillar scores — **the graph explains the
  number**, and the math is deterministic & logged.
- **Future scope** — a realistic upside case (adjacent products/markets/platform plays)
  with the headwinds that would cap it.
- **Provenance everywhere** — every claim carries `source_type`
  (`deck` / `web` / `enrichment` / `inference`), `source_ref` (`deck p.X` or a URL), and a
  `confidence` level.
- **Graceful degradation / mock mode** — runs end-to-end with deck-derived placeholders
  when keys/credits are missing, and never lets a degraded run masquerade as a real,
  different company's memo.

---

## Architecture

```
Upload (deck [+ transcript/video])
   │
   ├─ Parse (PyMuPDF / python-pptx)  ──► OCR layer if image-only (Tesseract / Claude Vision)
   │
   ├─ (Video → Whisper transcript)
   │
   ├─ Deck understanding (LLM, page-cited)
   ├─ Entity extraction (dedupe people/company, carry deck keywords)
   ├─ Research (Exa search + Proxycurl enrichment, CACHED)   ── founder search cascade,
   │                                                            papers + patents
   ├─ Critical analysis (LLM, provenance-enforced)  ──► InvestmentReport (Pydantic)
   ├─ Delivery analysis (LLM, from transcript/video)
   ├─ Knowledge-graph scoring (LLM node scores + deterministic interlinking)
   └─ Report assembly + export (HTML / PDF / DOCX)
                     │
                     ▼
        Next.js dashboard + report view  ◄── icebreakers (on-demand endpoint)
```

### Tech stack

| Layer | Tech |
|-------|------|
| **Backend** | Python · FastAPI · SQLAlchemy (SQLite dev / Postgres-ready) · Pydantic |
| **Frontend** | Next.js (App Router) · React · TypeScript · Tailwind CSS |
| **LLM** | Anthropic Claude (deck understanding, analysis, delivery, scoring) |
| **Research** | Exa (web search) · Proxycurl (people enrichment) |
| **Transcription / OCR** | OpenAI Whisper (video) · Tesseract / Claude Vision (image-only decks) |
| **Parsing** | PyMuPDF (PDF) · python-pptx (PPTX) |
| **Export** | Jinja2 → HTML · WeasyPrint → PDF · python-docx → DOCX |
| **Jobs / caching** | FastAPI BackgroundTasks · research cache (keyed by name+company) to avoid re-billing |
| **Observability** | Centralized, ASCII-safe logging of every stage, LLM call, token use, and OCR result |

### Backend layout (`backend/app/`)

```
main.py                  FastAPI app: upload, status, export, icebreakers, delete
config.py                settings / API keys / feature flags
schemas.py               Pydantic models (the InvestmentReport contract)
db.py                    SQLAlchemy models + lightweight SQLite migrations
obs.py                   logging setup
clients/                 llm.py · search.py (Exa) · enrichment.py (Proxycurl) · cache.py · _resilience.py
pipeline/
  parse.py               PDF/PPTX text + image extraction
  ocr.py                 hybrid OCR for image-only decks
  transcript.py          transcript parsing + Whisper video transcription
  deck_understanding.py  LLM → structured, page-cited deck facts
  entities.py            dedupe/normalize people & company (+ deck keywords)
  research.py            Exa + Proxycurl, founder search cascade, papers/patents, cached
  analysis.py            LLM → full InvestmentReport (provenance-enforced)
  delivery.py            LLM → pitch delivery / Q&A analysis
  scoring.py             knowledge-graph-driven 0–100 score + risk breakdown
  icebreakers.py         on-demand common-ground finder
  report.py              HTML / PDF / DOCX export
  runner.py              orchestrates the stages with logging + graceful degradation
```

### Resilience

- Rate limiting + exponential backoff on external APIs; exhausted retries degrade to
  mock results instead of crashing the run.
- LLM JSON is repaired if truncated/malformed; OCR failures are isolated so they can't
  degrade the whole run.
- Cost guards cap how many people/competitors a single deck can fan out into.

---

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
# optional native extras (PDF export, local OCR, Whisper):
pip install -r requirements-optional.txt
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
cp .env.local.example .env.local   # points at http://localhost:8000 by default
npm run dev                        # http://localhost:3000
```

---

## API keys (`.env`)

| Key | Purpose | Get it from |
|-----|---------|-------------|
| `ANTHROPIC_API_KEY` | LLM: deck understanding, analysis, delivery, scoring | console.anthropic.com |
| `EXA_API_KEY` | Web research / competitor + comp discovery / founder lookup | exa.ai |
| `PROXYCURL_API_KEY` | People enrichment (founder work history) | nubela.co/proxycurl |
| `OPENAI_API_KEY` | Whisper video transcription (optional) | platform.openai.com |

Leave any key as a `PLACEHOLDER_…` value to run that step in **mock mode**. With no keys
at all, the full pipeline still runs on deck-derived placeholders so you can demo the UI.

---

## HTTP API (selected)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/decks` | Upload a deck (multipart) + optional `transcript_text` / `transcript` / `video` |
| `GET`  | `/api/decks` | List decks (status, recommendation, flags) |
| `GET`  | `/api/decks/{id}` | Deck detail + full report (poll while processing) |
| `POST` | `/api/decks/{id}/icebreakers` | Common ground / openers for a supplied background |
| `GET`  | `/api/decks/{id}/export?format=pdf\|docx\|html` | Download the memo |
| `DELETE` | `/api/decks/{id}` | Remove a deck |
| `GET`  | `/health` | Mode + which integrations are live |

---

## Report structure

1. Company snapshot · 2. Team analysis (per-person **+ team as a whole**) ·
3. Competitive landscape · 4. Red flags (ranked) · 5. Diligence questions ·
6. Valuation analysis · 7. Future scope · 8. Recommendation ·
9. Pitch delivery & Q&A (when a recording/transcript is provided)

Plus, up top: a consolidated executive summary and the **0–100 investment score** with a
risk breakdown and the **entity knowledge graph** that produced it. An on-report panel
finds **common ground / icebreakers** with the founders from a background you paste in.
