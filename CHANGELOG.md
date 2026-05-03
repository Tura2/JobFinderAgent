# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] — 2026-05-03

### Added

- **Full job ingestion pipeline** — Greenhouse and Lever direct JSON APIs; Scrapling `StealthyFetcher` for Workday/custom pages; `DynamicFetcher` (JS render + stealth) for LinkedIn
- **AI matchmaker** — OpenRouter LLM scores each job 0–100 across 5 weighted dimensions: tech stack (30), role type (25), domain (20), seniority (15), location (10)
- **CV variant selector** — keyword-based matching against `focus_tags` picks the most relevant CV per job
- **Telegram notifications** — instant alert on new matches with score, reasoning, and ATS pre-fill link; duplicate guard via `telegram_message_id`
- **APScheduler orchestrator** — configurable scan interval; background task per company; unscored job recovery on each tick
- **React PWA dashboard** — matches, near-misses, application tracker, company watchlist, manual scan trigger
- **Session cookie auth** — HMAC-signed cookie; login rate limiting (5 failures / 60s per IP)
- **ATS pre-fill links** — constructs Greenhouse/Lever application URLs from `APPLICANT_*` env vars
- **Near-miss storage** — jobs below threshold saved as `low_match`; visible in PWA, no Telegram sent; promotable to `new`
- **Score breakdown** — per-dimension scores stored as JSON on each match
- **Pre-filter pipeline** — title allowlist (dev/R&D keywords) + blocklist + Israel/remote location filter; saves ~88% of LLM tokens on non-dev-heavy companies
- **Pagination** — `?page=&limit=` on `/matches`, `/matches/near-misses`, and `/tracker`; `X-Total-Count` response header
- **Batch cap** — `SCAN_BATCH_SIZE` (default 50) limits unscored job recovery per scan tick
- **Company health-check** — `POST /companies/{id}/test` and monthly scheduler job; stores `last_test_at`, `last_test_passed`, `last_test_jobs_found`
- **Scan status UI** — auto-resumes progress indicator on mount if a scan is already running
- **`run_batch_test.py`** — CLI script to health-check all active companies and print pass/fail results
- **68 Israeli tech companies** pre-loaded in `scripts/companies_seed.json`

### Changed

- Default OpenRouter model changed to `deepseek/deepseek-v4-flash` (reliable JSON output, low cost)
- Settings polling interval reduced from 2s to 5s to lower API load during scans
- `user_profile.md` shipped as an anonymized template; fill in your own profile before first run

### Fixed

- OpenRouter 429 responses now honour the `Retry-After` header before re-raising
- Matchmaker retried when OpenRouter returns 200 with no `choices` key (silent rate-limit)
- Duplicate `Match.job_id` constraint added to prevent double-scoring
- Orphaned jobs (ingested but never scored due to prior matchmaker failure) automatically picked up on next scan
- ATS apply URL opens synchronously in browser tab; post-apply confirmation added
- Logout returns JSON 200 so `fetch()` receives `Set-Cookie` directly (302 responses followed silently by fetch)
