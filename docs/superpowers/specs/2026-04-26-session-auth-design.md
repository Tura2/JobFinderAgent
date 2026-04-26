# Session Auth Design

**Date:** 2026-04-26  
**Status:** Approved  
**Scope:** Replace bearer token auth with HMAC-signed session cookie + login page

---

## Problem

The `PWA_ACCESS_TOKEN` is currently baked into the React JS bundle via `VITE_ACCESS_TOKEN`. Anyone who opens DevTools can read it. The app also has no login screen — the full UI is visible immediately on first visit.

Out of scope for this iteration: HTTPS / Let's Encrypt (future task).

---

## Approach

FastAPI middleware intercepts every request before routing. If no valid session cookie is present, redirect to `/login`. The login page is a standalone HTML file (not part of the React bundle) served by FastAPI. On correct password the backend sets an HMAC-signed cookie and redirects into the app.

---

## Architecture

```
Browser request
      │
      ▼
SessionMiddleware (FastAPI)
      │
      ├── path is /login, /auth/login, /auth/logout, /health?
      │         └── pass through (public)
      │
      ├── has valid signed session cookie?
      │         └── yes → pass through to router
      │
      └── no cookie / invalid / expired
                └── redirect 302 → /login
                          │
                          ▼
                    GET /login → login.html
                    password form → POST /auth/login
                          │
                     correct password?
                          ├── yes → set cookie → redirect 302 → /
                          └── no  → redirect 302 → /login?error=1
```

---

## Cookie Design

**Format:** `<expiry_unix_timestamp>:<hmac_sha256_signature>`

**Validation (middleware):**
1. Read `session` cookie from request
2. Split on `:` → `expiry`, `signature`
3. Recompute `HMAC-SHA256(SECRET_KEY, expiry)`
4. Reject if signature mismatch or `expiry < now()`
5. Invalid → 302 to `/login`

**Properties:**
- `HttpOnly` — JS cannot read the cookie
- `SameSite=Strict` — blocks CSRF
- `Secure` flag: **omitted** (app runs on HTTP; future task to add HTTPS + Secure flag)
- `Max-Age`: configurable via `SESSION_MAX_AGE_DAYS` (default 30 days)

**Password:** reuses existing `PWA_ACCESS_TOKEN` env var. No new password variable.

**Brute-force mitigation:** 1-second `asyncio.sleep` on failed login attempt.

---

## New Env Vars

| Var | Purpose | Default |
|---|---|---|
| `SESSION_SECRET_KEY` | HMAC signing key (generate with `openssl rand -hex 32`) | required |
| `SESSION_MAX_AGE_DAYS` | Cookie lifetime in days | `30` |

`PWA_ACCESS_TOKEN` is retained — it becomes the login password.

**Key rotation = forced logout:** Changing `SESSION_SECRET_KEY` invalidates all existing cookies instantly.

---

## New Files

### `backend/app/middleware/session.py`
Starlette `BaseHTTPMiddleware` subclass.
- `PUBLIC_PATHS = {"/login", "/auth/login", "/auth/logout", "/health"}`
- On each request: if path in public → pass through; else validate cookie → pass through or redirect.
- Cookie validation: parse `expiry:sig`, recompute HMAC, check expiry.

### `backend/app/routers/auth.py`
Two routes:

**`POST /auth/login`** (form body: `password`)
- Compare `password` against `settings.pwa_access_token`
- Wrong: `asyncio.sleep(1)` then redirect to `/login?error=1`
- Correct: build `expiry = now + SESSION_MAX_AGE_DAYS`; sign; set `session` cookie; redirect to `/`

**`POST /auth/logout`**
- Delete `session` cookie
- Redirect to `/login`

### `backend/app/login.html`
Standalone HTML file. No React, no JS framework.
- Dark theme matching PWA (`#030712` background, `#f9fafb` text, indigo accent)
- Single password `<input type="password">`, Submit button
- Shows "Invalid password" message when `?error=1` in URL
- Form `action="/auth/login"` `method="POST"`

---

## Modified Files

### `backend/app/main.py`
- Add `SessionMiddleware` (registered before routers)
- Add `auth` router
- Add `GET /login` route that returns `login.html` as `HTMLResponse`
- Public paths list kept in sync with middleware

### `backend/app/config.py`
- Add `session_secret_key: str`
- Add `session_max_age_days: int = 30`

### `backend/app/auth.py`
- Delete entire file — `verify_token` dependency is removed
- All routers that imported it need `Depends(verify_token)` removed

### All API routers (`matches`, `companies`, `tracker`, `cv_variants`, `scanner`)
- Remove `Depends(verify_token)` from every route function signature
- Remove `from app.auth import verify_token` import

### `frontend/src/api/client.ts`
- Remove `TOKEN` constant and `VITE_ACCESS_TOKEN` reference
- Remove `Authorization` header from `apiFetch`
- Add `credentials: 'include'` to all fetch calls (so session cookie is sent)

### `frontend/src/pages/Settings.tsx`
- Add **Logout** button → `POST /auth/logout` (plain form submit or `fetch`)
- Add **"Developed by Offir Tura"** credit at page bottom
  - Reads LinkedIn URL from `GET /config` response
  - Renders as `<a href={linkedinUrl} target="_blank" rel="noopener noreferrer">`

### `frontend/.env.example` + `frontend/.env.local`
- Remove `VITE_ACCESS_TOKEN` line

### `backend/.env.example`
- Add `SESSION_SECRET_KEY=` and `SESSION_MAX_AGE_DAYS=30`

### `backend/app/main.py` — CORS middleware
- Change `allow_credentials=False` → `allow_credentials=True`
- Change `allow_origins=["*"]` → `allow_origins=[settings.pwa_base_url]` (wildcard + credentials is rejected by browsers)

---

## New Public Endpoint

**`GET /config`** — no auth required  
Returns a minimal JSON object with frontend-safe public config:
```json
{ "linkedin_url": "https://linkedin.com/in/..." }
```
Reads from `settings.applicant_linkedin_url`. This keeps the URL out of the bundle.

---

## Data Flow: Login

```
1. User visits /
2. Middleware: no cookie → 302 /login
3. Browser loads login.html (plain HTML, instant)
4. User types password → submits form to POST /auth/login
5. Backend verifies password == PWA_ACCESS_TOKEN
6. Backend sets HttpOnly session cookie, 302 → /
7. Browser loads /, React bundle loads, app works
8. Every subsequent API call sends cookie automatically (same-origin)
```

## Data Flow: Logout

```
1. User taps Logout in Settings
2. POST /auth/logout
3. Backend deletes session cookie, 302 → /login
4. Browser shows login page
```

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Wrong password | 1s delay + redirect `/login?error=1` |
| Cookie tampered | HMAC mismatch → redirect `/login` |
| Cookie expired | expiry < now() → redirect `/login` |
| `/health` always reachable | Exempt from middleware |
| `SESSION_SECRET_KEY` missing | App fails to start (Pydantic required field) |

---

## Out of Scope (Future Tasks)

- HTTPS + Let's Encrypt (Certbot on VM) — adding `Secure` flag to cookie closes the network interception gap
- Rate limiting on `/auth/login` beyond the 1s sleep
- Multi-device session management

---

## File Change Summary

| File | Action |
|---|---|
| `backend/app/middleware/session.py` | Create |
| `backend/app/routers/auth.py` | Create |
| `backend/app/login.html` | Create |
| `backend/app/main.py` | Modify |
| `backend/app/config.py` | Modify |
| `backend/app/auth.py` | Delete |
| `backend/app/routers/matches.py` | Modify |
| `backend/app/routers/companies.py` | Modify |
| `backend/app/routers/tracker.py` | Modify |
| `backend/app/routers/cv_variants.py` | Modify |
| `backend/app/routers/scanner.py` | Modify |
| `frontend/src/api/client.ts` | Modify |
| `frontend/src/pages/Settings.tsx` | Modify |
| `frontend/.env.example` | Modify |
| `backend/.env.example` | Modify |
