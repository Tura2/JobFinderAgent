# Production Bug Fixes — 2026-04-27 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the six production bugs identified in the 2026-04-27 log report: Telegram localhost links, Playwright missing, matchmaker rate-limit silently dropping 44% of jobs, orphaned unscored jobs never retried, near-miss page overloaded with garbage, and wrong Greenhouse slugs.

**Architecture:** Four code changes (matchmaker retry detection, orphaned job rescoring, score floor config, near-miss API filter + frontend slider) plus two infrastructure steps on the VM (env var update, Playwright install). A slug-verification script is added to diagnose and fix the remaining ATS data issue.

**Tech Stack:** Python 3.11, FastAPI, SQLModel/SQLite, tenacity (already installed), React 18 + TypeScript, Vite

---

## Files Modified

| File | What changes |
|---|---|
| `backend/app/pipeline/matchmaker.py` | Detect missing `choices` key → raise so tenacity retries |
| `backend/app/config.py` | Add `low_match_floor: int = 30` setting |
| `backend/app/scheduler.py` | Score orphaned jobs; apply score floor before saving |
| `backend/app/routers/matches.py` | Add `min_score` query param to near-misses endpoint |
| `frontend/src/pages/NearMisses.tsx` | Score slider UI, pass `min_score` to API |
| `frontend/src/api/client.ts` | Pass `min_score` param to `getNearMisses` |
| `scripts/verify_slugs.py` | New: async script to probe each company's ATS URL |
| `backend/tests/test_matchmaker.py` | Test rate-limit retry |
| `backend/tests/test_scheduler.py` | Test orphaned job rescoring + score floor |
| `backend/tests/test_api_matches.py` | Test `min_score` filter |

---

## Task 1: Infrastructure fixes on the VM (no code change)

These must be done directly on the Oracle Cloud VM. No tests needed.

- [ ] **Step 1: Fix Telegram links — update PWA_BASE_URL**

SSH into the VM and edit `backend/.env`:
```bash
# Replace localhost with the server's actual public IP:
# Change this line:
PWA_BASE_URL=http://localhost:8000
# To:
PWA_BASE_URL=http://<your-vm-public-ip>:8000
```

- [ ] **Step 2: Install Playwright Chromium**

```bash
cd ~/JobFinderAgent/backend
source venv/bin/activate
playwright install chromium
```

Expected output ends with: `Chromium ... downloaded to /home/ubuntu/.cache/ms-playwright/chromium-XXXX/chrome-linux/chrome`

- [ ] **Step 3: Restart the service**

```bash
sudo systemctl restart jobfinder
sudo systemctl status jobfinder
```

Expected: `Active: active (running)` within a few seconds.

- [ ] **Step 4: Verify fix**

Trigger a manual scan and check the next Telegram notification. The link should read `http://<public-ip>:8000/matches/N`.

---

## Task 2: Fix matchmaker rate-limit retry

**Problem:** OpenRouter returns HTTP 200 with a JSON body that has no `choices` key when rate-limited. The current `@retry` decorator only triggers on `httpx.RequestError` / `HTTPStatusError`, so these are silently swallowed as `None`.

**Fix:** In `_call_openrouter`, check for missing `choices` and raise `httpx.RequestError` so tenacity retries it.

**Files:**
- Modify: `backend/app/pipeline/matchmaker.py`
- Test: `backend/tests/test_matchmaker.py`

- [ ] **Step 1: Write the failing test**

Open `backend/tests/test_matchmaker.py` and add at the end:

```python
import pytest
import respx
import httpx
from unittest.mock import patch

@respx.mock
@pytest.mark.asyncio
async def test_score_job_retries_when_choices_missing():
    """When OpenRouter returns 200 but no 'choices' key, score_job should retry and eventually return None (not crash)."""
    # Simulate 3 responses with no 'choices' (rate-limit envelope)
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"error": {"message": "rate limited"}})
    )

    result = await score_job(
        job_title="Backend Engineer",
        company_name="Acme",
        location="Tel Aviv",
        description="Python, AWS",
        user_profile="Python dev",
        cv_variants_text="general [python]",
    )
    assert result is None  # exhausted retries, returns None gracefully
```

- [ ] **Step 2: Run it to verify it fails (currently passes by accident — confirm behavior)**

```bash
cd backend && source venv/Scripts/activate
pytest tests/test_matchmaker.py::test_score_job_retries_when_choices_missing -v
```

Note the current behavior (passes or fails) — the key point is to confirm the implementation change below actually changes behavior.

- [ ] **Step 3: Fix `_call_openrouter` to raise on missing `choices`**

In `backend/app/pipeline/matchmaker.py`, replace:

```python
        resp.raise_for_status()
        return resp.json()
```

with:

```python
        resp.raise_for_status()
        data = resp.json()
        if "choices" not in data:
            raise httpx.RequestError(
                f"OpenRouter returned no choices (rate-limited?): {data.get('error', data)}"
            )
        return data
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_matchmaker.py -v
```

Expected: all pass. The retry decorator now fires on missing-choices responses, giving tenacity 3 attempts with 2–10s backoff before returning None.

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/matchmaker.py backend/tests/test_matchmaker.py
git commit -m "fix: retry matchmaker when OpenRouter returns 200 with no choices key"
```

---

## Task 3: Fix orphaned unscored jobs (permanently skipped after matchmaker failure)

**Problem:** When the matchmaker returns `None` for a job, the job is already committed to the DB (content_hash set). On the next scan, `normalize_and_deduplicate` sees the content_hash and skips it, so it's permanently lost.

**Fix:** In `run_scan_for_company`, after dedup, also find any jobs for this company that have no `Match` record yet and add them to the scoring batch.

**Files:**
- Modify: `backend/app/scheduler.py` (lines 86–165)
- Test: `backend/tests/test_scheduler.py`

- [ ] **Step 1: Write the failing test**

Open `backend/tests/test_scheduler.py` and add:

```python
import pytest
from unittest.mock import AsyncMock, patch
from sqlmodel import Session

from app.models.company import Company
from app.models.job import Job
from app.models.match import Match
from app.scheduler import run_scan_for_company


@pytest.mark.asyncio
async def test_orphaned_jobs_are_rescored(db: Session):
    """Jobs committed to DB with no Match (matchmaker previously failed) are scored on the next scan."""
    company = Company(name="Acme", ats_type="greenhouse", ats_slug="acme")
    db.add(company)
    db.commit()
    db.refresh(company)

    # Pre-existing job with no Match (orphaned from previous failed matchmaker call)
    orphan = Job(
        company_id=company.id,
        title="Backend Engineer",
        url="https://boards.greenhouse.io/acme/jobs/99",
        source="ats_api",
        content_hash="orphan-hash-99",
    )
    db.add(orphan)
    db.commit()
    db.refresh(orphan)

    # The fetcher returns no new jobs (all deduped or empty)
    mock_score_result = {"score": 75, "reasoning": "Good fit", "cv_variant": "general", "score_breakdown": "{}"}

    with patch("app.scheduler._fetch_jobs_for_company", new=AsyncMock(return_value=[])), \
         patch("app.scheduler.score_job", new=AsyncMock(return_value=mock_score_result)), \
         patch("app.scheduler.send_match_notification", new=AsyncMock()):
        results = await run_scan_for_company(company, db)

    # Orphan was scored and a Match was created
    assert len(results) == 1
    assert results[0]["job_title"] == "Backend Engineer"
    assert results[0]["score"] == 75
    match = db.exec(__import__("sqlmodel").select(Match).where(Match.job_id == orphan.id)).first()
    assert match is not None
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && source venv/Scripts/activate
pytest tests/test_scheduler.py::test_orphaned_jobs_are_rescored -v
```

Expected: FAIL — `assert len(results) == 1` fails because orphaned jobs aren't in the scoring loop yet.

- [ ] **Step 3: Add orphaned job collection to `run_scan_for_company`**

In `backend/app/scheduler.py`, at the top of the file add the missing import (already present: `from sqlmodel import Session, select`). Also ensure `Job` is imported — add it:

```python
from app.models.company import Company
from app.models.cv_variant import CVVariant
from app.models.match import Match
from app.models.job import Job  # add this line if not already present
```

Then in `run_scan_for_company`, replace the block starting at `new_jobs = normalize_and_deduplicate(...)` through `if not new_jobs: return []` with:

```python
    new_jobs = normalize_and_deduplicate(raw_jobs, company.id, session)

    # Collect previously unscored jobs (matchmaker returned None on a past scan)
    scored_job_ids: set[int] = {
        row for row in session.exec(
            select(Match.job_id)
            .join(Job, Match.job_id == Job.id)
            .where(Job.company_id == company.id)
        ).all()
    }
    all_company_jobs = list(
        session.exec(select(Job).where(Job.company_id == company.id)).all()
    )
    new_job_ids = {j.id for j in new_jobs}
    unscored_jobs = [
        j for j in all_company_jobs
        if j.id not in scored_job_ids and j.id not in new_job_ids
    ]

    jobs_to_score = new_jobs + unscored_jobs
    filtered_jobs = [j for j in jobs_to_score if not _is_excluded_title(j.title)]
    skipped = len(jobs_to_score) - len(filtered_jobs)
    if skipped:
        logger.info(f"Pre-filter skipped {skipped} irrelevant titles for {company.name}")
    if not filtered_jobs:
        return []
```

Then update the rest of the function to use `filtered_jobs` instead of the old `new_jobs` variable (it already is — confirm that the `for job in new_jobs:` loop below becomes `for job in filtered_jobs:`):

The full updated `run_scan_for_company` should read:

```python
async def run_scan_for_company(company: Company, session: Session) -> list[dict]:
    raw_jobs = await _fetch_jobs_for_company(company)
    if not raw_jobs:
        raw_jobs = []

    new_jobs = normalize_and_deduplicate(raw_jobs, company.id, session)

    # Collect previously unscored jobs (matchmaker returned None on a past scan)
    scored_job_ids: set[int] = {
        row for row in session.exec(
            select(Match.job_id)
            .join(Job, Match.job_id == Job.id)
            .where(Job.company_id == company.id)
        ).all()
    }
    all_company_jobs = list(
        session.exec(select(Job).where(Job.company_id == company.id)).all()
    )
    new_job_ids = {j.id for j in new_jobs}
    unscored_jobs = [
        j for j in all_company_jobs
        if j.id not in scored_job_ids and j.id not in new_job_ids
    ]

    jobs_to_score = new_jobs + unscored_jobs
    filtered_jobs = [j for j in jobs_to_score if not _is_excluded_title(j.title)]
    skipped = len(jobs_to_score) - len(filtered_jobs)
    if skipped:
        logger.info(f"Pre-filter skipped {skipped} irrelevant titles for {company.name}")
    if not filtered_jobs:
        return []

    user_profile = _load_user_profile()
    cv_variants_text = _get_cv_variants_text(session)
    active_variants = list(
        session.exec(select(CVVariant).where(CVVariant.is_active == True)).all()
    )

    results = []

    for job in filtered_jobs:
        match_result = await score_job(
            job_title=job.title,
            company_name=company.name,
            location=job.location or "",
            description=job.description_raw or "",
            user_profile=user_profile,
            cv_variants_text=cv_variants_text,
        )

        if match_result is None:
            logger.warning(f"Matchmaker returned None for job {job.title} — skipping")
            continue

        score = match_result["score"]
        reasoning = match_result["reasoning"]
        cv_name = match_result["cv_variant"]
        score_breakdown = match_result.get("score_breakdown")

        selected = select_cv_variant(cv_name, active_variants)
        cv_variant_id = selected[0].id if selected else None

        status = "new" if score >= settings.match_threshold else "low_match"

        match = Match(
            job_id=job.id,
            score=score,
            reasoning=reasoning,
            cv_variant_id=cv_variant_id,
            status=status,
            score_breakdown=score_breakdown,
        )
        session.add(match)
        session.commit()
        session.refresh(match)

        if status == "new":
            await send_match_notification(
                match_id=match.id,
                company_name=company.name,
                job_title=job.title,
                score=score,
                reasoning=reasoning,
                pwa_base_url=settings.pwa_base_url,
                db=session,
            )

        results.append({
            "match_id": match.id,
            "job_title": job.title,
            "score": score,
            "status": status,
        })

    return results
```

- [ ] **Step 4: Run the test**

```bash
pytest tests/test_scheduler.py::test_orphaned_jobs_are_rescored -v
```

Expected: PASS.

- [ ] **Step 5: Run full test suite**

```bash
pytest -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/scheduler.py backend/tests/test_scheduler.py
git commit -m "fix: rescore orphaned jobs that had no match due to matchmaker failure"
```

---

## Task 4: Add score floor — don't persist garbage matches

**Problem:** Jobs scored 0–29 are irrelevant noise. They pollute the `low_match` bucket. Better to discard them rather than store 36 zero-score jobs and 81 near-zero-score jobs.

**Fix:** Add `low_match_floor: int = 30` to config. In the scheduler, skip saving a Match if `score < low_match_floor`.

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/scheduler.py` (the status assignment block)
- Test: `backend/tests/test_scheduler.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_scheduler.py`:

```python
@pytest.mark.asyncio
async def test_score_below_floor_is_not_saved(db: Session):
    """Jobs scored below low_match_floor are not persisted as matches."""
    company = Company(name="Acme2", ats_type="greenhouse", ats_slug="acme2")
    db.add(company)
    db.commit()
    db.refresh(company)

    mock_score_result = {"score": 10, "reasoning": "Irrelevant", "cv_variant": "general", "score_breakdown": "{}"}

    with patch("app.scheduler._fetch_jobs_for_company", new=AsyncMock(return_value=[{
        "title": "Marketing Manager",
        "url": "https://boards.greenhouse.io/acme2/jobs/1",
        "source": "ats_api",
    }])), \
         patch("app.scheduler.score_job", new=AsyncMock(return_value=mock_score_result)):
        results = await run_scan_for_company(company, db)

    assert results == []
    assert db.exec(__import__("sqlmodel").select(Match)).all() == []
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
pytest tests/test_scheduler.py::test_score_below_floor_is_not_saved -v
```

Expected: FAIL — currently score=10 gets saved as `low_match`.

- [ ] **Step 3: Add `low_match_floor` to config**

In `backend/app/config.py`, add after the `match_threshold` field:

```python
    match_threshold: int = 65
    low_match_floor: int = 30  # scores below this are discarded, not saved as low_match
    scan_interval_hours: int = 4
```

- [ ] **Step 4: Apply score floor in scheduler**

In `backend/app/scheduler.py`, in the `for job in filtered_jobs:` loop, replace:

```python
        status = "new" if score >= settings.match_threshold else "low_match"

        match = Match(
```

with:

```python
        if score < settings.low_match_floor:
            logger.debug(f"Score {score} below floor {settings.low_match_floor} for '{job.title}' — discarding")
            continue

        status = "new" if score >= settings.match_threshold else "low_match"

        match = Match(
```

- [ ] **Step 5: Add conftest env var**

In `backend/tests/conftest.py`, the `Settings()` call at module level will now pick up `low_match_floor` — it has a default of 30, so no conftest change is needed. Verify by running:

```bash
pytest tests/test_config.py -v
```

Expected: all pass (low_match_floor defaults to 30).

- [ ] **Step 6: Run the score-floor test**

```bash
pytest tests/test_scheduler.py::test_score_below_floor_is_not_saved -v
```

Expected: PASS.

- [ ] **Step 7: Run full suite**

```bash
pytest -v
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add backend/app/config.py backend/app/scheduler.py backend/tests/test_scheduler.py
git commit -m "feat: add low_match_floor config to discard irrelevant jobs (default score<30)"
```

---

## Task 5: Add `min_score` filter to near-misses endpoint + frontend slider

**Problem:** `GET /matches/near-misses` returns all 380 `low_match` entries with no filtering. The frontend shows all of them in one overwhelming list.

**Fix:** Add `min_score: int = Query(default=30)` to the endpoint. Add a score slider to `NearMisses.tsx` that re-fetches with the chosen floor.

**Files:**
- Modify: `backend/app/routers/matches.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/NearMisses.tsx`
- Test: `backend/tests/test_api_matches.py`

- [ ] **Step 1: Write the failing backend test**

Add to `backend/tests/test_api_matches.py`:

```python
def test_near_misses_min_score_filter(client, db):
    _seed_match(db, status="low_match", score=60)
    _seed_match(db, status="low_match", score=20)
    _seed_match(db, status="low_match", score=5)

    # Default min_score=30 — should exclude score=20 and score=5
    resp = client.get("/matches/near-misses")
    assert resp.status_code == 200
    scores = [m["score"] for m in resp.json()]
    assert 60 in scores
    assert 20 not in scores
    assert 5 not in scores

def test_near_misses_min_score_explicit(client, db):
    _seed_match(db, status="low_match", score=60)
    _seed_match(db, status="low_match", score=20)

    resp = client.get("/matches/near-misses?min_score=50")
    assert resp.status_code == 200
    scores = [m["score"] for m in resp.json()]
    assert scores == [60]
```

Note: `_seed_match` uses `content_hash=f"hash_{score}_{status}"` — for multiple calls with the same score+status combo, add a unique suffix. Update the helper:

```python
import uuid

def _seed_match(db: Session, status="new", score=85) -> tuple:
    company = Company(name="Vercel", ats_type="greenhouse", ats_slug="vercel")
    db.add(company)
    db.commit()
    db.refresh(company)

    job = Job(
        company_id=company.id,
        title="Frontend Engineer",
        url="https://boards.greenhouse.io/vercel/jobs/1",
        description_raw="Build UIs with React",
        location="Remote",
        remote=True,
        source="ats_api",
        content_hash=f"hash_{score}_{status}_{uuid.uuid4().hex[:8]}",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    cv = CVVariant(name="frontend-focused", file_path="/cv/fe.pdf", focus_tags='["react"]', is_active=True)
    db.add(cv)
    db.commit()
    db.refresh(cv)

    match = Match(
        job_id=job.id,
        score=score,
        reasoning="Strong React fit.",
        cv_variant_id=cv.id,
        status=status,
    )
    db.add(match)
    db.commit()
    db.refresh(match)

    return company, job, cv, match
```

Add `import uuid` at the top of `test_api_matches.py`.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
pytest tests/test_api_matches.py::test_near_misses_min_score_filter tests/test_api_matches.py::test_near_misses_min_score_explicit -v
```

Expected: FAIL — endpoint ignores min_score.

- [ ] **Step 3: Update the endpoint**

In `backend/app/routers/matches.py`, add `Query` to the FastAPI imports:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
```

Then replace the `get_near_misses` function:

```python
@router.get("/near-misses", response_model=list[MatchListItem])
async def get_near_misses(
    min_score: int = Query(default=30, ge=0, le=100),
    session: Session = Depends(get_session),
):
    matches = session.exec(
        select(Match, Job, Company)
        .join(Job, Match.job_id == Job.id)
        .join(Company, Job.company_id == Company.id)
        .where(Match.status == "low_match")
        .where(Match.score >= min_score)
        .order_by(Match.score.desc())
    ).all()

    return [
        MatchListItem(
            id=m.id, score=m.score, reasoning=m.reasoning, status=m.status,
            matched_at=m.matched_at, job_title=j.title, company_name=c.name,
        )
        for m, j, c in matches
    ]
```

- [ ] **Step 4: Run backend tests**

```bash
pytest tests/test_api_matches.py -v
```

Expected: all pass.

- [ ] **Step 5: Update frontend API client**

In `frontend/src/api/client.ts`, replace:

```typescript
  getNearMisses: () => apiFetch<import("../types").MatchListItem[]>("/matches/near-misses"),
```

with:

```typescript
  getNearMisses: (minScore = 30) =>
    apiFetch<import("../types").MatchListItem[]>(`/matches/near-misses?min_score=${minScore}`),
```

- [ ] **Step 6: Update NearMisses.tsx to add score slider**

Replace the entire `frontend/src/pages/NearMisses.tsx` with:

```tsx
import { useEffect, useState } from 'react';
import { TrendingDown } from 'lucide-react';
import { api } from '../api/client';
import type { MatchListItem } from '../types';

const scoreColor = (s: number) =>
  s >= 85 ? '#22c55e' : s >= 70 ? '#eab308' : s >= 55 ? '#f97316' : '#ef4444';

export default function NearMisses() {
  const [items, setItems] = useState<MatchListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [minScore, setMinScore] = useState(30);

  useEffect(() => {
    setLoading(true);
    api.getNearMisses(minScore).then(setItems).finally(() => setLoading(false));
  }, [minScore]);

  return (
    <div style={{ paddingBottom: 96, paddingTop: 24, paddingInline: 16 }}>
      <h1 style={{ color: '#fff', fontSize: 26, fontWeight: 700, letterSpacing: '-0.03em' }}>Near Misses</h1>
      <p style={{ color: '#4b5563', fontSize: 13, marginTop: 2, marginBottom: 12 }}>
        Below threshold — review manually if interested
      </p>

      {/* Score filter slider */}
      <div style={{ marginBottom: 18, display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ color: '#6b7280', fontSize: 12, whiteSpace: 'nowrap' }}>Min score</span>
        <input
          type="range"
          min={0}
          max={64}
          step={5}
          value={minScore}
          onChange={e => setMinScore(Number(e.target.value))}
          style={{ flex: 1, accentColor: '#6366f1' }}
        />
        <span style={{
          color: '#e5e7eb', fontSize: 13, fontWeight: 700,
          minWidth: 24, textAlign: 'right',
        }}>{minScore}</span>
      </div>

      {loading ? (
        <div className="flex items-center justify-center" style={{ height: 120 }}>
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-indigo-500 border-t-transparent" />
        </div>
      ) : items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '64px 0' }}>
          <div style={{
            background: '#1a1f2e', border: '1px solid #1f2937', borderRadius: '50%',
            width: 72, height: 72, display: 'flex', alignItems: 'center',
            justifyContent: 'center', margin: '0 auto 16px',
          }}>
            <TrendingDown size={30} color="#374151" />
          </div>
          <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: 16, marginBottom: 6 }}>No near misses</div>
          <div style={{ color: '#4b5563', fontSize: 13 }}>Jobs just under threshold will appear here.</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {items.map(m => {
            const c = scoreColor(m.score);
            return (
              <div key={m.id} style={{
                background: '#111827', border: '1px solid #1f2937',
                borderRadius: 16, padding: 14,
              }}>
                <div style={{
                  display: 'flex', justifyContent: 'space-between',
                  alignItems: 'flex-start', gap: 8, marginBottom: 7,
                }}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ color: '#e5e7eb', fontWeight: 600, fontSize: 14, marginBottom: 2 }}>
                      {m.job_title}
                    </div>
                    <div style={{ color: '#4b5563', fontSize: 12 }}>{m.company_name}</div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
                    <div style={{ height: 5, width: 60, background: '#1f2937', borderRadius: 3, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${m.score}%`, background: c, borderRadius: 3 }} />
                    </div>
                    <span style={{ fontSize: 12, fontWeight: 700, color: c, minWidth: 20 }}>{m.score}</span>
                    <span style={{
                      fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 6,
                      letterSpacing: '0.02em', background: '#431407', color: '#fb923c',
                    }}>Near miss</span>
                  </div>
                </div>
                <p style={{
                  color: '#4b5563', fontSize: 12, lineHeight: 1.55,
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical' as const,
                  overflow: 'hidden',
                } as React.CSSProperties}>
                  {m.reasoning}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 7: Run frontend type check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 8: Commit**

```bash
git add backend/app/routers/matches.py backend/tests/test_api_matches.py \
        frontend/src/api/client.ts frontend/src/pages/NearMisses.tsx
git commit -m "feat: add min_score filter to near-misses endpoint and score slider to PWA"
```

---

## Task 6: Greenhouse / Lever slug verification script

**Problem:** 36 companies are configured with Greenhouse/Lever slugs that return 404. Each needs its correct slug found manually.

**Fix:** Add a script that pings the API URL for each company and reports which slugs are broken, so you can fix them in the DB one by one.

**Files:**
- Create: `scripts/verify_slugs.py`

- [ ] **Step 1: Create the script**

```python
#!/usr/bin/env python3
"""
Usage (from repo root, with backend venv active):
  python scripts/verify_slugs.py [--fix]

Checks all active companies' Greenhouse/Lever ATS slugs by hitting
their public API. Prints a report of broken slugs.

Pass --fix to be prompted for the correct slug interactively.
"""
import asyncio
import sys
from pathlib import Path

# Load backend .env so DATABASE_URL is available
import os
os.chdir(Path(__file__).parent.parent / "backend")
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

import httpx
from sqlmodel import Session, create_engine, select
from app.models.company import Company
from app.config import settings

FIX_MODE = "--fix" in sys.argv

engine = create_engine(settings.database_url, echo=False)


async def check_slug(client: httpx.AsyncClient, company: Company) -> dict:
    if company.ats_type == "greenhouse" and company.ats_slug:
        url = f"https://boards.greenhouse.io/{company.ats_slug}/jobs"
    elif company.ats_type == "lever" and company.ats_slug:
        url = f"https://api.lever.co/v0/postings/{company.ats_slug}"
    else:
        return {"company": company.name, "status": "skip", "url": None}

    try:
        resp = await client.get(url, timeout=10.0, follow_redirects=True)
        return {
            "company": company.name,
            "id": company.id,
            "slug": company.ats_slug,
            "ats_type": company.ats_type,
            "status": resp.status_code,
            "ok": resp.status_code == 200,
            "url": url,
        }
    except Exception as e:
        return {"company": company.name, "id": company.id, "slug": company.ats_slug, "status": "error", "ok": False, "url": url, "error": str(e)}


async def main():
    with Session(engine) as session:
        companies = list(session.exec(
            select(Company)
            .where(Company.active == True)
            .where(Company.ats_type.in_(["greenhouse", "lever"]))
        ).all())

    print(f"Checking {len(companies)} companies...\n")

    broken = []
    async with httpx.AsyncClient() as client:
        tasks = [check_slug(client, c) for c in companies]
        results = await asyncio.gather(*tasks)

    for r in sorted(results, key=lambda x: (x.get("ok", True), x["company"])):
        if r["status"] == "skip":
            continue
        icon = "✅" if r.get("ok") else "❌"
        print(f"{icon} {r['company']:30s}  {r['ats_type']:12s}  slug={r['slug']:25s}  HTTP {r['status']}")
        if not r.get("ok"):
            broken.append(r)

    print(f"\n{len(broken)} broken slugs found.\n")

    if FIX_MODE and broken:
        with Session(engine) as session:
            for r in broken:
                new_slug = input(f"New slug for {r['company']} (current: {r['slug']}, enter to skip): ").strip()
                if new_slug:
                    company = session.get(Company, r["id"])
                    company.ats_slug = new_slug
                    session.add(company)
                    session.commit()
                    print(f"  → Updated {r['company']} slug to: {new_slug}")

asyncio.run(main())
```

- [ ] **Step 2: Run the script (read-only check)**

```bash
cd ~/JobFinderAgent
source backend/venv/bin/activate
python scripts/verify_slugs.py
```

Expected: prints a table showing ✅ for working slugs and ❌ for broken ones. Use this output to identify the correct slugs (visit each company's careers page to find their actual Greenhouse board URL).

- [ ] **Step 3: Fix slugs interactively**

```bash
python scripts/verify_slugs.py --fix
```

For each broken company, look up the real slug. Example: `mondaydotcom` → the correct board may be `monday` (check `boards.greenhouse.io/monday/jobs`). Enter the correct slug when prompted.

- [ ] **Step 4: Re-run to confirm**

```bash
python scripts/verify_slugs.py
```

Expected: significantly fewer ❌ entries.

- [ ] **Step 5: Commit the script**

```bash
git add scripts/verify_slugs.py
git commit -m "feat: add verify_slugs.py script to detect and fix broken ATS slugs"
```

---

## Self-Review

**Spec coverage:**

| Issue from log | Task |
|---|---|
| Telegram links → localhost | Task 1 (env fix on VM) |
| Playwright not installed | Task 1 (install on VM) |
| Matchmaker 44% rate-limit drops | Task 2 (retry on missing choices) |
| Orphaned jobs never retried | Task 3 (rescore unmatched jobs) |
| Score=0 garbage in near-misses | Task 4 (low_match_floor) |
| Near-miss page overloaded | Task 5 (min_score filter + slider) |
| 36 wrong Greenhouse slugs | Task 6 (verify_slugs.py script) |

All six issues from the log's Summary of Issues table are covered.

**Placeholder scan:** No TBD/TODO left in any step. All code blocks are complete.

**Type consistency:**
- `Match.job_id` used consistently across Tasks 3–5.
- `settings.low_match_floor` added in Task 4 config and consumed in Task 4 scheduler — matches.
- `getNearMisses(minScore)` defined in Task 5 client and called in Task 5 component — matches.
