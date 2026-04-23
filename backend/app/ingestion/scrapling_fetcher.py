import logging
import urllib.parse
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

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

# LinkedIn's public guest API — returns server-rendered HTML cards.
# Requires StealthyFetcher's browser context (plain httpx is blocked by LinkedIn).
# geoId=101620260 = Israel; without it LinkedIn defaults to US and misses IL listings.
_LINKEDIN_GUEST_API = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    "?keywords={keywords}&geoId=101620260&start=0"
)


async def fetch_career_page(url: str, base_domain: str) -> list[dict]:
    try:
        from scrapling import StealthyFetcher
        page = await StealthyFetcher.async_fetch(url)

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


async def fetch_linkedin_jobs(company_name: str) -> list[dict]:
    """
    Fetch LinkedIn jobs for a company via the public jobs-guest API.

    StealthyFetcher's browser context is required — plain httpx is blocked by LinkedIn.
    The API returns server-rendered HTML cards without authentication.
    """
    try:
        from scrapling import StealthyFetcher

        api_url = _LINKEDIN_GUEST_API.format(
            keywords=urllib.parse.quote(company_name)
        )
        logger.info(f"LinkedIn guest API: {api_url}")

        page = await StealthyFetcher.async_fetch(api_url, network_idle=True)

        jobs = []
        seen_titles: set[str] = set()

        for card in page.css(".job-search-card"):
            title_els = card.css(".base-search-card__title")
            title = (title_els[0].text or "").strip() if title_els else ""
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)

            loc_els = card.css(".job-search-card__location")
            location = (loc_els[0].text or "").strip() if loc_els else ""

            link_els = card.css("a.base-card__full-link, a")
            href = link_els[0].attrib.get("href", "") if link_els else ""

            jobs.append({
                "title": title,
                "url": href,
                "description_raw": "",
                "location": location,
                "source": "linkedin",
            })

        logger.info(f"LinkedIn found {len(jobs)} jobs for '{company_name}'")
        return jobs

    except Exception as e:
        logger.warning(f"LinkedIn fetch failed for '{company_name}': {e}")
        return []
