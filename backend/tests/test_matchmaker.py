import pytest
import json
from unittest.mock import AsyncMock, patch

from app.pipeline.matchmaker import score_job


@pytest.mark.asyncio
async def test_score_job_high_match():
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "score": 88,
                        "reasoning": "Strong React and Node.js fit. Company builds developer tools.",
                        "cv_variant": "fullstack-automation",
                    })
                }
            }
        ]
    }
    mock_response.raise_for_status = lambda: None

    with patch("app.pipeline.matchmaker.httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.post.return_value = mock_response
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        result = await score_job(
            job_title="Senior Frontend Engineer",
            company_name="Vercel",
            location="Remote",
            description="Build Next.js tooling...",
            user_profile="5 years React, Node.js, TypeScript...",
            cv_variants_text="frontend-focused [react, ui]\nfullstack-automation [node, deploy]",
        )

    assert result["score"] == 88
    assert result["cv_variant"] == "fullstack-automation"
    assert "reasoning" in result


@pytest.mark.asyncio
async def test_score_job_low_match():
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "score": 25,
                        "reasoning": "Role requires 10+ years Java enterprise experience.",
                        "cv_variant": "fullstack-automation",
                    })
                }
            }
        ]
    }
    mock_response.raise_for_status = lambda: None

    with patch("app.pipeline.matchmaker.httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.post.return_value = mock_response
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        result = await score_job(
            job_title="Principal Java Architect",
            company_name="Oracle",
            location="Austin, TX",
            description="10+ years Java EE, Spring Boot...",
            user_profile="5 years React, Node.js...",
            cv_variants_text="frontend-focused [react]\nfullstack-automation [node]",
        )

    assert result["score"] == 25


@pytest.mark.asyncio
async def test_score_job_api_error_retries_then_returns_none():
    with patch("app.pipeline.matchmaker.httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.post.side_effect = Exception("API down")
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        result = await score_job(
            job_title="Dev",
            company_name="Co",
            location="",
            description="...",
            user_profile="...",
            cv_variants_text="v1 [tag]",
        )

    assert result is None


@pytest.mark.asyncio
async def test_score_job_invalid_json_returns_none():
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "I cannot evaluate this job."}}]
    }
    mock_response.raise_for_status = lambda: None

    with patch("app.pipeline.matchmaker.httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.post.return_value = mock_response
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        result = await score_job(
            job_title="Dev",
            company_name="Co",
            location="",
            description="...",
            user_profile="...",
            cv_variants_text="v1 [tag]",
        )

    assert result is None
