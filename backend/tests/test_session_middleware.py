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
