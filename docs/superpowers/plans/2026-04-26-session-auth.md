# Session Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded bearer token (currently baked into the JS bundle) with an HMAC-signed session cookie and a standalone login page.

**Architecture:** A FastAPI `BaseHTTPMiddleware` intercepts every request — public paths (`/login`, `/auth/*`, `/health`, `/config`) pass through freely; all others require a valid signed session cookie or are redirected to `/login`. The login page is a plain HTML file served by FastAPI (not part of the React bundle). On correct password the backend sets an `HttpOnly SameSite=Strict` cookie and redirects into the app.

**Tech Stack:** Python stdlib `hmac` + `hashlib` (no new deps), FastAPI `BaseHTTPMiddleware`, Starlette `RedirectResponse`, React 18 + Vite, TypeScript.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/app/middleware/__init__.py` | Create | Package marker |
| `backend/app/middleware/session.py` | Create | Cookie sign/verify + middleware class |
| `backend/app/routers/auth.py` | Create | GET /login, POST /auth/login, POST /auth/logout, GET /config |
| `backend/app/login.html` | Create | Dark-themed standalone password page |
| `backend/app/config.py` | Modify | Add `session_secret_key`, `session_max_age_days` |
| `backend/app/main.py` | Modify | Register middleware + auth router; fix CORS |
| `backend/app/routers/matches.py` | Modify | Remove `Depends(verify_token)` |
| `backend/app/routers/companies.py` | Modify | Remove `Depends(verify_token)` |
| `backend/app/routers/tracker.py` | Modify | Remove `Depends(verify_token)` |
| `backend/app/routers/cv_variants.py` | Modify | Remove `Depends(verify_token)` |
| `backend/app/routers/scanner.py` | Modify | Remove `Depends(verify_token)` |
| `backend/app/auth.py` | Delete | Replaced by middleware |
| `backend/tests/conftest.py` | Modify | Replace `verify_token` override with session cookie |
| `backend/tests/test_session_middleware.py` | Create | Tests for cookie utils + middleware |
| `backend/tests/test_api_auth.py` | Create | Tests for login/logout/config routes |
| `frontend/src/api/client.ts` | Modify | Remove bearer token; add `credentials: include` |
| `frontend/src/pages/Settings.tsx` | Modify | Add logout button + "Developed by" credit |
| `backend/.env.example` | Modify | Add `SESSION_SECRET_KEY`, `SESSION_MAX_AGE_DAYS` |
| `frontend/.env.example` | Modify | Remove `VITE_ACCESS_TOKEN` |

---

## Task 1: Config — add session fields

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example`
- Modify: `backend/.env` *(manual step — add your real secret key)*

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_session_middleware.py`:

```python
import os
os.environ.setdefault("SESSION_SECRET_KEY", "test-secret-key-for-testing-32chars!")

import time
import hmac as hmaclib
import hashlib

from app.middleware.session import make_session_cookie, verify_session_cookie

SECRET = "test-secret-key-for-testing-32chars!"


def test_valid_cookie_verifies():
    cookie = make_session_cookie(SECRET, 30)
    assert verify_session_cookie(SECRET, cookie) is True


def test_expired_cookie_rejected():
    expiry = int(time.time()) - 1
    sig = hmaclib.new(SECRET.encode(), str(expiry).encode(), hashlib.sha256).hexdigest()
    assert verify_session_cookie(SECRET, f"{expiry}:{sig}") is False


def test_tampered_cookie_rejected():
    cookie = make_session_cookie(SECRET, 30)
    expiry = cookie.split(":")[0]
    assert verify_session_cookie(SECRET, f"{expiry}:deadbeef") is False


def test_malformed_cookie_rejected():
    assert verify_session_cookie(SECRET, "notacookie") is False
    assert verify_session_cookie(SECRET, "") is False
    assert verify_session_cookie(SECRET, ":") is False
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd backend && source venv/Scripts/activate
pytest tests/test_session_middleware.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `app.middleware.session` doesn't exist yet.

- [ ] **Step 3: Add session fields to config**

In `backend/app/config.py`, add two fields after `pwa_base_url`:

```python
# Session auth
session_secret_key: str
session_max_age_days: int = 30
```

- [ ] **Step 4: Add vars to backend/.env.example**

Append after `PWA_ACCESS_TOKEN`:

```
SESSION_SECRET_KEY=replace-with-output-of--openssl-rand-hex-32
SESSION_MAX_AGE_DAYS=30
```

- [ ] **Step 5: Add SESSION_SECRET_KEY to your real backend/.env**

```bash
# Generate a real key
openssl rand -hex 32
```

Add the output to `backend/.env`:
```
SESSION_SECRET_KEY=<paste output here>
SESSION_MAX_AGE_DAYS=30
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/config.py backend/.env.example
git commit -m "feat: add session_secret_key and session_max_age_days to config"
```

---

## Task 2: Cookie utilities + session middleware

**Files:**
- Create: `backend/app/middleware/__init__.py`
- Create: `backend/app/middleware/session.py`
- Test: `backend/tests/test_session_middleware.py` (extend from Task 1)

- [ ] **Step 1: Create the middleware package**

Create `backend/app/middleware/__init__.py` as an empty file.

- [ ] **Step 2: Implement cookie utils + middleware**

Create `backend/app/middleware/session.py`:

```python
import hashlib
import hmac as hmaclib
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

PUBLIC_PATHS = {"/login", "/auth/login", "/auth/logout", "/health", "/config"}


def _sign(secret: str, expiry: int) -> str:
    return hmaclib.new(secret.encode(), str(expiry).encode(), hashlib.sha256).hexdigest()


def make_session_cookie(secret: str, max_age_days: int) -> str:
    expiry = int(time.time()) + max_age_days * 86400
    return f"{expiry}:{_sign(secret, expiry)}"


def verify_session_cookie(secret: str, value: str) -> bool:
    try:
        expiry_str, sig = value.split(":", 1)
        expiry = int(expiry_str)
    except (ValueError, AttributeError):
        return False
    if time.time() > expiry:
        return False
    return hmaclib.compare_digest(_sign(secret, expiry), sig)


class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)
        from app.config import settings
        cookie = request.cookies.get("session", "")
        if verify_session_cookie(settings.session_secret_key, cookie):
            return await call_next(request)
        return RedirectResponse("/login", status_code=302)
```

- [ ] **Step 3: Add middleware integration tests to test_session_middleware.py**

Append to `backend/tests/test_session_middleware.py`:

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.middleware.session import SessionMiddleware


def _make_app() -> FastAPI:
    import app.config as cfg
    cfg.settings.session_secret_key = SECRET

    test_app = FastAPI()
    test_app.add_middleware(SessionMiddleware)

    @test_app.get("/protected")
    async def protected():
        return {"ok": True}

    @test_app.get("/health")
    async def health():
        return {"ok": True}

    return test_app


def test_middleware_redirects_without_cookie():
    client = TestClient(_make_app(), follow_redirects=False)
    resp = client.get("/protected")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/login"


def test_middleware_allows_valid_cookie():
    cookie = make_session_cookie(SECRET, 30)
    client = TestClient(_make_app(), follow_redirects=False)
    client.cookies.set("session", cookie)
    resp = client.get("/protected")
    assert resp.status_code == 200


def test_middleware_redirects_invalid_cookie():
    client = TestClient(_make_app(), follow_redirects=False)
    client.cookies.set("session", "bogus:value")
    resp = client.get("/protected")
    assert resp.status_code == 302


def test_middleware_allows_public_path_without_cookie():
    client = TestClient(_make_app(), follow_redirects=False)
    resp = client.get("/health")
    assert resp.status_code == 200
```

- [ ] **Step 4: Run all middleware tests**

```bash
pytest tests/test_session_middleware.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/middleware/ backend/tests/test_session_middleware.py
git commit -m "feat: add HMAC session cookie utilities and middleware"
```

---

## Task 3: Auth router (login / logout / config)

**Files:**
- Create: `backend/app/routers/auth.py`
- Create: `backend/tests/test_api_auth.py`

- [ ] **Step 1: Write the failing auth tests**

Create `backend/tests/test_api_auth.py`:

```python
import os
os.environ.setdefault("SESSION_SECRET_KEY", "test-secret-key-for-testing-32chars!")

import pytest
from fastapi.testclient import TestClient
from app.main import app

TEST_PASSWORD = os.environ.get("PWA_ACCESS_TOKEN", "changeme")


@pytest.fixture
def client():
    with TestClient(app, follow_redirects=False) as c:
        yield c


def test_login_correct_password_sets_cookie_and_redirects(client):
    resp = client.post("/auth/login", data={"password": TEST_PASSWORD})
    assert resp.status_code == 302
    assert resp.headers["location"] == "/"
    assert "session" in resp.cookies


def test_login_wrong_password_redirects_with_error(client):
    resp = client.post("/auth/login", data={"password": "wrongpassword"})
    assert resp.status_code == 302
    assert "error=1" in resp.headers["location"]
    assert "session" not in resp.cookies


def test_logout_clears_cookie_and_redirects(client):
    resp = client.post("/auth/logout")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/login"


def test_config_returns_linkedin_url(client):
    resp = client.get("/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "linkedin_url" in data


def test_login_page_returns_html(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert b"password" in resp.content
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_api_auth.py -v
```

Expected: FAIL — routes don't exist yet.

- [ ] **Step 3: Create the auth router**

Create `backend/app/routers/auth.py`:

```python
import asyncio
from pathlib import Path

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.config import settings
from app.middleware.session import make_session_cookie

router = APIRouter()

_LOGIN_HTML = (Path(__file__).parent.parent / "login.html").read_text()


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page():
    return HTMLResponse(_LOGIN_HTML)


@router.post("/auth/login")
async def login(password: str = Form(...)):
    if password != settings.pwa_access_token:
        await asyncio.sleep(1)
        return RedirectResponse("/login?error=1", status_code=302)
    cookie_val = make_session_cookie(settings.session_secret_key, settings.session_max_age_days)
    resp = RedirectResponse("/", status_code=302)
    resp.set_cookie(
        key="session",
        value=cookie_val,
        max_age=settings.session_max_age_days * 86400,
        httponly=True,
        samesite="strict",
    )
    return resp


@router.post("/auth/logout")
async def logout():
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie("session")
    return resp


@router.get("/config")
async def get_config():
    return JSONResponse({"linkedin_url": settings.applicant_linkedin_url})
```

- [ ] **Step 4: Run auth tests** (will still fail — router not registered yet; that's expected)

```bash
pytest tests/test_api_auth.py -v
```

Expected: FAIL with 404 — router isn't in main.py yet. That's fine; we wire it up in Task 5.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/auth.py backend/tests/test_api_auth.py
git commit -m "feat: add auth router (login, logout, config)"
```

---

## Task 4: Login HTML page

**Files:**
- Create: `backend/app/login.html`

- [ ] **Step 1: Create the login page**

Create `backend/app/login.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>JobFinder — Login</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: #030712;
      color: #f9fafb;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      min-height: 100dvh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }
    .card {
      background: #111827;
      border: 1px solid #1f2937;
      border-radius: 20px;
      padding: 32px 28px;
      width: 100%;
      max-width: 360px;
    }
    .logo { font-size: 22px; font-weight: 800; letter-spacing: -0.03em; margin-bottom: 6px; }
    .subtitle { color: #4b5563; font-size: 13px; margin-bottom: 28px; }
    label {
      display: block;
      font-size: 12px;
      font-weight: 600;
      color: #6b7280;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 8px;
    }
    input[type="password"] {
      width: 100%;
      height: 48px;
      background: #0a0f1a;
      border: 1px solid #1f2937;
      border-radius: 12px;
      padding: 0 16px;
      font-size: 16px;
      color: #f9fafb;
      outline: none;
      font-family: inherit;
      margin-bottom: 16px;
      transition: border-color 0.15s;
    }
    input[type="password"]:focus { border-color: #6366f1; }
    .error {
      background: #1f0a0a;
      border: 1px solid #7f1d1d;
      border-radius: 10px;
      color: #fca5a5;
      font-size: 13px;
      padding: 10px 14px;
      margin-bottom: 16px;
      display: none;
    }
    .error.visible { display: block; }
    button {
      width: 100%;
      height: 50px;
      background: #6366f1;
      color: #fff;
      border: none;
      border-radius: 12px;
      font-size: 15px;
      font-weight: 600;
      cursor: pointer;
      font-family: inherit;
      transition: opacity 0.15s;
    }
    button:active { opacity: 0.85; }
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">JobFinder</div>
    <div class="subtitle">Autonomous job hunting pipeline</div>
    <div class="error" id="err">Incorrect password — try again.</div>
    <form method="POST" action="/auth/login">
      <label for="password">Password</label>
      <input type="password" id="password" name="password"
             autocomplete="current-password" autofocus />
      <button type="submit">Unlock</button>
    </form>
  </div>
  <script>
    if (new URLSearchParams(location.search).get('error')) {
      document.getElementById('err').classList.add('visible');
    }
  </script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/login.html
git commit -m "feat: add dark-themed login page"
```

---

## Task 5: Wire up main.py

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Register middleware, auth router, and fix CORS**

Replace the entire contents of `backend/app/main.py`:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.database import create_db_and_tables
from app.middleware.session import SessionMiddleware
from app.routers import matches, companies, tracker, cv_variants, scanner
from app.routers import auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    try:
        from app.scheduler import start_scheduler
        start_scheduler()
    except Exception:
        pass
    yield


app = FastAPI(
    title="JobFinderAgent",
    description="Autonomous Job Hunting Pipeline API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(SessionMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.pwa_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, tags=["auth"])
app.include_router(matches.router, prefix="/matches", tags=["matches"])
app.include_router(companies.router, prefix="/companies", tags=["companies"])
app.include_router(tracker.router, tags=["tracker"])
app.include_router(cv_variants.router, prefix="/cv-variants", tags=["cv-variants"])
app.include_router(scanner.router, tags=["scanner"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "jobfinder-agent"}


pwa_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if pwa_dist.exists():
    app.mount("/", StaticFiles(directory=str(pwa_dist), html=True), name="pwa")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
```

- [ ] **Step 2: Run auth tests — they should now pass**

```bash
pytest tests/test_api_auth.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: register session middleware and auth router in main.py"
```

---

## Task 6: Strip verify_token from all routers + update conftest

**Files:**
- Modify: `backend/tests/conftest.py`
- Modify: `backend/app/routers/matches.py`
- Modify: `backend/app/routers/companies.py`
- Modify: `backend/app/routers/tracker.py`
- Modify: `backend/app/routers/cv_variants.py`
- Modify: `backend/app/routers/scanner.py`
- Delete: `backend/app/auth.py`

- [ ] **Step 1: Update conftest.py to use session cookie instead of verify_token override**

Replace the entire contents of `backend/tests/conftest.py`:

```python
import os
os.environ.setdefault("SESSION_SECRET_KEY", "test-secret-key-for-testing-32chars!")

import pytest
from sqlmodel import SQLModel, Session, create_engine
from fastapi.testclient import TestClient

import app.models  # noqa: F401 — register all models with metadata


@pytest.fixture(name="engine")
def test_engine():
    engine = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(engine)
    yield engine


@pytest.fixture(name="db")
def db_session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def test_client(engine):
    from app.main import app
    from app.database import get_session
    from app.middleware.session import make_session_cookie
    from app.config import settings

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session

    cookie_val = make_session_cookie(settings.session_secret_key, settings.session_max_age_days)

    with TestClient(app, follow_redirects=False) as c:
        c.cookies.set("session", cookie_val)
        yield c

    app.dependency_overrides.clear()
```

- [ ] **Step 2: Strip verify_token from matches.py**

In `backend/app/routers/matches.py`:

Remove line 9: `from app.auth import verify_token`

Change line 18 from:
```python
router = APIRouter(dependencies=[Depends(verify_token)])
```
to:
```python
router = APIRouter()
```

- [ ] **Step 3: Strip verify_token from companies.py**

In `backend/app/routers/companies.py`:

Remove: `from app.auth import verify_token`

Change:
```python
router = APIRouter(dependencies=[Depends(verify_token)])
```
to:
```python
router = APIRouter()
```

- [ ] **Step 4: Strip verify_token from tracker.py**

In `backend/app/routers/tracker.py`:

Remove: `from app.auth import verify_token`

Change:
```python
router = APIRouter(dependencies=[Depends(verify_token)])
```
to:
```python
router = APIRouter()
```

- [ ] **Step 5: Strip verify_token from cv_variants.py**

In `backend/app/routers/cv_variants.py`:

Remove: `from app.auth import verify_token`

Change:
```python
router = APIRouter(dependencies=[Depends(verify_token)])
```
to:
```python
router = APIRouter()
```

- [ ] **Step 6: Strip verify_token from scanner.py**

In `backend/app/routers/scanner.py`:

Remove: `from app.auth import verify_token`

Change:
```python
router = APIRouter(dependencies=[Depends(verify_token)])
```
to:
```python
router = APIRouter()
```

- [ ] **Step 7: Delete auth.py**

```bash
rm backend/app/auth.py
```

- [ ] **Step 8: Run the full test suite**

```bash
cd backend && pytest -v
```

Expected: all existing tests PASS (no 401 failures). If any test imports `from app.auth import verify_token`, fix that import — it should now be gone.

- [ ] **Step 9: Commit**

```bash
git add backend/tests/conftest.py \
        backend/app/routers/matches.py \
        backend/app/routers/companies.py \
        backend/app/routers/tracker.py \
        backend/app/routers/cv_variants.py \
        backend/app/routers/scanner.py
git rm backend/app/auth.py
git commit -m "feat: remove bearer token auth — middleware handles all auth"
```

---

## Task 7: Frontend changes

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/.env.example`

- [ ] **Step 1: Update client.ts**

Replace the entire contents of `frontend/src/api/client.ts`:

```typescript
const BASE_URL = import.meta.env.VITE_API_URL || "";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!resp.ok) {
    throw new Error(`API error ${resp.status}: ${await resp.text()}`);
  }

  return resp.json();
}

export const api = {
  getMatches: () => apiFetch<import("../types").MatchListItem[]>("/matches"),
  getMatch: (id: number) => apiFetch<import("../types").MatchDetail>(`/matches/${id}`),
  skipMatch: (id: number) => apiFetch<{ status: string }>(`/matches/${id}/skip`, { method: "POST" }),
  applyMatch: (id: number, atsUrl?: string, chosenCvVariantId?: number) =>
    apiFetch<{ match: import("../types").MatchListItem; application: { id: number }; ats_url: string }>(
      `/matches/${id}/applied`,
      { method: "POST", body: JSON.stringify({ ats_url: atsUrl, chosen_cv_variant_id: chosenCvVariantId }) }
    ),
  getNearMisses: () => apiFetch<import("../types").MatchListItem[]>("/matches/near-misses"),

  getTracker: () => apiFetch<import("../types").Application[]>("/tracker"),
  updateApplication: (id: number, data: { outcome_status?: string; notes?: string }) =>
    apiFetch<import("../types").Application>(`/applications/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  getCompanies: () => apiFetch<import("../types").Company[]>("/companies"),
  addCompany: (data: Partial<import("../types").Company>) =>
    apiFetch<import("../types").Company>("/companies", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateCompany: (id: number, data: Partial<import("../types").Company>) =>
    apiFetch<import("../types").Company>(`/companies/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteCompany: (id: number) =>
    apiFetch<{ deleted: boolean }>(`/companies/${id}`, { method: "DELETE" }),

  getCVVariants: () => apiFetch<import("../types").CVVariant[]>("/cv-variants"),
  addCVVariant: (data: { name: string; file_path: string; focus_tags: string }) =>
    apiFetch<import("../types").CVVariant>("/cv-variants", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  triggerScan: () => apiFetch<{ message: string }>("/trigger-scan", { method: "POST" }),
  getScanStatus: () => apiFetch<import("../types").ScanStatus>("/scan-status"),

  getConfig: () => apiFetch<{ linkedin_url: string }>("/config"),
};
```

- [ ] **Step 2: Update Settings.tsx — add logout button and credit**

In `frontend/src/pages/Settings.tsx`:

a) Add `useEffect` import already exists. Add `LogOut` to the lucide import:

```typescript
import { useState, useEffect, useRef } from 'react';
import { Play, RefreshCw, CheckCircle2, LogOut } from 'lucide-react';
import { api } from '../api/client';
import type { ScanStatus } from '../types';
```

b) Add `linkedinUrl` state alongside `scanStatus`:

```typescript
const [linkedinUrl, setLinkedinUrl] = useState<string | null>(null);
```

c) Fetch config on mount — add inside the component after the existing `useEffect`:

```typescript
useEffect(() => {
  api.getConfig().then(c => setLinkedinUrl(c.linkedin_url)).catch(() => {});
}, []);
```

d) Add logout handler after `handleScan`:

```typescript
const handleLogout = () => {
  fetch('/auth/logout', { method: 'POST', credentials: 'include' })
    .finally(() => { window.location.href = '/login'; });
};
```

e) Replace the final `{/* About */}` card and closing tags with:

```tsx
      {/* Account */}
      <div style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 16, padding: 16, marginBottom: 10 }}>
        <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: 15, marginBottom: 12 }}>Account</div>
        <button
          onClick={handleLogout}
          style={{
            width: '100%', height: 46, fontSize: 14, borderRadius: 12,
            border: '1px solid #374151', background: 'transparent',
            color: '#9ca3af', cursor: 'pointer', display: 'flex',
            alignItems: 'center', justifyContent: 'center', gap: 8,
            fontWeight: 600, fontFamily: 'inherit',
          }}
        >
          <LogOut size={15} />
          Log out
        </button>
      </div>

      {/* About */}
      <div style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 16, padding: 16 }}>
        <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: 14, marginBottom: 6 }}>JobFinder Agent v0.1.0</div>
        <div style={{ color: '#4b5563', fontSize: 13, marginBottom: linkedinUrl ? 12 : 0 }}>
          Autonomous job hunting pipeline
        </div>
        {linkedinUrl && (
          <a
            href={linkedinUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: '#6366f1', fontSize: 12, fontWeight: 600, textDecoration: 'none' }}
          >
            Developed by Offir Tura
          </a>
        )}
      </div>
```

- [ ] **Step 3: Remove VITE_ACCESS_TOKEN from frontend/.env.example**

In `frontend/.env.example`, remove the line:
```
VITE_ACCESS_TOKEN=changeme
```

Also remove it from `frontend/.env.local` if it exists on your machine (not committed).

- [ ] **Step 4: Run frontend type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/pages/Settings.tsx frontend/.env.example
git commit -m "feat: switch frontend to cookie auth, add logout and credit to Settings"
```

---

## Task 8: VM deploy + smoke test

- [ ] **Step 1: Push to main and deploy**

```bash
git checkout main && git merge master && git push origin main
```

On the VM:
```bash
cd ~/JobFinderAgent && bash scripts/deploy.sh
sudo systemctl restart jobfinder
```

- [ ] **Step 2: Smoke test**

1. Open `http://<vm-ip>:8000` in browser → should see login page (not the app)
2. Enter wrong password → should see "Incorrect password" error
3. Enter correct password (your `PWA_ACCESS_TOKEN`) → should redirect into the app
4. Navigate around — all pages should work
5. Open DevTools → Network tab → confirm requests carry `Cookie: session=...` header, no `Authorization` header
6. Open DevTools → Application → Cookies → confirm `session` cookie is `HttpOnly`
7. Tap Settings → tap "Log out" → should redirect to login page
8. Tap "Developed by Offir Tura" → should open LinkedIn in new tab

- [ ] **Step 3: Confirm /health still reachable without auth**

```bash
curl http://<vm-ip>:8000/health
```

Expected: `{"status":"ok","service":"jobfinder-agent"}`

---

## Future Tasks (out of scope)

- **HTTPS + Let's Encrypt**: Run Certbot on the VM, add `secure=True` to `resp.set_cookie(...)` in `auth.py`, update `pwa_base_url` to `https://`. This closes the network interception gap.
- **Login rate limiting**: Replace the 1-second sleep with a proper attempt counter (e.g. in-memory dict with exponential backoff).
