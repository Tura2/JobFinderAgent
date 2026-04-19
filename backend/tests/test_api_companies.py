import pytest
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
