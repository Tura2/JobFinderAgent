# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All backend commands run from `backend/` with the venv active.

```bash
# Setup
cd backend && python -m venv venv && source venv/Scripts/activate  # Windows
pip install -r requirements.txt

# Dev server
uvicorn app.main:app --reload --port 8000

# Tests
pytest                          # all tests with coverage
pytest tests/test_foo.py        # single file
pytest -k "test_name"           # single test

# Lint / format
ruff check app/ tests/
ruff format app/ tests/
```

Frontend (once scaffolded) runs from `frontend/`:
```bash
npm install && npm run dev      # Vite dev server
npm run build                   # production build → served by FastAPI as static files
```

## Architecture

Single-process FastAPI backend that serves both the REST API and the React PWA static build. Deployed as a systemd service on an Oracle Cloud Ubuntu VM.

### Pipeline flow (background)

```
APScheduler (every SCAN_INTERVAL_HOURS)
  → Ingestion layer (ATS API fetcher or Scrapling scraper per company)
  → Normalizer (unified job schema)
  → Dedup (content_hash = hash(company_id + title + url))
  → AI Matchmaker via OpenRouter (score 0–100)
  → score ≥ MATCH_THRESHOLD → CV Selector → SQLite match saved → Telegram notification
```

### Module map

| Path | Responsibility |
|---|---|
| `backend/app/models/` | SQLModel table definitions: `Company`, `Job`, `Match`, `CVVariant`, `Application` |
| `backend/app/ingestion/` | Fetchers: ATS API (Greenhouse/Lever) and Scrapling (Workday/custom/LinkedIn) |
| `backend/app/pipeline/` | Normalizer, dedup, AI matchmaker (OpenRouter), CV selector |
| `backend/app/notifications/` | Telegram bot sender |
| `backend/app/routers/` | FastAPI route handlers (matches, tracker, companies, cv-variants, scan) |
| `backend/app/main.py` | App factory, scheduler setup, static file mount |
| `frontend/src/` | React 18 + Vite + Tailwind mobile PWA |

### Key design decisions

- **Single-user, token-auth only.** Every API route checks `Authorization: Bearer <PWA_ACCESS_TOKEN>`. No login UI.
- **No auto-apply.** The pipeline stops at Telegram notification; the user applies manually.
- **CV variants are data, not code.** Loaded from `cv_variants` table; variant logic is keyword matching against `focus_tags` JSON array.
- **content_hash dedup.** Jobs are never re-processed once seen; hash is on `company_id + title + url`.
- **Near misses.** Jobs scored below `MATCH_THRESHOLD` are saved with `status=low_match` — visible in PWA but no Telegram sent.
- **OpenRouter retries.** Max 3 retries via `tenacity`; failed matches are queued for next scheduler tick.

### ATS ingestion strategy

| ATS | Method |
|---|---|
| Greenhouse | Direct JSON API: `boards.greenhouse.io/{slug}/jobs` |
| Lever | Direct JSON API: `api.lever.co/v0/postings/{slug}` |
| Workday / custom pages | Scrapling `StealthyFetcher` with adaptive selectors |
| LinkedIn | Scrapling `DynamicFetcher` (JS render + stealth); skipped gracefully on block |

### Match lifecycle statuses

`low_match → new → reviewed → skipped / applied → interview / offer / rejected / no_response`

### Environment variables

Copy `backend/.env.example` to `backend/.env`. Key vars:

| Var | Purpose |
|---|---|
| `OPENROUTER_API_KEY` / `OPENROUTER_MODEL` | LLM provider |
| `MATCH_THRESHOLD` | Score cutoff (0–100, default 65) |
| `SCAN_INTERVAL_HOURS` | Scheduler frequency |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | Notifications |
| `PWA_ACCESS_TOKEN` | Static bearer auth for all API routes |
| `DATABASE_URL` | SQLite path (`sqlite:///./jobfinder.db`) |
| `APPLICANT_*` | Name/email/LinkedIn/portfolio for ATS pre-fill links |

### API surface (FastAPI)

```
GET/POST       /companies, /companies/{id}
GET/POST/DEL   /cv-variants, /cv-variants/{id}
GET            /matches, /matches/{id}
POST           /matches/{id}/skip, /matches/{id}/applied
GET            /tracker
PATCH          /applications/{id}
POST           /trigger-scan
GET            /scan-status
```

### Implementation phases (plan: `docs/superpowers/plans/2026-04-18-job-finder-agent-plan.md`)

1. Scaffold + Config + Database
2. Ingestion layer (ATS APIs + Scrapling)
3. Pipeline (normalizer, dedup, AI matchmaker, CV selector)
4. Notifications (Telegram)
5. REST API (FastAPI routers)
6. React PWA (mobile UI)
7. Deployment (systemd, VM setup)
