import pytest
from unittest.mock import patch, AsyncMock


def test_list_cv_variants_empty(client):
    resp = client.get("/cv-variants")
    assert resp.status_code == 200
    assert resp.json() == []


def test_add_cv_variant(client):
    resp = client.post("/cv-variants", json={
        "name": "frontend-focused",
        "file_path": "/cvs/frontend.pdf",
        "focus_tags": '["react","ui"]',
    })
    assert resp.status_code == 201
    assert resp.json()["name"] == "frontend-focused"


def test_delete_cv_variant(client):
    resp = client.post("/cv-variants", json={
        "name": "temp", "file_path": "/cv.pdf", "focus_tags": "[]",
    })
    vid = resp.json()["id"]

    resp = client.delete(f"/cv-variants/{vid}")
    assert resp.status_code == 200

    resp = client.get("/cv-variants")
    assert all(v["is_active"] for v in resp.json())


def test_trigger_scan(client):
    with patch("app.routers.scanner.run_full_scan", new_callable=AsyncMock, return_value={
        "last_scan_at": "2026-04-17T10:00:00",
        "last_scan_new_jobs": 3,
        "is_running": False,
    }):
        resp = client.post("/trigger-scan")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Scan triggered"


def test_scan_status(client):
    resp = client.get("/scan-status")
    assert resp.status_code == 200
    assert "last_scan_at" in resp.json()
