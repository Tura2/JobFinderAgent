import hashlib
import logging
from sqlmodel import Session, select

from app.models.job import Job

logger = logging.getLogger(__name__)


def compute_content_hash(company_id: int, title: str, url: str) -> str:
    raw = f"{company_id}:{title}:{url}"
    return hashlib.sha256(raw.encode()).hexdigest()


def detect_remote(location: str, description: str) -> bool:
    text = f"{location} {description}".lower()
    return "remote" in text


def normalize_and_deduplicate(
    raw_jobs: list[dict],
    company_id: int,
    session: Session,
) -> list[Job]:
    new_jobs = []

    for raw in raw_jobs:
        title = raw.get("title", "").strip()
        url = raw.get("url", "").strip()
        if not title or not url:
            logger.debug(f"Skipping job with missing title or url: {raw}")
            continue

        content_hash = compute_content_hash(company_id, title, url)

        existing = session.exec(
            select(Job).where(Job.content_hash == content_hash)
        ).first()
        if existing:
            logger.debug(f"Duplicate skipped: {title}")
            continue

        description_raw = raw.get("description_raw", "")
        location = raw.get("location", "")
        remote = detect_remote(location, description_raw)

        job = Job(
            company_id=company_id,
            title=title,
            url=url,
            description_raw=description_raw,
            location=location,
            remote=remote,
            source=raw.get("source", "ats_api"),
            content_hash=content_hash,
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        new_jobs.append(job)

    return new_jobs
