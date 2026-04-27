import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from sqlmodel import Session

from app.models.company import Company
from app.models.cv_variant import CVVariant
from app.scheduler import run_scan_for_company, get_active_companies


def _seed_company(db: Session, **kwargs) -> Company:
    defaults = {"name": "TestCo", "ats_type": "greenhouse", "ats_slug": "testco", "active": True}
    defaults.update(kwargs)
    c = Company(**defaults)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _seed_cv(db: Session) -> CVVariant:
    cv = CVVariant(
        name="fullstack-automation",
        file_path="/cv/fs.pdf",
        focus_tags=json.dumps(["node", "react"]),
        is_active=True,
    )
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return cv


def test_get_active_companies(db: Session):
    _seed_company(db, name="Active1", active=True)
    _seed_company(db, name="Active2", active=True)
    _seed_company(db, name="Inactive", active=False, ats_slug="inactive")

    companies = get_active_companies(db)
    assert len(companies) == 2
    assert all(c.active for c in companies)


@pytest.mark.asyncio
async def test_run_scan_for_greenhouse_company(db: Session):
    company = _seed_company(db)
    cv = _seed_cv(db)

    mock_raw_jobs = [
        {"title": "Dev", "url": "http://x.com/1", "description_raw": "Build stuff", "location": "Remote", "source": "ats_api"},
    ]

    with patch("app.scheduler.fetch_greenhouse_jobs", new_callable=AsyncMock, return_value=mock_raw_jobs), \
         patch("app.scheduler.score_job", new_callable=AsyncMock, return_value={
             "score": 85, "reasoning": "Great fit", "cv_variant": "fullstack-automation"
         }), \
         patch("app.scheduler.send_match_notification", new_callable=AsyncMock) as mock_notify, \
         patch("app.scheduler._load_user_profile", return_value="profile text"), \
         patch("app.scheduler._get_cv_variants_text", return_value="fullstack-automation [node, react]"):

        results = await run_scan_for_company(company, db)

    assert len(results) == 1
    assert results[0]["score"] == 85
    mock_notify.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_scan_low_score_no_notification(db: Session):
    company = _seed_company(db)
    cv = _seed_cv(db)

    mock_raw_jobs = [
        {"title": "Java Architect", "url": "http://x.com/2", "description_raw": "Java EE", "location": "Austin", "source": "ats_api"},
    ]

    with patch("app.scheduler.fetch_greenhouse_jobs", new_callable=AsyncMock, return_value=mock_raw_jobs), \
         patch("app.scheduler.score_job", new_callable=AsyncMock, return_value={
             "score": 30, "reasoning": "Wrong domain", "cv_variant": "fullstack-automation"
         }), \
         patch("app.scheduler.send_match_notification", new_callable=AsyncMock) as mock_notify, \
         patch("app.scheduler._load_user_profile", return_value="profile"), \
         patch("app.scheduler._get_cv_variants_text", return_value="fullstack-automation [node]"):

        results = await run_scan_for_company(company, db)

    assert len(results) == 1
    assert results[0]["score"] == 30
    mock_notify.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_scan_dedup_skips_existing(db: Session):
    company = _seed_company(db)
    cv = _seed_cv(db)

    mock_raw_jobs = [
        {"title": "Dev", "url": "http://x.com/1", "description_raw": "Build", "location": "", "source": "ats_api"},
    ]

    with patch("app.scheduler.fetch_greenhouse_jobs", new_callable=AsyncMock, return_value=mock_raw_jobs), \
         patch("app.scheduler.score_job", new_callable=AsyncMock, return_value={
             "score": 85, "reasoning": "Great", "cv_variant": "fullstack-automation"
         }), \
         patch("app.scheduler.send_match_notification", new_callable=AsyncMock), \
         patch("app.scheduler._load_user_profile", return_value="profile"), \
         patch("app.scheduler._get_cv_variants_text", return_value="fullstack-automation [node]"):

        first = await run_scan_for_company(company, db)
        assert len(first) == 1

        second = await run_scan_for_company(company, db)
        assert len(second) == 0


@pytest.mark.asyncio
async def test_orphaned_jobs_are_rescored(db):
    """Jobs in DB with no Match (matchmaker previously failed) must be scored on the next scan."""
    from app.models.company import Company
    from app.models.job import Job
    from app.models.match import Match
    from app.scheduler import run_scan_for_company
    from unittest.mock import AsyncMock, patch
    from sqlmodel import select

    company = Company(name="OrphanCo", ats_type="greenhouse", ats_slug="orphanco")
    db.add(company)
    db.commit()
    db.refresh(company)

    cv = _seed_cv(db)

    orphan = Job(
        company_id=company.id,
        title="Backend Engineer",
        url="https://boards.greenhouse.io/orphanco/jobs/99",
        source="ats_api",
        content_hash="orphan-hash-99",
    )
    db.add(orphan)
    db.commit()
    db.refresh(orphan)

    mock_score = {"score": 75, "reasoning": "Good fit", "cv_variant": "general", "score_breakdown": "{}"}

    with patch("app.scheduler._fetch_jobs_for_company", new=AsyncMock(return_value=[])), \
         patch("app.scheduler.score_job", new=AsyncMock(return_value=mock_score)), \
         patch("app.scheduler.send_match_notification", new=AsyncMock()):
        results = await run_scan_for_company(company, db)

    assert len(results) == 1
    assert results[0]["job_title"] == "Backend Engineer"
    assert results[0]["score"] == 75
    match = db.exec(select(Match).where(Match.job_id == orphan.id)).first()
    assert match is not None
