import httpx
import logging

logger = logging.getLogger(__name__)


async def fetch_greenhouse_jobs(slug: str) -> list[dict]:
    url = f"https://boards.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        logger.warning(f"Greenhouse fetch failed for {slug}: {e}")
        return []

    jobs = []
    for raw in data.get("jobs", []):
        jobs.append({
            "title": raw["title"],
            "url": raw["absolute_url"],
            "description_raw": raw.get("content", ""),
            "location": raw.get("location", {}).get("name", ""),
            "source": "ats_api",
        })
    return jobs


async def fetch_lever_jobs(slug: str) -> list[dict]:
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        logger.warning(f"Lever fetch failed for {slug}: {e}")
        return []

    jobs = []
    for raw in data:
        jobs.append({
            "title": raw["text"],
            "url": raw["hostedUrl"],
            "description_raw": raw.get("descriptionPlain", ""),
            "location": raw.get("categories", {}).get("location", ""),
            "source": "ats_api",
        })
    return jobs
