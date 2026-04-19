import pytest
from sqlmodel import Session, select

from app.models.company import Company
from app.models.job import Job
from app.ingestion.normalizer import normalize_and_deduplicate


def test_normalize_new_jobs(db: Session):
    company = Company(name="Vercel", ats_type="greenhouse", ats_slug="vercel")
    db.add(company)
    db.commit()
    db.refresh(company)

    raw_jobs = [
        {
            "title": "Frontend Engineer",
            "url": "https://boards.greenhouse.io/vercel/jobs/1",
            "description_raw": "Build UIs",
            "location": "Remote",
            "source": "ats_api",
        },
        {
            "title": "Backend Engineer",
            "url": "https://boards.greenhouse.io/vercel/jobs/2",
            "description_raw": "Scale APIs",
            "location": "SF",
            "source": "ats_api",
        },
    ]

    new_jobs = normalize_and_deduplicate(raw_jobs, company.id, db)

    assert len(new_jobs) == 2
    assert new_jobs[0].title == "Frontend Engineer"
    assert new_jobs[0].company_id == company.id
    assert new_jobs[0].content_hash is not None

    all_jobs = db.exec(select(Job)).all()
    assert len(all_jobs) == 2


def test_normalize_deduplicates(db: Session):
    company = Company(name="Stripe", ats_type="lever", ats_slug="stripe")
    db.add(company)
    db.commit()
    db.refresh(company)

    raw_jobs = [
        {"title": "Dev", "url": "http://x.com/1", "description_raw": "", "location": "", "source": "ats_api"},
    ]

    first_pass = normalize_and_deduplicate(raw_jobs, company.id, db)
    assert len(first_pass) == 1

    second_pass = normalize_and_deduplicate(raw_jobs, company.id, db)
    assert len(second_pass) == 0

    all_jobs = db.exec(select(Job)).all()
    assert len(all_jobs) == 1


def test_normalize_handles_remote_detection(db: Session):
    company = Company(name="Co", ats_type="custom")
    db.add(company)
    db.commit()
    db.refresh(company)

    raw = [
        {"title": "Dev", "url": "http://x.com", "description_raw": "", "location": "Remote - US", "source": "ats_api"},
    ]

    jobs = normalize_and_deduplicate(raw, company.id, db)
    assert jobs[0].remote is True


def test_normalize_strips_html(db: Session):
    company = Company(name="Co", ats_type="custom")
    db.add(company)
    db.commit()
    db.refresh(company)

    raw = [
        {
            "title": "Dev",
            "url": "http://x.com",
            "description_raw": "<p>Hello <b>world</b></p>",
            "location": "",
            "source": "ats_api",
        },
    ]

    jobs = normalize_and_deduplicate(raw, company.id, db)
    assert jobs[0].description_raw == "<p>Hello <b>world</b></p>"
