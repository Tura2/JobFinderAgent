import pytest
from unittest.mock import patch, AsyncMock
from app.models.company import Company


def test_list_companies_empty(client):
    resp = client.get("/companies")
    assert resp.status_code == 200
    assert resp.json() == []


def test_add_company(client):
    resp = client.post("/companies", json={
        "name": "Vercel",
        "website": "https://vercel.com",
        "ats_type": "greenhouse",
        "ats_slug": "vercel",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Vercel"
    assert data["ats_type"] == "greenhouse"
    assert data["active"] is True


def test_list_companies_after_add(client):
    client.post("/companies", json={"name": "Co1", "ats_type": "lever", "ats_slug": "co1"})
    client.post("/companies", json={"name": "Co2", "ats_type": "greenhouse", "ats_slug": "co2"})

    resp = client.get("/companies")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_update_company(client):
    resp = client.post("/companies", json={"name": "Old", "ats_type": "custom"})
    cid = resp.json()["id"]

    resp = client.patch(f"/companies/{cid}", json={"name": "New", "active": False})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"
    assert resp.json()["active"] is False


def test_delete_company(client):
    resp = client.post("/companies", json={"name": "ToDelete", "ats_type": "custom"})
    cid = resp.json()["id"]

    resp = client.delete(f"/companies/{cid}")
    assert resp.status_code == 200

    resp = client.get("/companies")
    assert len(resp.json()) == 0


def test_update_nonexistent_company(client):
    resp = client.patch("/companies/9999", json={"name": "X"})
    assert resp.status_code == 404


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
