import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.ingestion.scrapling_fetcher import fetch_career_page, fetch_linkedin_jobs


@pytest.mark.asyncio
async def test_fetch_career_page():
    mock_page = MagicMock()
    mock_element_1 = MagicMock()
    mock_element_1.text = "Senior React Developer"
    mock_element_1.attrib = {"href": "/careers/senior-react-dev"}

    mock_element_2 = MagicMock()
    mock_element_2.text = "DevOps Engineer"
    mock_element_2.attrib = {"href": "/careers/devops-eng"}

    mock_page.css.return_value = [mock_element_1, mock_element_2]
    mock_page.url = "https://example.com/careers"

    with patch("app.ingestion.scrapling_fetcher.StealthyFetcher") as MockFetcher:
        instance = MagicMock()
        instance.fetch.return_value = mock_page
        MockFetcher.return_value = instance

        jobs = await fetch_career_page("https://example.com/careers", "example.com")

    assert len(jobs) == 2
    assert jobs[0]["title"] == "Senior React Developer"
    assert jobs[0]["source"] == "scrapling"


@pytest.mark.asyncio
async def test_fetch_career_page_no_jobs():
    mock_page = MagicMock()
    mock_page.css.return_value = []
    mock_page.url = "https://example.com/careers"

    with patch("app.ingestion.scrapling_fetcher.StealthyFetcher") as MockFetcher:
        instance = MagicMock()
        instance.fetch.return_value = mock_page
        MockFetcher.return_value = instance

        jobs = await fetch_career_page("https://example.com/careers", "example.com")

    assert jobs == []


@pytest.mark.asyncio
async def test_fetch_linkedin_jobs():
    mock_page = MagicMock()
    mock_element = MagicMock()
    mock_element.text = "Full Stack Engineer"
    mock_element.attrib = {"href": "https://www.linkedin.com/jobs/view/123"}

    mock_page.css.return_value = [mock_element]
    mock_page.url = "https://www.linkedin.com/company/stripe/jobs"

    with patch("app.ingestion.scrapling_fetcher.DynamicFetcher") as MockFetcher:
        instance = MagicMock()
        instance.fetch.return_value = mock_page
        MockFetcher.return_value = instance

        jobs = await fetch_linkedin_jobs("https://www.linkedin.com/company/stripe/jobs")

    assert len(jobs) == 1
    assert jobs[0]["title"] == "Full Stack Engineer"
    assert jobs[0]["source"] == "linkedin"


@pytest.mark.asyncio
async def test_fetch_career_page_error_returns_empty():
    with patch("app.ingestion.scrapling_fetcher.StealthyFetcher") as MockFetcher:
        instance = MagicMock()
        instance.fetch.side_effect = Exception("Connection refused")
        MockFetcher.return_value = instance

        jobs = await fetch_career_page("https://example.com/careers", "example.com")

    assert jobs == []
