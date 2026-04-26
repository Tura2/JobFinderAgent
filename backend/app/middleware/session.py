import hashlib
import hmac as hmaclib
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

# /config is public so the frontend can read applicant_linkedin_url before login
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
