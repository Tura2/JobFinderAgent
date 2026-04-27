import logging
from sqlmodel import Session
from telegram import Bot

from app.config import settings

logger = logging.getLogger(__name__)


def format_match_message(
    company_name: str,
    job_title: str,
    score: int,
    reasoning: str,
    match_id: int,
    pwa_base_url: str,
    ats_apply_url: str = "",
) -> str:
    review_link = f"{pwa_base_url}/matches/{match_id}"
    msg = (
        f"\U0001f3af Match at {company_name} \u00b7 {score}%\n"
        f"{job_title}\n\n"
        f"{reasoning}\n\n"
        f"\U0001f517 Review: {review_link}"
    )
    if ats_apply_url:
        msg += f"\n\U0001f4cb Apply (pre-filled): {ats_apply_url}"
    return msg


async def send_match_notification(
    match_id: int,
    company_name: str,
    job_title: str,
    score: int,
    reasoning: str,
    pwa_base_url: str,
    db: Session,
    ats_apply_url: str = "",
) -> None:
    from app.models.match import Match

    match = db.get(Match, match_id)
    if match and match.telegram_message_id:
        logger.debug(f"Skipping duplicate Telegram send for match {match_id}")
        return

    try:
        bot = Bot(token=settings.telegram_bot_token)
        message = format_match_message(
            company_name=company_name,
            job_title=job_title,
            score=score,
            reasoning=reasoning,
            match_id=match_id,
            pwa_base_url=pwa_base_url,
            ats_apply_url=ats_apply_url,
        )
        sent = await bot.send_message(
            chat_id=settings.telegram_chat_id,
            text=message,
        )
        if match:
            match.telegram_message_id = sent.message_id
            db.add(match)
            db.commit()
        logger.info(f"Telegram notification sent for match {match_id}")
    except Exception as e:
        logger.error(f"Failed to send Telegram notification for match {match_id}: {e}")
