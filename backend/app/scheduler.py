import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlmodel import Session, select

from app.config import settings
from app.models.company import Company
from app.models.cv_variant import CVVariant
from app.models.job import Job
from app.models.match import Match
from app.ingestion.ats_fetcher import fetch_greenhouse_jobs, fetch_lever_jobs
from app.ingestion.scrapling_fetcher import fetch_career_page, fetch_linkedin_jobs
from app.ingestion.normalizer import normalize_and_deduplicate
from app.pipeline.matchmaker import score_job
from app.pipeline.cv_selector import select_cv_variant
from app.notifications.telegram import send_match_notification
from app.routers.matches import build_ats_apply_url

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

scan_state = {
    "last_scan_at": None,
    "next_scan_at": None,
    "last_scan_new_jobs": 0,
    "is_running": False,
}


EXCLUDED_TITLE_KEYWORDS = [
    "account manager", "account executive", "sales manager", "sales representative",
    "sales development", "business development", "customer success", "customer support",
    "support engineer", "technical support", "sdr", "bdr", "recruiter", "hr ",
    "human resources", "marketing manager", "content manager", "social media",
    "finance manager", "accountant", "legal", "paralegal", "office manager",
    "operations manager", "product designer", "ux designer", "ui designer",
    "graphic designer", "presales", "pre-sales", "project manager", "program manager",
]

INCLUDED_TITLE_KEYWORDS = [
    "engineer", "developer", "architect",
    "full stack", "fullstack", "full-stack",
    "frontend", "front-end",
    "backend", "back-end",
    "software", "r&d",
    "devops", "dev ops", "site reliability",
    "data scientist", "machine learning",
    "researcher", "scientist",
    "tech lead", "technical lead", "team lead",
]

ISRAEL_LOCATION_KEYWORDS = [
    "israel", "tel aviv", "netanya", "herzliya", "herzelia", "haifa",
    "petah tikva", "petah tiqwa", "petah", "rishon", "rehovot",
    "raanana", "ra'anana", "beer sheva", "beersheba", "kfar saba",
    "modi'in", "modin", "jerusalem", "yahud", "yehud", "bnei brak",
    "holon", "bat yam", "ramat gan", "givatayim", "ness ziona",
    "lod", "ramla", "airport city", "rosh haayin", "rosh ha'ayin", "kiryat",
]


def _is_excluded_title(title: str) -> bool:
    lower = title.lower()
    return any(kw in lower for kw in EXCLUDED_TITLE_KEYWORDS)


def _is_relevant_dev_role(title: str) -> bool:
    lower = title.lower()
    return any(kw in lower for kw in INCLUDED_TITLE_KEYWORDS)


def _is_location_relevant(location: str | None) -> bool:
    if not location:
        return True
    lower = location.lower().strip()
    if any(kw in lower for kw in ISRAEL_LOCATION_KEYWORDS):
        return True
    # Any remote mention is kept — LLM scores location mismatch; remote roles are
    # worth scoring since Israeli candidates can apply to global remote positions.
    if "remote" in lower:
        return True
    return False


def _load_user_profile() -> str:
    profile_path = Path(__file__).parent.parent / "user_profile.md"
    if profile_path.exists():
        return profile_path.read_text(encoding="utf-8")
    return ""


def _get_cv_variants_text(session: Session) -> str:
    variants = session.exec(select(CVVariant).where(CVVariant.is_active == True)).all()
    lines = []
    for v in variants:
        try:
            tags = json.loads(v.focus_tags)
        except (json.JSONDecodeError, TypeError):
            tags = []
        lines.append(f"{v.name} [{', '.join(tags)}]")
    return "\n".join(lines)


def get_active_companies(session: Session) -> list[Company]:
    return list(session.exec(select(Company).where(Company.active == True)).all())


async def fetch_jobs_for_company(company: Company) -> list[dict]:
    if company.ats_type == "greenhouse" and company.ats_slug:
        return await fetch_greenhouse_jobs(company.ats_slug)
    elif company.ats_type == "lever" and company.ats_slug:
        return await fetch_lever_jobs(company.ats_slug)
    elif company.ats_type == "linkedin":
        return await fetch_linkedin_jobs(company.name)
    elif company.career_page_url:
        return await fetch_career_page(company.career_page_url, company.website or "")
    else:
        logger.warning(f"No fetch strategy for company {company.name} (ats_type={company.ats_type})")
        return []


async def run_scan_for_company(company: Company, session: Session) -> list[dict]:
    raw_jobs = await fetch_jobs_for_company(company)
    if not raw_jobs:
        raw_jobs = []

    new_jobs = normalize_and_deduplicate(raw_jobs, company.id, session)

    # Also pick up jobs that exist in DB but have no Match (matchmaker failed previously)
    scored_job_ids: set[int] = {
        row for row in session.exec(
            select(Match.job_id)
            .join(Job, Match.job_id == Job.id)
            .where(Job.company_id == company.id)
        ).all()
    }
    all_company_jobs = list(
        session.exec(select(Job).where(Job.company_id == company.id)).all()
    )
    new_job_ids = {j.id for j in new_jobs}
    unscored_jobs = [
        j for j in all_company_jobs
        if j.id not in scored_job_ids and j.id not in new_job_ids
    ]

    jobs_to_score = new_jobs + unscored_jobs
    filtered_jobs = [
        j for j in jobs_to_score
        if not _is_excluded_title(j.title)
        and _is_relevant_dev_role(j.title)
        and _is_location_relevant(j.location)
    ]
    skipped = len(jobs_to_score) - len(filtered_jobs)
    if skipped:
        logger.info(f"Pre-filter skipped {skipped} irrelevant titles for {company.name}")
    if not filtered_jobs:
        return []

    user_profile = _load_user_profile()
    cv_variants_text = _get_cv_variants_text(session)
    active_variants = list(
        session.exec(select(CVVariant).where(CVVariant.is_active == True)).all()
    )

    results = []

    for job in filtered_jobs:
        match_result = await score_job(
            job_title=job.title,
            company_name=company.name,
            location=job.location or "",
            description=job.description_raw or "",
            user_profile=user_profile,
            cv_variants_text=cv_variants_text,
        )

        if match_result is None:
            logger.warning(f"Matchmaker returned None for job {job.title} — skipping")
            continue

        score = match_result["score"]
        reasoning = match_result["reasoning"]
        cv_name = match_result["cv_variant"]
        score_breakdown = match_result.get("score_breakdown")

        if score < settings.low_match_floor:
            logger.debug(f"Score {score} below floor {settings.low_match_floor} for '{job.title}' — discarding")
            continue

        selected = select_cv_variant(cv_name, active_variants)
        cv_variant_id = selected[0].id if selected else None

        status = "new" if score >= settings.match_threshold else "low_match"

        match = Match(
            job_id=job.id,
            score=score,
            reasoning=reasoning,
            cv_variant_id=cv_variant_id,
            status=status,
            score_breakdown=score_breakdown,
        )
        session.add(match)
        session.commit()
        session.refresh(match)

        if status == "new":
            ats_apply_url = build_ats_apply_url(job.url, company.ats_type)
            await send_match_notification(
                match_id=match.id,
                company_name=company.name,
                job_title=job.title,
                score=score,
                reasoning=reasoning,
                pwa_base_url=settings.pwa_base_url,
                db=session,
                ats_apply_url=ats_apply_url if ats_apply_url != job.url else "",
            )

        results.append({
            "match_id": match.id,
            "job_title": job.title,
            "score": score,
            "status": status,
        })

    return results


async def run_full_scan(session: Session) -> dict:
    scan_state["is_running"] = True
    total_new = 0
    companies = get_active_companies(session)

    for company in companies:
        try:
            results = await run_scan_for_company(company, session)
            total_new += len([r for r in results if r["status"] == "new"])
        except Exception as e:
            logger.error(f"Scan failed for {company.name}: {e}")

    scan_state["is_running"] = False
    scan_state["last_scan_at"] = datetime.now(timezone.utc).isoformat()
    scan_state["last_scan_new_jobs"] = total_new

    return scan_state


async def run_health_check(session: Session) -> None:
    companies = get_active_companies(session)
    for company in companies:
        try:
            jobs = await fetch_jobs_for_company(company)
            tested_at = datetime.now(timezone.utc)
            company.last_test_at = tested_at
            company.last_test_passed = len(jobs) >= 1
            company.last_test_jobs_found = len(jobs)
            session.add(company)
            session.commit()
            logger.info(f"Health check {company.name}: {'pass' if company.last_test_passed else 'fail'} ({len(jobs)} jobs)")
        except Exception as e:
            logger.error(f"Health check failed for {company.name}: {e}")


def _health_check_tick():
    import asyncio
    from app.database import get_session

    session = next(get_session())
    try:
        asyncio.run(run_health_check(session))
    finally:
        session.close()


def start_scheduler():
    scheduler.add_job(
        _scheduler_tick,
        trigger=IntervalTrigger(hours=settings.scan_interval_hours),
        id="job_scan",
        replace_existing=True,
    )
    scheduler.add_job(
        _health_check_tick,
        trigger=IntervalTrigger(days=30),
        id="company_health_check",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started — scanning every {settings.scan_interval_hours}h")


def _scheduler_tick():
    import asyncio
    from app.database import get_session

    session = next(get_session())
    try:
        asyncio.run(run_full_scan(session))
    finally:
        session.close()
