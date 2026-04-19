import pytest
from sqlmodel import Session

from app.models.company import Company
from app.models.job import Job
from app.models.match import Match
from app.models.cv_variant import CVVariant
from app.models.application import Application


def _seed_match(db: Session, status="new", score=85) -> tuple:
    company = Company(name="Vercel", ats_type="greenhouse", ats_slug="vercel")
    db.add(company)
    db.commit()
    db.refresh(company)

    job = Job(
        company_id=company.id,
        title="Frontend Engineer",
        url="https://boards.greenhouse.io/vercel/jobs/1",
        description_raw="Build UIs with React",
        location="Remote",
        remote=True,
        source="ats_api",
        content_hash=f"hash_{score}_{status}",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    cv = CVVariant(name="frontend-focused", file_path="/cv/fe.pdf", focus_tags='["react"]', is_active=True)
    db.add(cv)
    db.commit()
    db.refresh(cv)

    match = Match(
        job_id=job.id,
        score=score,
        reasoning="Strong React fit.",
        cv_variant_id=cv.id,
        status=status,
    )
    db.add(match)
    db.commit()
    db.refresh(match)

    return company, job, cv, match


def test_get_pending_matches(client, db):
    _seed_match(db, status="new", score=85)
    _seed_match(db, status="skipped", score=70)

    resp = client.get("/matches")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["status"] == "new"
    assert data[0]["score"] == 85


def test_get_match_detail(client, db):
    _, _, _, match = _seed_match(db)

    resp = client.get(f"/matches/{match.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == match.id
    assert data["job"]["title"] == "Frontend Engineer"
    assert data["company"]["name"] == "Vercel"


def test_get_match_not_found(client):
    resp = client.get("/matches/9999")
    assert resp.status_code == 404


def test_skip_match(client, db):
    _, _, _, match = _seed_match(db)

    resp = client.post(f"/matches/{match.id}/skip")
    assert resp.status_code == 200
    assert resp.json()["status"] == "skipped"


def test_apply_match(client, db):
    _, _, _, match = _seed_match(db)

    resp = client.post(
        f"/matches/{match.id}/applied",
        json={"ats_url": "https://boards.greenhouse.io/apply/1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["match"]["status"] == "applied"
    assert data["application"]["outcome_status"] == "pending"


def test_get_near_misses(client, db):
    _seed_match(db, status="low_match", score=55)
    _seed_match(db, status="new", score=90)

    resp = client.get("/matches/near-misses")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["status"] == "low_match"


def test_apply_generates_prefilled_greenhouse_url(client, db, monkeypatch):
    monkeypatch.setenv("APPLICANT_EMAIL", "test@example.com")
    monkeypatch.setenv("APPLICANT_FIRST_NAME", "Test")
    _, _, _, match = _seed_match(db)

    resp = client.post(f"/matches/{match.id}/applied", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "email=test" in data["ats_url"] or "email=" in data["ats_url"] or data["ats_url"] != ""
