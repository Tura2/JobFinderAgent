import pytest
from sqlmodel import Session

from app.models.company import Company
from app.models.job import Job
from app.models.match import Match
from app.models.cv_variant import CVVariant
from app.models.application import Application


def _seed_application(db: Session, outcome="pending") -> Application:
    c = Company(name="Co", ats_type="custom")
    db.add(c)
    db.commit()
    db.refresh(c)

    j = Job(company_id=c.id, title="Dev", url="http://x.com", source="ats_api",
            content_hash=f"h_{outcome}_{id(db)}")
    db.add(j)
    db.commit()
    db.refresh(j)

    cv = CVVariant(name="v1", file_path="/cv.pdf", focus_tags="[]", is_active=True)
    db.add(cv)
    db.commit()
    db.refresh(cv)

    m = Match(job_id=j.id, score=85, reasoning="Good", cv_variant_id=cv.id, status="applied")
    db.add(m)
    db.commit()
    db.refresh(m)

    app = Application(match_id=m.id, cv_variant_id=cv.id, outcome_status=outcome)
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


def test_get_tracker(client, db):
    _seed_application(db, "pending")

    resp = client.get("/tracker")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["outcome_status"] == "pending"


def test_update_application(client, db):
    app = _seed_application(db, "pending")

    resp = client.patch(f"/applications/{app.id}", json={
        "outcome_status": "interview",
        "notes": "Phone screen scheduled for next week",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["outcome_status"] == "interview"
    assert data["notes"] == "Phone screen scheduled for next week"


def test_update_nonexistent_application(client):
    resp = client.patch("/applications/9999", json={"outcome_status": "offer"})
    assert resp.status_code == 404
