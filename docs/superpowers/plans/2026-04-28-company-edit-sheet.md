# Company Edit Sheet & Fetch Test — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tappable bottom sheet per company row that lets the user edit all fields and run a live fetch test (pass/fail), with results persisted and auto-rechecked monthly.

**Architecture:** Thin `POST /companies/{id}/test` endpoint calls the existing fetcher functions directly, writes pass/fail + job count to three new DB columns, and returns the result. A new APScheduler job runs the same logic for all active companies every 30 days. The existing `BottomSheet` component wraps a new `CompanyEditSheet` component on the frontend.

**Tech Stack:** FastAPI · SQLModel · APScheduler · SQLite (manual ALTER) · React 18 · TypeScript · Vite

---

## File Map

| Action | Path | What changes |
|---|---|---|
| Modify | `backend/app/models/company.py` | Add 3 optional test-result fields |
| Modify | `backend/app/scheduler.py` | Make fetch helper public; add monthly health-check job |
| Modify | `backend/app/routers/companies.py` | Add `POST /{id}/test` endpoint |
| Modify | `backend/tests/test_api_companies.py` | Add 4 tests for the test endpoint |
| Modify | `frontend/src/types/index.ts` | Add 3 fields to `Company` interface; add `TestResult` |
| Modify | `frontend/src/api/client.ts` | Add `testCompany` method |
| Create | `frontend/src/components/CompanyEditSheet.tsx` | New edit + test sheet component |
| Modify | `frontend/src/pages/Companies.tsx` | Tappable rows + sheet state wiring |

---

## Task 1: DB Migration — add test-result columns

**Files:**
- Modify: `backend/app/models/company.py`

- [ ] **Step 1: Run the manual ALTER statements on the production DB**

```bash
cd backend
sqlite3 jobfinder.db "ALTER TABLE companies ADD COLUMN last_test_at TEXT DEFAULT NULL;"
sqlite3 jobfinder.db "ALTER TABLE companies ADD COLUMN last_test_passed INTEGER DEFAULT NULL;"
sqlite3 jobfinder.db "ALTER TABLE companies ADD COLUMN last_test_jobs_found INTEGER DEFAULT NULL;"
```

Expected: no output (SQLite is silent on success). Verify:

```bash
sqlite3 jobfinder.db ".schema companies"
```

Expected output includes `last_test_at`, `last_test_passed`, `last_test_jobs_found`.

- [ ] **Step 2: Add the fields to the SQLModel**

Replace the full contents of `backend/app/models/company.py`:

```python
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class Company(SQLModel, table=True):
    __tablename__ = "companies"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    website: Optional[str] = None
    ats_type: str  # greenhouse | lever | workday | custom | linkedin
    ats_slug: Optional[str] = None
    linkedin_url: Optional[str] = None
    career_page_url: Optional[str] = None
    active: bool = True
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_test_at: Optional[datetime] = Field(default=None)
    last_test_passed: Optional[bool] = Field(default=None)
    last_test_jobs_found: Optional[int] = Field(default=None)
```

- [ ] **Step 3: Verify the in-memory test DB still builds correctly**

```bash
cd backend && source venv/Scripts/activate
pytest tests/test_models.py -v
```

Expected: all pass (SQLModel.metadata.create_all uses the model definition, not the file DB).

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/company.py
git commit -m "feat: add last_test_at/passed/jobs_found columns to Company model"
```

---

## Task 2: Test endpoint — `POST /companies/{id}/test`

**Files:**
- Modify: `backend/app/scheduler.py` (make fetch helper public)
- Modify: `backend/app/routers/companies.py` (add endpoint)

- [ ] **Step 1: Make `_fetch_jobs_for_company` public in `scheduler.py`**

In `backend/app/scheduler.py`, rename the function and update its internal call site:

```python
# Change this (line ~74):
async def _fetch_jobs_for_company(company: Company) -> list[dict]:

# To this:
async def fetch_jobs_for_company(company: Company) -> list[dict]:
```

Also update the one internal call in `run_scan_for_company` (line ~89):

```python
# Change:
    raw_jobs = await _fetch_jobs_for_company(company)
# To:
    raw_jobs = await fetch_jobs_for_company(company)
```

- [ ] **Step 2: Write the failing tests first**

Add to `backend/tests/test_api_companies.py`:

```python
from unittest.mock import patch, AsyncMock


def test_test_company_pass(client):
    resp = client.post("/companies", json={"name": "Wix", "ats_type": "greenhouse", "ats_slug": "wix"})
    cid = resp.json()["id"]

    with patch("app.routers.companies.fetch_jobs_for_company", new_callable=AsyncMock,
               return_value=[{"title": "Engineer", "url": "https://example.com", "description_raw": "", "location": "", "source": "ats_api"}]):
        resp = client.post(f"/companies/{cid}/test")

    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is True
    assert data["jobs_found"] == 1
    assert "tested_at" in data


def test_test_company_fail(client):
    resp = client.post("/companies", json={"name": "Empty Co", "ats_type": "custom", "career_page_url": "https://empty.example.com"})
    cid = resp.json()["id"]

    with patch("app.routers.companies.fetch_jobs_for_company", new_callable=AsyncMock, return_value=[]):
        resp = client.post(f"/companies/{cid}/test")

    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is False
    assert data["jobs_found"] == 0


def test_test_company_persists_result(client):
    resp = client.post("/companies", json={"name": "Persist Co", "ats_type": "lever", "ats_slug": "persistco"})
    cid = resp.json()["id"]

    with patch("app.routers.companies.fetch_jobs_for_company", new_callable=AsyncMock,
               return_value=[{"title": "Dev", "url": "u", "description_raw": "", "location": "", "source": "ats_api"}]):
        client.post(f"/companies/{cid}/test")

    company_data = client.get("/companies").json()
    co = next(c for c in company_data if c["id"] == cid)
    assert co["last_test_passed"] is True
    assert co["last_test_jobs_found"] == 1
    assert co["last_test_at"] is not None


def test_test_company_not_found(client):
    resp = client.post("/companies/9999/test")
    assert resp.status_code == 404
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd backend && source venv/Scripts/activate
pytest tests/test_api_companies.py::test_test_company_pass -v
```

Expected: FAIL — `405 Method Not Allowed` (route doesn't exist yet).

- [ ] **Step 4: Add the test endpoint to `backend/app/routers/companies.py`**

Add imports at the top of the file (after existing imports):

```python
from datetime import datetime, timezone
from app.scheduler import fetch_jobs_for_company
```

Add the response model and endpoint at the bottom of the file:

```python
class CompanyTestResult(BaseModel):
    passed: bool
    jobs_found: int
    tested_at: datetime


@router.post("/{company_id}/test")
async def test_company_fetch(
    company_id: int,
    session: Session = Depends(get_session),
) -> CompanyTestResult:
    company = session.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    jobs = await fetch_jobs_for_company(company)
    tested_at = datetime.now(timezone.utc)
    passed = len(jobs) >= 1

    company.last_test_at = tested_at
    company.last_test_passed = passed
    company.last_test_jobs_found = len(jobs)
    session.add(company)
    session.commit()

    return CompanyTestResult(passed=passed, jobs_found=len(jobs), tested_at=tested_at)
```

- [ ] **Step 5: Run all companies tests to confirm all pass**

```bash
pytest tests/test_api_companies.py -v
```

Expected: all 9 tests pass (5 existing + 4 new).

- [ ] **Step 6: Commit**

```bash
git add backend/app/scheduler.py backend/app/routers/companies.py backend/tests/test_api_companies.py
git commit -m "feat: add POST /companies/{id}/test endpoint with pass/fail result"
```

---

## Task 3: Monthly health-check scheduler job

**Files:**
- Modify: `backend/app/scheduler.py`

- [ ] **Step 1: Add the async health-check function**

Add after `run_full_scan` in `backend/app/scheduler.py`:

```python
async def run_health_check(session: Session) -> None:
    companies = get_active_companies(session)
    for company in companies:
        try:
            jobs = await fetch_jobs_for_company(company)
            tested_at = datetime.now(timezone.utc)
            company.last_test_at = tested_at
            company.last_test_passed = len(jobs) >= 1
            company.last_test_jobs_found = len(jobs)
            session.add(company)
            session.commit()
            logger.info(f"Health check {company.name}: {'pass' if company.last_test_passed else 'fail'} ({len(jobs)} jobs)")
        except Exception as e:
            logger.error(f"Health check failed for {company.name}: {e}")


def _health_check_tick():
    import asyncio
    from app.database import get_session

    session = next(get_session())
    try:
        asyncio.run(run_health_check(session))
    finally:
        session.close()
```

- [ ] **Step 2: Register the monthly job in `start_scheduler`**

In `start_scheduler()`, add after the existing `scheduler.add_job(...)` call:

```python
    scheduler.add_job(
        _health_check_tick,
        trigger=IntervalTrigger(days=30),
        id="company_health_check",
        replace_existing=True,
    )
```

- [ ] **Step 3: Write a test for the health-check function**

Add to `backend/tests/test_scheduler.py` (open the file first to check existing style, then append):

```python
import pytest
from unittest.mock import patch, AsyncMock
from sqlmodel import Session
from app.models.company import Company
from app.scheduler import run_health_check


@pytest.mark.asyncio
async def test_health_check_updates_pass(db):
    company = Company(name="TestCo", ats_type="greenhouse", ats_slug="testco")
    db.add(company)
    db.commit()
    db.refresh(company)

    with patch("app.scheduler.fetch_jobs_for_company", new_callable=AsyncMock,
               return_value=[{"title": "Eng", "url": "u", "description_raw": "", "location": "", "source": "ats_api"}]):
        await run_health_check(db)

    db.refresh(company)
    assert company.last_test_passed is True
    assert company.last_test_jobs_found == 1
    assert company.last_test_at is not None


@pytest.mark.asyncio
async def test_health_check_skips_inactive(db):
    company = Company(name="Inactive", ats_type="greenhouse", ats_slug="inactive", active=False)
    db.add(company)
    db.commit()
    db.refresh(company)

    with patch("app.scheduler.fetch_jobs_for_company", new_callable=AsyncMock, return_value=[]) as mock_fetch:
        await run_health_check(db)

    mock_fetch.assert_not_called()
    db.refresh(company)
    assert company.last_test_at is None
```

- [ ] **Step 4: Run the new scheduler tests**

```bash
cd backend && source venv/Scripts/activate
pytest tests/test_scheduler.py -v -k "health_check"
```

Expected: both pass.

- [ ] **Step 5: Run the full test suite**

```bash
pytest --tb=short
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/scheduler.py backend/tests/test_scheduler.py
git commit -m "feat: add monthly company health-check scheduler job"
```

---

## Task 4: Frontend — types and API client

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add fields to the `Company` interface and add `TestResult` type**

In `frontend/src/types/index.ts`, replace the `Company` interface with:

```ts
export interface Company {
  id: number;
  name: string;
  website: string | null;
  ats_type: string;
  ats_slug: string | null;
  linkedin_url: string | null;
  career_page_url: string | null;
  active: boolean;
  added_at: string;
  last_test_at: string | null;
  last_test_passed: boolean | null;
  last_test_jobs_found: number | null;
}

export interface TestResult {
  passed: boolean;
  jobs_found: number;
  tested_at: string;
}
```

- [ ] **Step 2: Add `testCompany` to the API client**

In `frontend/src/api/client.ts`, add after `deleteCompany`:

```ts
  testCompany: (id: number) =>
    apiFetch<import("../types").TestResult>(`/companies/${id}/test`, { method: "POST" }),
```

- [ ] **Step 3: Run the frontend type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts
git commit -m "feat: add test-result fields to Company type and testCompany API method"
```

---

## Task 5: Frontend — `CompanyEditSheet` component

**Files:**
- Create: `frontend/src/components/CompanyEditSheet.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/CompanyEditSheet.tsx`:

```tsx
import { useState } from 'react';
import { api } from '../api/client';
import type { Company, TestResult } from '../types';

const ATS_TYPES = ['greenhouse', 'lever', 'workday', 'custom', 'linkedin'] as const;

interface Props {
  company: Company;
  onClose: () => void;
  onUpdated: (updated: Company) => void;
}

const inputStyle: React.CSSProperties = {
  width: '100%', background: '#0f172a', border: '1px solid #374151',
  borderRadius: 10, padding: '10px 12px', color: '#f9fafb', fontSize: 14,
  fontFamily: 'inherit', outline: 'none', boxSizing: 'border-box',
};

const labelStyle: React.CSSProperties = {
  color: '#6b7280', fontSize: 11, fontWeight: 600,
  textTransform: 'uppercase', letterSpacing: '0.06em',
  display: 'block', marginBottom: 5, marginTop: 14,
};

function daysAgo(iso: string): number {
  return Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
}

export default function CompanyEditSheet({ company, onClose, onUpdated }: Props) {
  const [form, setForm] = useState({
    name: company.name,
    ats_type: company.ats_type,
    ats_slug: company.ats_slug ?? '',
    career_page_url: company.career_page_url ?? '',
    linkedin_url: company.linkedin_url ?? '',
  });

  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(
    company.last_test_at
      ? { passed: company.last_test_passed ?? false, jobs_found: company.last_test_jobs_found ?? 0, tested_at: company.last_test_at }
      : null
  );

  const runTest = async () => {
    setIsTesting(true);
    try {
      const result = await api.testCompany(company.id);
      setTestResult(result);
      onUpdated({
        ...company,
        ...form,
        ats_slug: form.ats_slug || null,
        career_page_url: form.career_page_url || null,
        linkedin_url: form.linkedin_url || null,
        last_test_passed: result.passed,
        last_test_jobs_found: result.jobs_found,
        last_test_at: result.tested_at,
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSaveAndTest = async () => {
    const updated = await api.updateCompany(company.id, {
      name: form.name,
      ats_type: form.ats_type,
      ats_slug: form.ats_slug || null,
      career_page_url: form.career_page_url || null,
      linkedin_url: form.linkedin_url || null,
    });
    onUpdated(updated);
    await runTest();
  };

  const needsSlug = form.ats_type === 'greenhouse' || form.ats_type === 'lever';
  const needsCareerUrl = form.ats_type === 'workday' || form.ats_type === 'custom';
  const needsLinkedIn = form.ats_type === 'linkedin';

  const daysUntilRecheck = testResult
    ? Math.max(0, 30 - daysAgo(testResult.tested_at))
    : null;

  return (
    <div style={{ padding: '0 0 8px' }}>
      <label style={labelStyle}>Company name</label>
      <input
        style={inputStyle}
        value={form.name}
        onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
      />

      <label style={labelStyle}>ATS type</label>
      <div style={{ display: 'flex', gap: 5, marginTop: 6 }}>
        {ATS_TYPES.map(t => (
          <button
            key={t}
            onClick={() => setForm(f => ({ ...f, ats_type: t }))}
            style={{
              flex: 1, height: 30, borderRadius: 8,
              border: `1px solid ${form.ats_type === t ? '#6366f1' : '#374151'}`,
              background: form.ats_type === t ? '#1e1b4b' : '#1f2937',
              color: form.ats_type === t ? '#818cf8' : '#4b5563',
              fontSize: 10, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit',
              textTransform: 'capitalize',
            }}
          >{t}</button>
        ))}
      </div>

      {needsSlug && (
        <>
          <label style={labelStyle}>Slug</label>
          <input
            style={inputStyle}
            value={form.ats_slug}
            onChange={e => setForm(f => ({ ...f, ats_slug: e.target.value }))}
            placeholder="e.g. vercel, monday, wix"
          />
        </>
      )}
      {needsCareerUrl && (
        <>
          <label style={labelStyle}>Career page URL</label>
          <input
            type="url"
            style={inputStyle}
            value={form.career_page_url}
            onChange={e => setForm(f => ({ ...f, career_page_url: e.target.value }))}
            placeholder="https://..."
          />
        </>
      )}
      {needsLinkedIn && (
        <>
          <label style={labelStyle}>LinkedIn company URL</label>
          <input
            type="url"
            style={inputStyle}
            value={form.linkedin_url}
            onChange={e => setForm(f => ({ ...f, linkedin_url: e.target.value }))}
            placeholder="https://www.linkedin.com/company/..."
          />
        </>
      )}

      {/* Test result block */}
      <div style={{ marginTop: 14 }}>
        {isTesting ? (
          <div style={{
            background: '#0f172a', border: '1px solid #374151', borderRadius: 12,
            padding: '11px 14px', display: 'flex', alignItems: 'center', gap: 10,
          }}>
            <span style={{ fontSize: 16 }}>⏳</span>
            <div>
              <div style={{ color: '#9ca3af', fontSize: 13, fontWeight: 600 }}>Testing…</div>
              <div style={{ color: '#4b5563', fontSize: 11, marginTop: 1 }}>Fetching from {form.ats_type}</div>
            </div>
          </div>
        ) : testResult ? (
          <div style={{
            background: testResult.passed ? '#031a0e' : '#1a0505',
            border: `1px solid ${testResult.passed ? '#166534' : '#7f1d1d'}`,
            borderRadius: 12, padding: '11px 14px',
            display: 'flex', alignItems: 'center', gap: 10,
          }}>
            <span style={{ fontSize: 16 }}>{testResult.passed ? '✅' : '❌'}</span>
            <div>
              <div style={{ color: testResult.passed ? '#22c55e' : '#ef4444', fontSize: 13, fontWeight: 600 }}>
                {testResult.passed ? `Pass — ${testResult.jobs_found} jobs found` : 'Fail — 0 jobs found'}
              </div>
              <div style={{ color: testResult.passed ? '#166534' : '#7f1d1d', fontSize: 11, marginTop: 1 }}>
                Tested {daysAgo(testResult.tested_at)}d ago
                {testResult.passed && daysUntilRecheck !== null && ` · next check in ${daysUntilRecheck}d`}
                {!testResult.passed && ' · check the slug or URL'}
              </div>
            </div>
          </div>
        ) : (
          <div style={{
            background: '#0f172a', border: '1px solid #1f2937', borderRadius: 12,
            padding: '11px 14px', display: 'flex', alignItems: 'center', gap: 10,
          }}>
            <span style={{ fontSize: 16 }}>⬜</span>
            <div>
              <div style={{ color: '#6b7280', fontSize: 13, fontWeight: 600 }}>Never tested</div>
              <div style={{ color: '#4b5563', fontSize: 11, marginTop: 1 }}>Add the URL and hit Test</div>
            </div>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
        <button
          onClick={handleSaveAndTest}
          disabled={isTesting}
          style={{
            flex: 1, height: 44, background: isTesting ? '#374151' : '#6366f1',
            color: '#fff', border: 'none', borderRadius: 12,
            fontSize: 14, fontWeight: 600, cursor: isTesting ? 'default' : 'pointer',
            fontFamily: 'inherit',
          }}
        >
          Save + Test
        </button>
        <button
          onClick={runTest}
          disabled={isTesting}
          style={{
            height: 44, background: '#1f2937', border: '1px solid #374151',
            borderRadius: 12, padding: '0 16px', color: '#9ca3af',
            fontSize: 14, fontWeight: 600, cursor: isTesting ? 'default' : 'pointer',
            fontFamily: 'inherit',
          }}
        >
          ⟳ Test now
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run the frontend type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/CompanyEditSheet.tsx
git commit -m "feat: add CompanyEditSheet component with edit form and test result"
```

---

## Task 6: Frontend — wire up Companies page

**Files:**
- Modify: `frontend/src/pages/Companies.tsx`

- [ ] **Step 1: Replace the full file contents**

Replace `frontend/src/pages/Companies.tsx` with:

```tsx
import { useState, useEffect } from 'react';
import { Plus, Power, Trash2, Building2 } from 'lucide-react';
import { api } from '../api/client';
import type { Company } from '../types';
import BottomSheet from '../components/BottomSheet';
import CompanyEditSheet from '../components/CompanyEditSheet';

const ATS_TYPES = ['greenhouse', 'lever', 'workday', 'custom', 'linkedin'] as const;

const emptyForm = {
  name: '', ats_type: 'greenhouse', ats_slug: '', career_page_url: '', linkedin_url: '',
};

function daysAgo(iso: string): number {
  return Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
}

function TestBadge({ company }: { company: Company }) {
  const dotColor = company.last_test_passed === null
    ? '#374151'
    : company.last_test_passed ? '#22c55e' : '#ef4444';

  const dotShadow = company.last_test_passed === true
    ? '0 0 5px rgba(34,197,94,0.5)'
    : company.last_test_passed === false
      ? '0 0 5px rgba(239,68,68,0.5)'
      : 'none';

  const pillBg = company.last_test_passed === false ? '#1a0505' : '#1f2937';
  const pillColor = company.last_test_passed === false ? '#ef4444' : '#4b5563';

  return (
    <>
      <span style={{
        width: 7, height: 7, borderRadius: '50%', flexShrink: 0, display: 'inline-block',
        background: dotColor, boxShadow: dotShadow,
      }} />
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: 3,
        background: pillBg, borderRadius: 6, padding: '1px 5px',
        fontSize: 10, color: pillColor, flexShrink: 0,
      }}>
        {company.last_test_at ? `🕐 ${daysAgo(company.last_test_at)}d` : '— never'}
      </span>
    </>
  );
}

export default function Companies() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);

  const refresh = () => api.getCompanies().then(setCompanies);
  useEffect(() => { refresh(); }, []);

  const handleAdd = async () => {
    if (!form.name.trim()) return;
    await api.addCompany(form);
    setForm(emptyForm);
    setShowAdd(false);
    refresh();
  };

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    if (!confirm('Remove this company from your watchlist?')) return;
    await api.deleteCompany(id);
    refresh();
  };

  const handleToggle = async (e: React.MouseEvent, company: Company) => {
    e.stopPropagation();
    await api.updateCompany(company.id, { active: !company.active });
    refresh();
  };

  const handleCompanyUpdated = (updated: Company) => {
    setCompanies(cs => cs.map(c => c.id === updated.id ? updated : c));
    if (selectedCompany?.id === updated.id) setSelectedCompany(updated);
  };

  const needsSlug = form.ats_type === 'greenhouse' || form.ats_type === 'lever';
  const needsCareerUrl = form.ats_type === 'workday' || form.ats_type === 'custom';
  const needsLinkedIn = form.ats_type === 'linkedin';
  const active = companies.filter(c => c.active).length;

  const inputStyle: React.CSSProperties = {
    width: '100%', background: '#0f172a', border: '1px solid #374151',
    borderRadius: 10, padding: '10px 12px', color: '#f9fafb', fontSize: 14,
    fontFamily: 'inherit', outline: 'none',
  };

  return (
    <div style={{ paddingBottom: 96, paddingTop: 24, paddingInline: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 18 }}>
        <div>
          <h1 style={{ color: '#fff', fontSize: 26, fontWeight: 700, letterSpacing: '-0.03em' }}>Watchlist</h1>
          <p style={{ color: '#4b5563', fontSize: 13, marginTop: 2 }}>
            {active} active · {companies.length} total
          </p>
        </div>
        <button
          onClick={() => setShowAdd(v => !v)}
          style={{
            height: 36, background: '#6366f1', color: '#fff', border: 'none',
            borderRadius: 10, padding: '0 14px', cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 6,
            fontSize: 13, fontWeight: 600, fontFamily: 'inherit', flexShrink: 0,
          }}
        >
          <Plus size={13} color="#fff" /> Add
        </button>
      </div>

      {showAdd && (
        <div style={{
          background: '#111827', border: '1px solid #1f2937', borderRadius: 16,
          padding: 14, marginBottom: 10,
        }}>
          <div style={{ color: '#4b5563', fontSize: 12, marginBottom: 8 }}>New company</div>
          <input
            value={form.name}
            onChange={e => setForm({ ...form, name: e.target.value })}
            placeholder="Company name"
            style={{ ...inputStyle, marginBottom: 8 }}
          />
          <div style={{ display: 'flex', gap: 5, marginBottom: 10 }}>
            {ATS_TYPES.map(t => (
              <button key={t} onClick={() => setForm({ ...form, ats_type: t })} style={{
                flex: 1, height: 28,
                background: form.ats_type === t ? '#1e1b4b' : '#1f2937',
                border: `1px solid ${form.ats_type === t ? '#6366f1' : '#374151'}`,
                borderRadius: 8, color: form.ats_type === t ? '#818cf8' : '#4b5563',
                fontSize: 10, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit',
                textTransform: 'capitalize',
              }}>{t}</button>
            ))}
          </div>
          {needsSlug && (
            <input
              placeholder={`${form.ats_type === 'greenhouse' ? 'Greenhouse' : 'Lever'} slug (e.g. vercel)`}
              value={form.ats_slug}
              onChange={e => setForm({ ...form, ats_slug: e.target.value })}
              style={{ ...inputStyle, marginBottom: 8 }}
            />
          )}
          {needsCareerUrl && (
            <input type="url" placeholder="Career page URL"
              value={form.career_page_url}
              onChange={e => setForm({ ...form, career_page_url: e.target.value })}
              style={{ ...inputStyle, marginBottom: 8 }}
            />
          )}
          {needsLinkedIn && (
            <input type="url" placeholder="LinkedIn company URL"
              value={form.linkedin_url}
              onChange={e => setForm({ ...form, linkedin_url: e.target.value })}
              style={{ ...inputStyle, marginBottom: 8 }}
            />
          )}
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => { setShowAdd(false); setForm(emptyForm); }}
              style={{
                flex: 1, height: 38, background: '#1f2937', color: '#6b7280',
                border: 'none', borderRadius: 12, cursor: 'pointer',
                fontSize: 13, fontWeight: 600, fontFamily: 'inherit',
              }}
            >Cancel</button>
            <button
              onClick={handleAdd}
              disabled={!form.name.trim()}
              style={{
                flex: 1, height: 38, background: '#6366f1', color: '#fff',
                border: 'none', borderRadius: 12, cursor: 'pointer',
                fontSize: 13, fontWeight: 600, fontFamily: 'inherit',
                opacity: form.name.trim() ? 1 : 0.4,
              }}
            >Add</button>
          </div>
        </div>
      )}

      {companies.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '64px 0' }}>
          <div style={{
            background: '#1a1f2e', border: '1px solid #1f2937', borderRadius: '50%',
            width: 72, height: 72, display: 'flex', alignItems: 'center',
            justifyContent: 'center', margin: '0 auto 16px',
          }}>
            <Building2 size={30} color="#374151" />
          </div>
          <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: 16, marginBottom: 6 }}>No companies yet</div>
          <div style={{ color: '#4b5563', fontSize: 13 }}>Add companies to start scanning for jobs.</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {companies.map(co => (
            <div
              key={co.id}
              onClick={() => setSelectedCompany(co)}
              style={{
                background: '#111827', border: '1px solid #1f2937',
                borderRadius: 16, padding: '12px 14px',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10,
                cursor: 'pointer',
              }}
            >
              <div style={{ minWidth: 0 }}>
                <div style={{ color: co.active ? '#f9fafb' : '#4b5563', fontWeight: 600, fontSize: 15 }}>
                  {co.name}
                </div>
                <div style={{ color: '#374151', fontSize: 12, marginTop: 3, display: 'flex', alignItems: 'center', gap: 5 }}>
                  <TestBadge company={co} />
                  <span>{co.ats_type}{co.ats_slug ? ` · ${co.ats_slug}` : ''}</span>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                <button
                  onClick={e => handleToggle(e, co)}
                  style={{
                    background: co.active ? '#031a0e' : '#1a1f2e',
                    border: `1px solid ${co.active ? '#166534' : '#1f2937'}`,
                    borderRadius: 8, padding: '6px 10px', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: 5,
                    fontSize: 12, fontWeight: 600,
                    color: co.active ? '#22c55e' : '#4b5563',
                    fontFamily: 'inherit',
                  }}
                  aria-label={co.active ? 'Pause' : 'Activate'}
                >
                  <Power size={11} color={co.active ? '#22c55e' : '#4b5563'} />
                  {co.active ? 'Active' : 'Paused'}
                </button>
                <button
                  onClick={e => handleDelete(e, co.id)}
                  style={{
                    background: '#1a0a0a', border: '1px solid #3f1010',
                    borderRadius: 8, padding: 7, cursor: 'pointer',
                    display: 'flex', alignItems: 'center',
                  }}
                  aria-label={`Remove ${co.name}`}
                >
                  <Trash2 size={14} color="#ef4444" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <BottomSheet
        isOpen={selectedCompany !== null}
        onClose={() => setSelectedCompany(null)}
        title={selectedCompany?.name ?? ''}
      >
        {selectedCompany && (
          <CompanyEditSheet
            company={selectedCompany}
            onClose={() => setSelectedCompany(null)}
            onUpdated={handleCompanyUpdated}
          />
        )}
      </BottomSheet>
    </div>
  );
}
```

- [ ] **Step 2: Run the frontend type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Run Vitest**

```bash
cd frontend && npx vitest run
```

Expected: all pass (no Companies-specific unit tests exist, so existing tests should still pass).

- [ ] **Step 4: Start the dev server and manually verify**

```bash
cd frontend && npm run dev
```

Open the app in the browser and verify:
1. Company rows are tappable and open the bottom sheet
2. Active and Delete buttons do NOT open the sheet (stopPropagation works)
3. ATS type tabs switch the visible field (slug ↔ career URL ↔ LinkedIn URL)
4. Test badge (dot + pill) shows correctly for pass/fail/never states
5. "Save + Test" saves and then runs the test, updating the result block
6. "Test now" runs without saving

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Companies.tsx
git commit -m "feat: tappable company rows with edit sheet and test badge"
```

---

## Task 7: Final verification

- [ ] **Step 1: Run the full backend test suite**

```bash
cd backend && source venv/Scripts/activate && pytest --tb=short
```

Expected: all pass.

- [ ] **Step 2: Run frontend type-check and tests**

```bash
cd frontend && npx tsc --noEmit && npx vitest run
```

Expected: no errors, all tests pass.

- [ ] **Step 3: Commit the plan document**

```bash
git add docs/superpowers/plans/2026-04-28-company-edit-sheet.md
git commit -m "docs: add company edit sheet implementation plan"
```
