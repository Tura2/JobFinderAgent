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

Frontend runs from `frontend/`:
```bash
npm install && npm run dev      # Vite dev server (proxies API to localhost:8000)
npm run build                   # production build → served by FastAPI as static files
npx vitest run                  # frontend unit tests
```

## Recommended OpenRouter Model

Set `OPENROUTER_MODEL` in `.env`.

**Recommended paid model (default):**

| Model ID | Why good |
|---|---|
| `deepseek/deepseek-v4-flash` | **Default** — fast, cheap, excellent JSON output, reliable `json_object` support |

**Best free options** (set if you have no credits):

| Model ID | Why good |
|---|---|
| `meta-llama/llama-3.3-70b-instruct:free` | IFEval 92.1% (best instruction following), 14 providers, most reliable `json_object` support |
| `nvidia/nemotron-3-super-120b-a12b:free` | Agentic-first design, hardware-accelerated structured output |
| `google/gemma-4-31b-it:free` | Strong benchmarks (GPQA 84.3%), native function calling — but new, test before committing |

> **Avoid:**
> - `openai/gpt-oss-120b:free` — `json_schema` mode broken on some providers; use with explicit JSON prompt only
> - `google/gemma-3-27b-it:free` — JSON/tool mode confirmed broken on free tier (400 errors)
> - `deepseek/*:free` — removed from OpenRouter free tier (2026-04-19)
> - `qwen/qwen3-35b-a3b:free` — removed from OpenRouter (caused 400 errors May 2026)

The matchmaker uses `response_format: {type: "json_object"}` so any model that supports that mode works best.

### Rate limits

- **Without credits:** 20 RPM / 50 RPD — insufficient for a 50-job scan (burns entire daily budget in one run)
- **With $10+ credits loaded:** 20 RPM / 1,000 RPD — ~20 full scans/day at no extra per-token cost on free models
- Credits are consumed only for paid models; free `:free` models stay free regardless of credit balance

## Architecture

Single-process FastAPI backend that serves both the REST API and the React PWA static build. Deployed as a systemd service on an Oracle Cloud Ubuntu VM.

### Pipeline flow (background)

```
APScheduler (every SCAN_INTERVAL_HOURS)
  → Ingestion layer (ATS API fetcher or Scrapling scraper per company)
  → Normalizer (unified job schema)
  → Dedup (content_hash = hash(company_id + title + url))
  → Pre-filter: title allowlist (dev/R&D keywords) + blocklist + Israel/remote location
  → AI Matchmaker via OpenRouter (score 0–100)
  → score ≥ MATCH_THRESHOLD → CV Selector → SQLite match saved → Telegram notification
```

**Pre-filter logic** (`backend/app/scheduler.py`):
- **Allowlist** (`INCLUDED_TITLE_KEYWORDS`): only jobs whose title contains engineering/dev keywords (engineer, developer, architect, full stack, frontend, backend, software, r&d, devops, data scientist, machine learning, tech lead). Saves ~88% of LLM tokens on non-dev-heavy companies like NICE.
- **Blocklist** (`EXCLUDED_TITLE_KEYWORDS`): explicit non-dev roles regardless of title (account executive, sales, customer success, presales, project manager, program manager, etc.).
- **Location filter** (`ISRAEL_LOCATION_KEYWORDS`): keep jobs with no location, Israel cities, or any "remote" mention. Skip jobs with on-site locations outside Israel. The LLM `location` subscore (max 10 pts) further penalises non-Israel remotes.
- **Recovery**: jobs that were ingested but never scored (matchmaker failure) are automatically picked up on the next scan via the `unscored_jobs` query — no manual reset needed.

### Module map

| Path | Responsibility |
|---|---|
| `backend/app/models/` | SQLModel table definitions: `Company`, `Job`, `Match`, `CVVariant`, `Application` |
| `backend/app/ingestion/` | Fetchers: ATS API (Greenhouse/Lever) and Scrapling (Workday/custom/LinkedIn) |
| `backend/app/pipeline/` | Normalizer, dedup, AI matchmaker (OpenRouter), CV selector |
| `backend/app/notifications/` | Telegram bot sender |
| `backend/app/routers/` | FastAPI route handlers (matches, tracker, companies, cv-variants, scan) |
| `backend/app/main.py` | App factory, scheduler setup, static file mount |
| `backend/app/scheduler.py` | APScheduler orchestrator — ties fetch → normalize → score → notify |
| `backend/user_profile.md` | Candidate profile fed to matchmaker — fill this in before first run |
| `frontend/src/` | React 18 + Vite + Tailwind mobile PWA |

### Key design decisions

- **Session cookie auth.** Login page at `/login` accepts `PWA_ACCESS_TOKEN` as the password and issues an HMAC-signed `session` cookie (`expiry:sha256(secret, expiry)`). All API routes are protected by `SessionMiddleware` except the public paths: `/login`, `/auth/login`, `/auth/logout`, `/health`, `/config`.
- **No auto-apply.** The pipeline stops at Telegram notification; the user applies manually.
- **CV variants are data, not code.** Loaded from `cv_variants` table; variant logic is keyword matching against `focus_tags` JSON array.
- **content_hash dedup.** Jobs are never re-processed once seen; hash is on `company_id + title + url`.
- **Near misses.** Jobs scored below `MATCH_THRESHOLD` are saved with `status=low_match` — visible in PWA but no Telegram sent.
- **OpenRouter retries.** Max 3 retries via `tenacity`; failed matches are queued for next scheduler tick.
- **Duplicate Telegram guard.** `Match.telegram_message_id` is set after first send; subsequent calls are a no-op.
- **ATS pre-fill.** `POST /matches/{id}/applied` constructs a pre-filled Greenhouse/Lever URL from `APPLICANT_*` env vars.

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
| `OPENROUTER_API_KEY` / `OPENROUTER_MODEL` | LLM provider (see model table above) |
| `MATCH_THRESHOLD` | Score cutoff (0–100, default 65) |
| `SCAN_INTERVAL_HOURS` | Scheduler frequency |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | Notifications |
| `PWA_ACCESS_TOKEN` | Login password for the `/login` form |
| `SESSION_SECRET_KEY` | **Required.** HMAC secret for signing session cookies |
| `SESSION_MAX_AGE_DAYS` | Cookie lifetime in days (default 30) |
| `PWA_BASE_URL` | Comma-separated allowed CORS origins (default `http://localhost:8000`) |
| `DATABASE_URL` | SQLite path (`sqlite:///./jobfinder.db`) |
| `APPLICANT_*` | Name/email/LinkedIn/portfolio for ATS pre-fill links |

Frontend env: copy `frontend/.env.example` to `frontend/.env.local` (gitignored):

```env
VITE_API_URL=http://<vm-ip>:8000
```

### API surface (FastAPI)

```text
GET            /login                    Login page (HTML)
POST           /auth/login               Submit password → sets session cookie
POST           /auth/logout              Clears session cookie
GET            /config                   Public: returns applicant linkedin_url
GET            /matches                  Pending matches (status=new), score desc
GET            /matches/near-misses      Below-threshold matches (status=low_match)
GET            /matches/{id}             Detail + ambiguous_variants if CV tie
POST           /matches/{id}/skip        → status=skipped
POST           /matches/{id}/applied     → status=applied, creates Application, returns pre-filled ats_url
GET            /companies                Watchlist
POST           /companies                Add company
PATCH          /companies/{id}           Update (toggle active, fix slug)
DELETE         /companies/{id}           Remove
GET            /cv-variants              Active variants
POST           /cv-variants              Add variant
DELETE         /cv-variants/{id}         Deactivate (soft delete)
GET            /tracker                  All applications with joined job/company
PATCH          /applications/{id}        Update outcome_status / notes
POST           /trigger-scan             Manual scan (background task)
GET            /scan-status              Last scan time, job count, is_running
GET            /health                   Liveness check
```

### Testing notes

`conftest.py` sets `SESSION_SECRET_KEY` and `PWA_ACCESS_TOKEN` via `os.environ.setdefault` **before any app import** because `Settings()` is instantiated at module level. Any new required env vars must be added there too, or tests will fail with a `ValidationError` at import time.

The `client` fixture injects a valid session cookie automatically — no need to handle auth in individual tests.

### Git history (phase-by-phase)

```
1937a94  docs: add design spec and implementation plan
314dbf2  chore: scaffold project structure and dependencies
32f507c  feat: add config, database engine, and all SQLModel models
c227aed  feat: add ingestion engine (ATS APIs, Scrapling, normalizer)
c1d8956  feat: add AI pipeline (OpenRouter matchmaker + CV selector)
6f33a91  feat: add Telegram notifications and APScheduler orchestrator
9256683  feat: add FastAPI app with all API routers
922bf1c  chore: add systemd service and deploy script
4d88d46  feat: add React PWA frontend (Vite + Tailwind + Vitest)
```

### Deployment

```bash
# On VM — first time
git clone <repo> ~/JobFinderAgent
cd ~/JobFinderAgent && bash scripts/deploy.sh

# Service management
sudo systemctl status jobfinder
sudo journalctl -u jobfinder -f
```

> **Branch note:** dev branch is `master`; `scripts/deploy.sh` pulls from `main`. Push to `main` before deploying.

### DB schema changes

No Alembic — add columns manually on existing DBs:
```bash
sqlite3 backend/jobfinder.db "ALTER TABLE <table> ADD COLUMN <col> <type> DEFAULT NULL;"
```
Example: `score_breakdown TEXT DEFAULT NULL` was added to `matches` in 2026-04.

### Company seeding

`python scripts/seed_companies.py` bulk-inserts from `scripts/companies_seed.json` via the REST API.
- Seed file field is `name` (not `company_name`)
- Token auto-loaded from `backend/.env` (`PWA_ACCESS_TOKEN`)
- Use `--dry-run` to preview before inserting
- 68 Israeli tech companies pre-loaded in `scripts/companies_seed.json`
