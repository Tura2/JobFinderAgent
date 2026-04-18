# JobFinderAgent — Design Specification

**Date:** 2026-04-17
**Status:** Approved
**Author:** Offir (via brainstorming session)

---

## 1. Problem Statement

Job hunting is an exhausting, friction-heavy process. Continuously monitoring job boards, filtering irrelevant positions, and manually tailoring a CV for each role takes too much time. The goal is an autonomous pipeline that handles all repetitive "grunt work" while keeping the human in control of every application decision.

---

## 2. Concept

A "sniper" job hunting agent — not broad spray-and-pray, but a focused watchlist of hand-picked target companies. The system monitors their career pages, evaluates each new posting against the user's profile, prepares a tailored application package, and notifies the user for a final human decision. No auto-applying.

---

## 3. Deployment Environment

- **Host:** Oracle Cloud Ubuntu VM (existing)
- **Service type:** Standalone — completely independent from openclaw and any other running services
- **Process management:** systemd unit (auto-restart on VM reboot)
- **Database:** SQLite (single file, simple backup)

---

## 4. Architecture

### 4.1 Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12 + FastAPI |
| Scraping | Scrapling (StealthyFetcher, DynamicFetcher) |
| ATS APIs | Direct HTTP/JSON (Greenhouse, Lever) |
| Scheduler | APScheduler |
| LLM | OpenRouter (model configurable via env) |
| Database | SQLite via SQLModel/SQLAlchemy |
| Notifications | python-telegram-bot |
| Frontend | TypeScript + React (Vite) — mobile PWA |
| Serving | FastAPI serves both API and static PWA build |

### 4.2 System Diagram

```
APScheduler (every N hours — configurable)
  │
  ├─ ATS API Fetcher ──────────────────────────────┐
  │   Greenhouse: boards.greenhouse.io/{slug}/jobs  │
  │   Lever:      api.lever.co/v0/postings/{slug}   │
  │                                                  │
  ├─ Scrapling StealthyFetcher ─────────────────────┤
  │   Workday + custom career pages                  │
  │   adaptive selectors — survives page redesigns  │
  │                                                  │
  └─ Scrapling DynamicFetcher (optional) ───────────┤
      LinkedIn company pages — stealth + JS render   │
                                                     │
                                              Normalizer
                                         (unified job schema)
                                                     │
                                           Dedup (content_hash)
                                                     │
                                         AI Matchmaker (OpenRouter)
                                         score 0–100 + reasoning
                                                     │
                                       score ≥ MATCH_THRESHOLD ?
                                   no ────────────────┤
                              SQLite · matches         │
                           (status=low_match)          yes
                           visible in Near Misses      │
                                                  CV Selector
                                            (picks best variant)
                                                     │
                                             SQLite · matches
                                          (status=new)
                                                     │
                                           Telegram Bot notification
                                           "Match at [Co] · [XX]%"
                                           + 2-line summary + PWA link
                                                     │
                                              React PWA (mobile)
                                           Card + Bottom Sheet UI
                                           Job · Reasoning · CV
                                                     │
                                         Apply → ATS deep link
                                      (pre-filled: name/email/LinkedIn/portfolio)
                                                     │
                                      "Did you submit?" confirmation
                                                     │
                                        Tracker → status: Applied
```

---

## 5. Configuration

All tuneable values live in a single `.env` file. No code changes needed to adjust behaviour.

```env
# LLM
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=anthropic/claude-opus-4.5   # swap to any OpenRouter model

# Pipeline
MATCH_THRESHOLD=65          # 0–100 — jobs below this score are saved but not notified
SCAN_INTERVAL_HOURS=4       # how often APScheduler runs the full scan

# Telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# App
PWA_ACCESS_TOKEN=...        # static bearer token — set once, used in every PWA request header
PWA_BASE_URL=http://<vm-ip>:8000
                             # Single-user tool: FastAPI checks Authorization: Bearer <token>
                             # on all API routes. No login UI needed.
```

---

## 6. Data Models

### 6.1 `companies` — the watchlist

```sql
id              INTEGER PRIMARY KEY
name            TEXT NOT NULL
website         TEXT
ats_type        TEXT  -- greenhouse | lever | workday | custom | linkedin
ats_slug        TEXT  -- e.g. "vercel" → boards.greenhouse.io/vercel/jobs
linkedin_url    TEXT
career_page_url TEXT  -- fallback URL for Scrapling
active          BOOLEAN DEFAULT TRUE
added_at        DATETIME
```

### 6.2 `jobs` — every job ever seen

```sql
id              INTEGER PRIMARY KEY
company_id      INTEGER REFERENCES companies(id)
title           TEXT NOT NULL
url             TEXT NOT NULL
description_raw TEXT
location        TEXT
remote          BOOLEAN
source          TEXT  -- ats_api | scrapling | linkedin
content_hash    TEXT UNIQUE  -- dedup key: hash(company_id + title + url)
first_seen_at   DATETIME
```

### 6.3 `matches` — jobs that entered the pipeline

```sql
id              INTEGER PRIMARY KEY
job_id          INTEGER REFERENCES jobs(id)
score           INTEGER  -- 0–100
reasoning       TEXT     -- 2–3 sentence AI summary
cv_variant_id   INTEGER REFERENCES cv_variants(id)
status          TEXT  -- low_match | new | reviewed | skipped | applied | rejected | no_response | interview | offer
                      -- low_match: scored but below MATCH_THRESHOLD, no Telegram sent
matched_at      DATETIME
reviewed_at     DATETIME
```

### 6.4 `cv_variants` — pre-built CV files

```sql
id              INTEGER PRIMARY KEY
name            TEXT  -- e.g. "frontend-focused"
file_path       TEXT  -- path to PDF on VM
focus_tags      TEXT  -- JSON array: ["react","ui","design-systems"]
is_active       BOOLEAN DEFAULT TRUE
```

### 6.5 `applications` — created on Apply tap

```sql
id              INTEGER PRIMARY KEY
match_id        INTEGER REFERENCES matches(id)
cv_variant_id   INTEGER REFERENCES cv_variants(id)
ats_url         TEXT     -- the pre-filled ATS deep link
applied_at      DATETIME -- set when user taps Apply (opens ATS form)
confirmed_at    DATETIME -- set when user confirms submission
notes           TEXT
outcome_status  TEXT  -- pending | interview | offer | rejected
last_status_update DATETIME
```

---

## 7. CV Variant Strategy

> **Note:** This section is a placeholder structure. The actual variants, their focus tags, and the selector logic will be defined once the real CVs are written. The implementation should treat variant definitions as pure data (loaded from the `cv_variants` table) so no code changes are needed when variants are updated.

Three pre-built variants (initial draft — to be refined). The CV Selector picks the best match based on job description keywords. Tie-break defaults to `fullstack-automation`.

| Variant | Focus | Target roles |
|---|---|---|
| `frontend-focused` | React, UI/UX, design systems, portfolio | Product companies, agencies wanting pixel-perfect work |
| `fullstack-automation` | End-to-end builds, Node.js, deployment, Electron, automation | Startups wanting a "build it all" engineer |
| `ai-builder` | LLM pipelines, AutoPot, Minerva, Claude/OpenRouter integrations | AI-native companies, automation/tooling roles |

If the best variant is ambiguous (score difference < 10 points), both are surfaced in the PWA and the user picks before tapping Apply.

---

## 8. Primary User Flows

### Flow 1 — Automated Scan & Match (background)
1. APScheduler triggers on interval
2. Each active company is fetched via the appropriate fetcher
3. New jobs (not in `content_hash`) are normalized and saved
4. Each new job is scored by OpenRouter
5. Score ≥ `MATCH_THRESHOLD` → CV Selector runs → match saved → Telegram fires

### Flow 2 — Review & Apply (on phone)
1. Telegram notification arrives: "Match at [Company] · [XX]%"
2. User taps link → PWA opens to job card
3. Card shows: company, title, score, location, 2-line AI reasoning
4. User swipes up → bottom sheet reveals full tailored CV (PDF viewer or rendered HTML)
5. User taps **Apply →** → ATS form opens in browser, pre-filled with name / email / LinkedIn / portfolio URL
6. User attaches CV PDF (accessible via share sheet), completes and submits the form
7. User returns to PWA → "Did you submit?" prompt → taps Yes → match status → `applied`, application record created

### Flow 3 — Skip
1. From the job card, user taps **✕ Skip**
2. Match status → `skipped`, no application record created
3. Next pending match shown (if any)

### Flow 4 — Watchlist Management (occasional)
1. PWA → Settings → Companies → Add
2. Enter company name + career page URL
3. System detects ATS type (checks known ATS URL patterns)
4. Company added to watchlist, included in next scheduled scan

### Flow 5 — Tracker Review (weekly)
1. PWA → Tracker tab
2. Pipeline view: New · Reviewed · Applied · Interview · No Response · Rejected · Offer
3. Tap any row → full detail: job description, AI reasoning, CV variant used, notes, timeline

---

## 9. Edge Cases

| Scenario | Handling |
|---|---|
| Same job reposted | `content_hash` dedup — silently ignored |
| Company changes ATS platform | Manual update of `ats_type` + `ats_slug` in Settings |
| Scrapling blocked by LinkedIn | Graceful failure — skip company for this cycle, log warning, retry next cycle |
| Score just below threshold (within 10 points) | Saved as "near miss" — visible in a separate Near Misses view in PWA |
| Both CV variants score similarly | Both surfaced in PWA for user to choose before applying |
| User taps Apply but never confirms | Status stays `applied` (unconfirmed) — reminder badge in Tracker after 48h |
| OpenRouter API timeout / failure | Job saved, match queued for retry on next scheduler tick. Max 3 retries. |
| VM restart | systemd unit auto-restarts FastAPI + APScheduler. SQLite file persists on disk. |
| User wants to manually trigger a scan | PWA → Settings → "Scan Now" button → POST /trigger-scan |
| Duplicate notification (bot sends twice) | Telegram message ID stored — no duplicate sends for same match_id |

---

## 10. API Endpoints (FastAPI)

```
GET    /matches                    All pending matches (status=new)
GET    /matches/{id}               Single match detail
POST   /matches/{id}/skip          Mark as skipped
POST   /matches/{id}/applied       Mark as applied (creates application record)

GET    /tracker                    All applications with status breakdown
PATCH  /applications/{id}          Update outcome status / notes

GET    /companies                  Watchlist
POST   /companies                  Add company
PATCH  /companies/{id}             Update (toggle active, fix ATS slug)
DELETE /companies/{id}             Remove from watchlist

GET    /cv-variants                List available CV variants
POST   /cv-variants                Upload new variant
DELETE /cv-variants/{id}           Deactivate variant

POST   /trigger-scan               Manual scan trigger (async background task)
GET    /scan-status                Last scan time, next scan time, job count delta
```

---

## 11. PWA Screens

| Screen | Purpose |
|---|---|
| **Match Card** | Job card (company, title, score, 2-line reasoning) + Apply/Skip actions |
| **Bottom Sheet** | Full CV view (PDF embed or rendered HTML) |
| **Tracker** | Pipeline board with status columns |
| **Application Detail** | Full detail for one application — job, CV used, timeline, notes |
| **Companies** | Watchlist management |
| **Settings** | MATCH_THRESHOLD display, scan interval, manual scan trigger, CV variant upload |

---

## 12. What This System Does NOT Do

- It does not auto-apply to any job
- It does not generate CVs from scratch per role (it selects from pre-built variants)
- It does not monitor Israeli job boards (AllJobs, JobMaster, Drushim) — out of scope
- It does not integrate with openclaw or share its Telegram bot, scheduler, or database
- It does not parse or fill ATS form fields automatically (pre-fill is limited to standard URL parameters supported by the ATS)
