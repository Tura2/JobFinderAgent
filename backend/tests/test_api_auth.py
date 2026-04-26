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
