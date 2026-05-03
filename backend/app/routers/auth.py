import asyncio
import hmac as _hmac
import time
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.config import settings
from app.middleware.session import make_session_cookie

router = APIRouter()

_LOGIN_HTML = (Path(__file__).parent.parent / "login.html").read_text(encoding="utf-8")

_RATE_LIMIT_WINDOW = 60      # seconds
_RATE_LIMIT_MAX_ATTEMPTS = 5
_RATE_LIMIT_MEMORY_CAP = 10_000
_failed_attempts: dict[str, list[float]] = {}


def _is_rate_limited(ip: str) -> bool:
    now = time.monotonic()
    attempts = _failed_attempts.get(ip, [])
    # Keep only attempts within the window
    attempts = [t for t in attempts if now - t < _RATE_LIMIT_WINDOW]
    _failed_attempts[ip] = attempts
    return len(attempts) >= _RATE_LIMIT_MAX_ATTEMPTS


def _record_failure(ip: str) -> None:
    if len(_failed_attempts) >= _RATE_LIMIT_MEMORY_CAP:
        _failed_attempts.clear()
    _failed_attempts.setdefault(ip, []).append(time.monotonic())


def _clear_failures(ip: str) -> None:
    _failed_attempts.pop(ip, None)


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page():
    return HTMLResponse(_LOGIN_HTML)


@router.post("/auth/login")
async def login(request: Request, password: str = Form(...)):
    ip = request.client.host if request.client else "unknown"

    if _is_rate_limited(ip):
        return JSONResponse(
            {"detail": "Too many failed attempts. Try again in 60 seconds."},
            status_code=429,
            headers={"Retry-After": "60"},
        )

    if not _hmac.compare_digest(password, settings.pwa_access_token):
        _record_failure(ip)
        await asyncio.sleep(1)
        return RedirectResponse("/login?error=1", status_code=302)

    _clear_failures(ip)
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
    # Return 200 JSON so fetch() receives the Set-Cookie directly (302 responses
    # are followed silently by fetch, making cookie deletion browser-dependent).
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("session", httponly=True, samesite="strict")
    return resp


@router.get("/config")
async def get_config():
    return JSONResponse({"linkedin_url": settings.applicant_linkedin_url})
