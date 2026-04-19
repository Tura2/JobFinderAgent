import logging
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

StealthyFetcher = None
DynamicFetcher = None


def _load_scrapling():
    global StealthyFetcher, DynamicFetcher
    if StealthyFetcher is None:
        from scrapling import StealthyFetcher as SF, DynamicFetcher as DF
        StealthyFetcher = SF
        DynamicFetcher = DF


JOB_LINK_SELECTORS = [
    'a[href*="job"]',
    'a[href*="career"]',
    'a[href*="position"]',
    'a[href*="opening"]',
    'a[href*="apply"]',
    ".job-listing a",
    ".careers-listing a",
    '[data-automation="job-link"]',
]


async def fetch_career_page(url: str, base_domain: str) -> list[dict]:
    try:
        _load_scrapling()
        fetcher = StealthyFetcher()
        page = fetcher.fetch(url)

        combined_selector = ", ".join(JOB_LINK_SELECTORS)
        elements = page.css(combined_selector)

        jobs = []
        seen_titles = set()
        for el in elements:
            title = (el.text or "").strip()
            href = el.attrib.get("href", "")
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)

            full_url = href if href.startswith("http") else urljoin(url, href)
            jobs.append({
                "title": title,
                "url": full_url,
                "description_raw": "",
                "location": "",
                "source": "scrapling",
            })
        return jobs

    except Exception as e:
        logger.warning(f"Career page fetch failed for {url}: {e}")
        return []


async def fetch_linkedin_jobs(linkedin_url: str) -> list[dict]:
    try:
        _load_scrapling()
        fetcher = DynamicFetcher()
        page = fetcher.fetch(linkedin_url)

        elements = page.css('a[href*="linkedin.com/jobs/view"]')

        jobs = []
        seen_titles = set()
        for el in elements:
            title = (el.text or "").strip()
            href = el.attrib.get("href", "")
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)
            jobs.append({
                "title": title,
                "url": href,
                "description_raw": "",
                "location": "",
                "source": "linkedin",
            })
        return jobs

    except Exception as e:
        logger.warning(f"LinkedIn fetch failed for {linkedin_url}: {e}")
        return []
