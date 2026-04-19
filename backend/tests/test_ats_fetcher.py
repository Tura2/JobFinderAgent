import pytest
import httpx
from unittest.mock import AsyncMock, patch

from app.ingestion.ats_fetcher import fetch_greenhouse_jobs, fetch_lever_jobs


GREENHOUSE_RESPONSE = {
    "jobs": [
        {
            "id": 101,
            "title": "Senior Frontend Engineer",
            "absolute_url": "https://boards.greenhouse.io/vercel/jobs/101",
            "location": {"name": "Remote"},
            "content": "<p>Build amazing UIs</p>",
            "updated_at": "2026-04-10T12:00:00Z",
        },
        {
            "id": 102,
            "title": "Backend Engineer",
            "absolute_url": "https://boards.greenhouse.io/vercel/jobs/102",
            "location": {"name": "San Francisco, CA"},
            "content": "<p>Scale APIs</p>",
            "updated_at": "2026-04-11T12:00:00Z",
        },
    ]
}

LEVER_RESPONSE = [
    {
        "id": "aaa-bbb",
        "text": "Product Designer",
        "hostedUrl": "https://jobs.lever.co/figma/aaa-bbb",
        "categories": {"location": "New York, NY", "commitment": "Full-time"},
        "descriptionPlain": "Design beautiful products...",
    },
    {
        "id": "ccc-ddd",
        "text": "Data Scientist",
        "hostedUrl": "https://jobs.lever.co/figma/ccc-ddd",
        "categories": {"location": "Remote", "commitment": "Full-time"},
        "descriptionPlain": "Analyze data at scale...",
    },
]


@pytest.mark.asyncio
async def test_fetch_greenhouse_jobs():
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = GREENHOUSE_RESPONSE
    mock_response.raise_for_status = lambda: None

    with patch("app.ingestion.ats_fetcher.httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_response
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        jobs = await fetch_greenhouse_jobs("vercel")

    assert len(jobs) == 2
    assert jobs[0]["title"] == "Senior Frontend Engineer"
    assert jobs[0]["url"] == "https://boards.greenhouse.io/vercel/jobs/101"
    assert jobs[0]["location"] == "Remote"
    assert jobs[0]["description_raw"] == "<p>Build amazing UIs</p>"
    assert jobs[0]["source"] == "ats_api"


@pytest.mark.asyncio
async def test_fetch_lever_jobs():
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = LEVER_RESPONSE
    mock_response.raise_for_status = lambda: None

    with patch("app.ingestion.ats_fetcher.httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_response
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        jobs = await fetch_lever_jobs("figma")

    assert len(jobs) == 2
    assert jobs[0]["title"] == "Product Designer"
    assert jobs[0]["url"] == "https://jobs.lever.co/figma/aaa-bbb"
    assert jobs[0]["description_raw"] == "Design beautiful products..."
    assert jobs[0]["source"] == "ats_api"


@pytest.mark.asyncio
async def test_greenhouse_empty_response():
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"jobs": []}
    mock_response.raise_for_status = lambda: None

    with patch("app.ingestion.ats_fetcher.httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_response
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        jobs = await fetch_greenhouse_jobs("nonexistent")

    assert jobs == []


@pytest.mark.asyncio
async def test_greenhouse_http_error():
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not Found", request=AsyncMock(), response=mock_response
    )

    with patch("app.ingestion.ats_fetcher.httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_response
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        jobs = await fetch_greenhouse_jobs("badslug")

    assert jobs == []
