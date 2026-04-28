# Company Edit Sheet & Fetch Test — Design Spec

**Date:** 2026-04-28  
**Status:** Approved

## Problem

56 companies returned zero jobs during scans. Root cause: wrong slugs or broken career page URLs with no way to inspect or fix them from the UI. There is also no feedback loop telling the user which company links are working.

## Feature Summary

A bottom sheet per company row that lets the user edit all fields and run a connectivity test — confirming the scraper can reach the URL and find at least one job listing. Test results are persisted per company and automatically re-run monthly.

---

## 1. Company List (UI changes)

**Trigger:** Tap anywhere on the company row body opens the edit sheet. The existing Active and Delete buttons call `stopPropagation` so they remain independent.

**Compact test badge on each row:**

- Colored dot (green = last test passed, red = last test failed, grey = never tested)
- Small pill `🕐 2d` showing time since last test (red background if failed)
- "— never" pill if the company has never been tested
- No additional text — the dot + pill is the entire indicator

---

## 2. Edit Bottom Sheet

Uses the existing `BottomSheet` component. Fields shown:

| Field | Always shown | Conditional |
|---|---|---|
| Company name | ✅ | |
| ATS type tabs | ✅ | |
| Slug | | greenhouse, lever only |
| Career page URL | | workday, custom only |
| LinkedIn company URL | | linkedin only |

**ATS type tabs** are the same pill-style selector as the Add form. Switching ATS type shows/hides the relevant field (slug vs URL).

**Last test result block** appears below the fields:

- Pass: green banner — "Pass — N jobs found · Tested X days ago · next check in Nd" (Nd = 30 − days since last_test_at, calculated frontend-side)
- Fail: red banner — "Fail — 0 jobs found · Tested X days ago · check the slug/URL"
- Never tested: grey banner — "Never tested · Add the URL and hit Test"

**Action buttons:**
- **Save + Test** — saves field edits via `PATCH /companies/{id}`, then automatically triggers `POST /companies/{id}/test`
- **Test now** — runs test without saving

---

## 3. Test Endpoint — `POST /companies/{id}/test`

**Approach:** Thin endpoint that calls the existing fetcher functions directly. No DB writes beyond persisting the result. No matchmaking, no scoring.

**Logic:**
1. Load company from DB
2. Call the appropriate fetcher based on `ats_type`:
   - `greenhouse` → `fetch_greenhouse_jobs(slug)`
   - `lever` → `fetch_lever_jobs(slug)`
   - `workday` / `custom` → `fetch_career_page(career_page_url, domain)`
   - `linkedin` → `fetch_linkedin_jobs(company_name)`
3. **Pass** if `len(jobs) >= 1`, **Fail** otherwise
4. Persist result to `Company`: `last_test_at`, `last_test_passed`, `last_test_jobs_found`
5. Return `{ passed: bool, jobs_found: int, tested_at: datetime }`

---

## 4. DB Schema Changes (no Alembic)

Three columns added to the `companies` table manually:

```sql
ALTER TABLE companies ADD COLUMN last_test_at TEXT DEFAULT NULL;
ALTER TABLE companies ADD COLUMN last_test_passed INTEGER DEFAULT NULL;
ALTER TABLE companies ADD COLUMN last_test_jobs_found INTEGER DEFAULT NULL;
```

Three corresponding optional fields added to the `Company` SQLModel:

```python
last_test_at: Optional[datetime] = Field(default=None)
last_test_passed: Optional[bool] = Field(default=None)
last_test_jobs_found: Optional[int] = Field(default=None)
```

---

## 5. Monthly Auto-Retest (APScheduler)

A new APScheduler job runs once per month. For every **active** company:
1. Call `POST /companies/{id}/test` logic directly (not via HTTP)
2. Persist result

Scheduler job ID: `"company_health_check"`, interval: 30 days.  
Added alongside the existing `job_scan` job in `backend/app/scheduler.py`.

---

## 6. Frontend — API Client & Types

**New `Company` type fields:**
```ts
last_test_at: string | null
last_test_passed: boolean | null
last_test_jobs_found: number | null
```

**New API method:**
```ts
testCompany(id: number): Promise<{ passed: boolean; jobs_found: number; tested_at: string }>
```

---

## 7. Frontend — Companies Page

- Each row becomes tappable (onClick on the row div, with `stopPropagation` on action buttons)
- `selectedCompany` state tracks which company's sheet is open
- `CompanyEditSheet` component (new) renders inside `BottomSheet`:
  - Controlled form state initialized from the selected company
  - ATS type tabs switch the visible URL/slug field
  - "Save + Test" calls `updateCompany` then `testCompany`, updates local state on both responses
  - "Test now" calls `testCompany` only
  - Loading spinner replaces test result block while test is in flight

---

## 8. Out of Scope

- Showing sample job titles in the test result (pass/fail count is sufficient)
- Testing inactive companies in the monthly recheck (active only)
- Any changes to the Add Company form
- Alembic migrations (manual SQL ALTER per CLAUDE.md convention)
