import asyncio
import json
import logging
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.pipeline.prompts import MATCHMAKER_SYSTEM_PROMPT, MATCHMAKER_USER_PROMPT

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    reraise=True,
)
async def _call_openrouter(messages: list[dict]) -> dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openrouter_model,
                "messages": messages,
                "response_format": {"type": "json_object"},
                "temperature": 0.3,
            },
        )
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 60))
            logger.warning(f"OpenRouter rate-limited — waiting {retry_after}s (Retry-After)")
            await asyncio.sleep(retry_after)
        resp.raise_for_status()
        data = resp.json()
        if "choices" not in data:
            raise httpx.RequestError(f"OpenRouter returned no choices (rate-limit?): {data.get('error', data)}")
        return data


async def score_job(
    job_title: str,
    company_name: str,
    location: str,
    description: str,
    user_profile: str,
    cv_variants_text: str,
) -> dict | None:
    user_msg = MATCHMAKER_USER_PROMPT.format(
        user_profile=user_profile,
        cv_variants=cv_variants_text,
        job_title=job_title,
        company_name=company_name,
        location=location,
        description=description,
    )

    messages = [
        {"role": "system", "content": MATCHMAKER_SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    try:
        data = await _call_openrouter(messages)
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)

        subs = parsed["scores"]
        tech     = max(0, min(30, int(subs["tech_stack"])))
        role     = max(0, min(25, int(subs["role_type"])))
        domain   = max(0, min(20, int(subs["domain"])))
        seniority = max(0, min(15, int(subs["seniority"])))
        location = max(0, min(10, int(subs["location"])))
        score = tech + role + domain + seniority + location

        breakdown = {
            "tech_stack": tech,
            "role_type": role,
            "domain": domain,
            "seniority": seniority,
            "location": location,
        }

        return {
            "score": score,
            "reasoning": str(parsed["reasoning"]),
            "cv_variant": str(parsed["cv_variant"]),
            "score_breakdown": json.dumps(breakdown),
        }

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(f"Failed to parse matchmaker response: {e}")
        return None
    except Exception as e:
        logger.error(f"Matchmaker API call failed: {e}")
        return None
