import pytest
import json
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from app.pipeline.matchmaker import score_job


def _make_response(json_data: dict) -> MagicMock:
    """Build a sync-compatible mock of httpx.Response (json() is synchronous)."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = json_data
    mock_response.raise_for_status = MagicMock(return_value=None)
    return mock_response


def _make_client(response) -> AsyncMock:
    """Build an async httpx.AsyncClient mock whose post() returns *response*."""
    client_instance = AsyncMock()
    client_instance.post = AsyncMock(return_value=response)
    client_instance.__aenter__ = AsyncMock(return_value=client_instance)
    client_instance.__aexit__ = AsyncMock(return_value=False)
    return client_instance


VALID_RESPONSE_BODY = {
    "choices": [
        {
            "message": {
                "content": json.dumps({
                    "scores": {
                        "tech_stack": 28,
                        "role_type": 22,
                        "domain": 18,
                        "seniority": 13,
                        "location": 7,
                    },
                    "reasoning": "Strong React and Node.js fit. Company builds developer tools.",
                    "cv_variant": "fullstack-automation",
                })
            }
        }
    ]
}


@pytest.mark.asyncio
async def test_score_job_high_match():
    response = _make_response(VALID_RESPONSE_BODY)
    client_instance = _make_client(response)

    with patch("app.pipeline.matchmaker.httpx.AsyncClient", return_value=client_instance):
        result = await score_job(
            job_title="Senior Frontend Engineer",
            company_name="Vercel",
            location="Remote",
            description="Build Next.js tooling...",
            user_profile="5 years React, Node.js, TypeScript...",
            cv_variants_text="frontend-focused [react, ui]\nfullstack-automation [node, deploy]",
        )

    assert result is not None
    assert result["score"] == 28 + 22 + 18 + 13 + 7  # 88
    assert result["cv_variant"] == "fullstack-automation"
    assert "reasoning" in result


@pytest.mark.asyncio
async def test_score_job_low_match():
    low_body = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "scores": {
                            "tech_stack": 5,
                            "role_type": 8,
                            "domain": 7,
                            "seniority": 4,
                            "location": 1,
                        },
                        "reasoning": "Role requires 10+ years Java enterprise experience.",
                        "cv_variant": "fullstack-automation",
                    })
                }
            }
        ]
    }
    response = _make_response(low_body)
    client_instance = _make_client(response)

    with patch("app.pipeline.matchmaker.httpx.AsyncClient", return_value=client_instance):
        result = await score_job(
            job_title="Principal Java Architect",
            company_name="Oracle",
            location="Austin, TX",
            description="10+ years Java EE, Spring Boot...",
            user_profile="5 years React, Node.js...",
            cv_variants_text="frontend-focused [react]\nfullstack-automation [node]",
        )

    assert result is not None
    assert result["score"] == 5 + 8 + 7 + 4 + 1  # 25


@pytest.mark.asyncio
async def test_score_job_api_error_retries_then_returns_none():
    client_instance = AsyncMock()
    client_instance.post = AsyncMock(side_effect=httpx.RequestError("network down"))
    client_instance.__aenter__ = AsyncMock(return_value=client_instance)
    client_instance.__aexit__ = AsyncMock(return_value=False)

    with patch("app.pipeline.matchmaker.httpx.AsyncClient", return_value=client_instance), \
         patch("tenacity.nap.time"):
        result = await score_job(
            job_title="Dev",
            company_name="Co",
            location="",
            description="...",
            user_profile="...",
            cv_variants_text="v1 [tag]",
        )

    assert result is None
    assert client_instance.post.call_count == 3  # 3 total attempts (1 initial + 2 retries)


@pytest.mark.asyncio
async def test_score_job_rate_limited_200_no_choices_retries_then_returns_none():
    """OpenRouter returns HTTP 200 with no 'choices' key (rate-limit envelope).
    tenacity should retry 3 times then score_job should return None."""
    response = _make_response({"error": {"message": "rate limited"}})
    client_instance = _make_client(response)

    # Patch wait so tenacity doesn't actually sleep between retries
    with patch("app.pipeline.matchmaker.httpx.AsyncClient", return_value=client_instance), \
         patch("tenacity.nap.time"):
        result = await score_job(
            job_title="Dev",
            company_name="Co",
            location="",
            description="...",
            user_profile="...",
            cv_variants_text="v1 [tag]",
        )

    assert result is None
    # 3 total attempts (1 initial + 2 retries)
    assert client_instance.post.call_count == 3


@pytest.mark.asyncio
async def test_score_job_invalid_json_returns_none():
    response = _make_response({
        "choices": [{"message": {"content": "I cannot evaluate this job."}}]
    })
    client_instance = _make_client(response)

    with patch("app.pipeline.matchmaker.httpx.AsyncClient", return_value=client_instance):
        result = await score_job(
            job_title="Dev",
            company_name="Co",
            location="",
            description="...",
            user_profile="...",
            cv_variants_text="v1 [tag]",
        )

    assert result is None
