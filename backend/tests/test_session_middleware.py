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
