import pytest
from datetime import datetime, timezone
from sqlmodel import Session, select

from app.models.company import Company
from app.models.job import Job
from app.models.match import Match
from app.models.cv_variant import CVVariant
from app.models.application import Application


def test_create_company(db: Session):
    company = Company(
        name="Vercel",
        website="https://vercel.com",
        ats_type="greenhouse",
        ats_slug="vercel",
        active=True,
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    assert company.id is not None
    assert company.name == "Vercel"
    assert company.ats_type == "greenhouse"
    assert company.active is True
    assert company.added_at is not None


def test_create_job_with_company(db: Session):
    company = Company(name="Stripe", ats_type="greenhouse", ats_slug="stripe")
    db.add(company)
    db.commit()
    db.refresh(company)

    job = Job(
        company_id=company.id,
        title="Senior Frontend Engineer",
        url="https://boards.greenhouse.io/stripe/jobs/123",
        description_raw="Build payment UIs...",
        location="San Francisco, CA",
        remote=True,
        source="ats_api",
        content_hash="abc123hash",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    assert job.id is not None
    assert job.company_id == company.id
    assert job.content_hash == "abc123hash"


def test_content_hash_unique(db: Session):
    company = Company(name="Co", ats_type="custom")
    db.add(company)
    db.commit()
    db.refresh(company)

    job1 = Job(
        company_id=company.id,
        title="Dev",
        url="http://x.com/1",
        source="ats_api",
        content_hash="samehash",
    )
    db.add(job1)
    db.commit()

    job2 = Job(
        company_id=company.id,
        title="Dev2",
        url="http://x.com/2",
        source="ats_api",
        content_hash="samehash",
    )
    db.add(job2)
    with pytest.raises(Exception):
        db.commit()


def test_create_cv_variant(db: Session):
    cv = CVVariant(
        name="frontend-focused",
        file_path="/cvs/frontend.pdf",
        focus_tags='["react","ui","design-systems"]',
        is_active=True,
    )
    db.add(cv)
    db.commit()
    db.refresh(cv)

    assert cv.id is not None
    assert cv.name == "frontend-focused"
    assert cv.is_active is True


def test_create_match(db: Session):
    company = Company(name="Co", ats_type="lever", ats_slug="co")
    db.add(company)
    db.commit()
    db.refresh(company)

    job = Job(
        company_id=company.id,
        title="Dev",
        url="http://x.com",
        source="ats_api",
        content_hash="h1",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    cv = CVVariant(name="general", file_path="/cv.pdf", focus_tags="[]", is_active=True)
    db.add(cv)
    db.commit()
    db.refresh(cv)

    match = Match(
        job_id=job.id,
        score=85,
        reasoning="Strong React + Node fit.",
        cv_variant_id=cv.id,
        status="new",
    )
    db.add(match)
    db.commit()
    db.refresh(match)

    assert match.id is not None
    assert match.score == 85
    assert match.status == "new"
    assert match.matched_at is not None
    assert match.telegram_message_id is None


def test_create_application(db: Session):
    company = Company(name="Co", ats_type="custom")
    db.add(company)
    db.commit()
    db.refresh(company)

    job = Job(company_id=company.id, title="Dev", url="http://x.com", source="ats_api", content_hash="h2")
    db.add(job)
    db.commit()
    db.refresh(job)

    cv = CVVariant(name="v1", file_path="/cv.pdf", focus_tags="[]", is_active=True)
    db.add(cv)
    db.commit()
    db.refresh(cv)

    match = Match(job_id=job.id, score=90, reasoning="Great", cv_variant_id=cv.id, status="applied")
    db.add(match)
    db.commit()
    db.refresh(match)

    app = Application(
        match_id=match.id,
        cv_variant_id=cv.id,
        ats_url="https://boards.greenhouse.io/apply/123",
        outcome_status="pending",
    )
    db.add(app)
    db.commit()
    db.refresh(app)

    assert app.id is not None
    assert app.outcome_status == "pending"
    assert app.applied_at is not None
