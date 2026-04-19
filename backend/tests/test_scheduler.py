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
