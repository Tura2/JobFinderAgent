import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlmodel import Session

from app.notifications.telegram import send_match_notification, format_match_message
from app.models.match import Match
from app.models.job import Job
from app.models.company import Company
from app.models.cv_variant import CVVariant


def test_format_match_message():
    msg = format_match_message(
        company_name="Vercel",
        job_title="Senior Frontend Engineer",
        score=88,
        reasoning="Strong React fit. Company builds developer tools.",
        match_id=42,
        pwa_base_url="http://myvm:8000",
    )

    assert "Vercel" in msg
    assert "88%" in msg
    assert "Senior Frontend Engineer" in msg
    assert "Strong React fit" in msg
    assert "http://myvm:8000/matches/42" in msg


def test_format_match_message_special_characters():
    msg = format_match_message(
        company_name="AT&T",
        job_title="C++ Developer (Senior)",
        score=72,
        reasoning="Good C++ skills. Some gaps in telecom.",
        match_id=1,
        pwa_base_url="http://vm:8000",
    )
    assert "AT" in msg
    assert "72%" in msg


@pytest.mark.asyncio
async def test_send_match_notification(db: Session):
    company = Company(name="Stripe", ats_type="greenhouse", ats_slug="stripe")
    db.add(company)
    db.commit()
    db.refresh(company)

    job = Job(company_id=company.id, title="Backend Engineer", url="http://x.com",
              source="ats_api", content_hash="h_notify")
    db.add(job)
    db.commit()
    db.refresh(job)

    cv = CVVariant(name="v1", file_path="/cv.pdf", focus_tags="[]", is_active=True)
    db.add(cv)
    db.commit()
    db.refresh(cv)

    match = Match(job_id=job.id, score=91, reasoning="Perfect match.", cv_variant_id=cv.id, status="new")
    db.add(match)
    db.commit()
    db.refresh(match)

    with patch("app.notifications.telegram.Bot") as MockBot:
        mock_message = MagicMock()
        mock_message.message_id = 12345
        bot_instance = AsyncMock()
        bot_instance.send_message.return_value = mock_message
        MockBot.return_value = bot_instance

        await send_match_notification(
            match_id=match.id,
            company_name="Stripe",
            job_title="Backend Engineer",
            score=91,
            reasoning="Perfect match.",
            pwa_base_url="http://vm:8000",
            db=db,
        )

        bot_instance.send_message.assert_awaited_once()

    db.refresh(match)
    assert match.telegram_message_id == 12345


@pytest.mark.asyncio
async def test_no_duplicate_send(db: Session):
    company = Company(name="Co", ats_type="custom")
    db.add(company)
    db.commit()
    db.refresh(company)

    job = Job(company_id=company.id, title="Dev", url="http://x.com/dup",
              source="ats_api", content_hash="h_dup")
    db.add(job)
    db.commit()
    db.refresh(job)

    cv = CVVariant(name="v1", file_path="/cv.pdf", focus_tags="[]", is_active=True)
    db.add(cv)
    db.commit()
    db.refresh(cv)

    match = Match(job_id=job.id, score=80, reasoning="good", cv_variant_id=cv.id,
                  status="new", telegram_message_id=999)
    db.add(match)
    db.commit()
    db.refresh(match)

    with patch("app.notifications.telegram.Bot") as MockBot:
        await send_match_notification(
            match_id=match.id,
            company_name="Co",
            job_title="Dev",
            score=80,
            reasoning="Good",
            pwa_base_url="http://x",
            db=db,
        )
        MockBot.return_value.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_send_notification_failure_does_not_crash(db: Session):
    company = Company(name="Co2", ats_type="custom")
    db.add(company)
    db.commit()
    db.refresh(company)

    job = Job(company_id=company.id, title="Dev", url="http://x.com/fail",
              source="ats_api", content_hash="h_fail")
    db.add(job)
    db.commit()
    db.refresh(job)

    cv = CVVariant(name="v1", file_path="/cv.pdf", focus_tags="[]", is_active=True)
    db.add(cv)
    db.commit()
    db.refresh(cv)

    match = Match(job_id=job.id, score=80, reasoning="good", cv_variant_id=cv.id, status="new")
    db.add(match)
    db.commit()
    db.refresh(match)

    with patch("app.notifications.telegram.Bot") as MockBot:
        bot_instance = AsyncMock()
        bot_instance.send_message.side_effect = Exception("Telegram API error")
        MockBot.return_value = bot_instance

        # Should not raise
        await send_match_notification(
            match_id=match.id,
            company_name="Co2",
            job_title="Dev",
            score=80,
            reasoning="Good",
            pwa_base_url="http://x",
            db=db,
        )
