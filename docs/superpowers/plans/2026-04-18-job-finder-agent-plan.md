# JobFinderAgent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone autonomous job hunting pipeline on Oracle Ubuntu VM — scrapes target companies, scores jobs via OpenRouter, selects a tailored CV, and notifies the user via Telegram with a mobile PWA for one-tap review and apply.

**Architecture:** Python/FastAPI backend with SQLite (SQLModel), APScheduler for scheduled scans, Scrapling for adaptive scraping, OpenRouter for AI matching, and python-telegram-bot for notifications. TypeScript/React (Vite) mobile PWA served as static files from the same FastAPI process. Deployed as a systemd service on Oracle Ubuntu VM.

**Tech Stack:** Python 3.12, FastAPI, SQLModel, APScheduler, Scrapling, httpx + tenacity, python-telegram-bot, TypeScript, React 18, Vite, Tailwind CSS, Vitest + React Testing Library

---

Below is the full task-by-task plan across all 7 phases. Every task follows strict Red-Green-Refactor: write the failing test first, then the implementation, then verify.

---

## Phase 1: Scaffold + Config + Database (Tasks 1-3)

### Task 1 -- Project Scaffold and Dependencies

**Files to create:**
- `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\pyproject.toml`
- `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\requirements.txt`
- `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\.env.example`
- `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\__init__.py`
- `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\models\__init__.py`
- `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\ingestion\__init__.py`
- `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\pipeline\__init__.py`
- `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\notifications\__init__.py`
- `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\routers\__init__.py`
- `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\tests\__init__.py`
- `C:\Users\offir\Desktop\Projects\JobFinderAgent\.gitignore`

**pyproject.toml:**
```toml
[build-system]
requires = ["setuptools>=65.0"]
build-backend = "setuptools.build_meta"

[project]
name = "jobfinder-backend"
version = "0.1.0"
description = "Autonomous Job Hunting Agent - Backend"
requires-python = ">=3.12"

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "ruff>=0.9.0",
]

[tool.ruff]
line-length = 100
target-version = "py312"
select = ["E", "F", "W", "I"]
ignore = ["E501"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = "test_*.py"
addopts = "--cov=app --cov-report=term-missing"
```

**requirements.txt:**
```
# Web Framework
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
pydantic>=2.9.0
pydantic-settings>=2.5.0

# Database
sqlmodel>=0.0.22
aiosqlite>=0.20.0

# Scraping
scrapling>=0.2.0

# HTTP + LLM
httpx>=0.27.0
tenacity>=9.0.0

# Scheduler
apscheduler>=3.10.0

# Telegram
python-telegram-bot>=21.0

# Testing
pytest>=8.0.0
pytest-asyncio>=0.24.0
pytest-cov>=6.0.0
ruff>=0.9.0
```

**.env.example:**
```
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=anthropic/claude-opus-4.5
MATCH_THRESHOLD=65
SCAN_INTERVAL_HOURS=4
TELEGRAM_BOT_TOKEN=123456:ABC-DEF
TELEGRAM_CHAT_ID=123456789
PWA_ACCESS_TOKEN=changeme
PWA_BASE_URL=http://localhost:8000
DATABASE_URL=sqlite:///./jobfinder.db
```

**.gitignore:**
```
__pycache__/
*.pyc
.env
*.db
venv/
.venv/
.pytest_cache/
htmlcov/
.coverage
node_modules/
dist/
```

All `__init__.py` files are empty.

**Run command:**
```bash
cd backend && pip install -r requirements.txt && python -c "import fastapi; import sqlmodel; print('OK')"
```

**Commit:** `chore: scaffold project structure and dependencies`

---

### Task 2 -- Config Module

**Failing test first.**

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\tests\test_config.py`
```python
"""Tests for application configuration."""

import os
import pytest


def test_settings_loads_defaults():
    """Settings should provide sane defaults without .env."""
    from app.config import Settings

    s = Settings(
        OPENROUTER_API_KEY="test-key",
        TELEGRAM_BOT_TOKEN="test-bot",
        TELEGRAM_CHAT_ID="12345",
        PWA_ACCESS_TOKEN="test-token",
    )
    assert s.openrouter_model == "anthropic/claude-opus-4.5"
    assert s.match_threshold == 65
    assert s.scan_interval_hours == 4
    assert s.database_url == "sqlite:///./jobfinder.db"
    assert s.pwa_base_url == "http://localhost:8000"


def test_settings_overrides_from_env(monkeypatch):
    """Settings should read from environment variables."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o")
    monkeypatch.setenv("MATCH_THRESHOLD", "80")
    monkeypatch.setenv("SCAN_INTERVAL_HOURS", "2")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "999")
    monkeypatch.setenv("PWA_ACCESS_TOKEN", "tok123")
    monkeypatch.setenv("PWA_BASE_URL", "http://myvm:8000")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")

    from app.config import Settings

    s = Settings()
    assert s.openrouter_api_key == "sk-test"
    assert s.openrouter_model == "openai/gpt-4o"
    assert s.match_threshold == 80
    assert s.scan_interval_hours == 2
    assert s.telegram_bot_token == "bot-tok"
    assert s.telegram_chat_id == "999"
    assert s.pwa_access_token == "tok123"
    assert s.pwa_base_url == "http://myvm:8000"
    assert s.database_url == "sqlite:///./test.db"


def test_match_threshold_bounds():
    """Threshold must be 0-100."""
    from app.config import Settings

    with pytest.raises(Exception):
        Settings(
            OPENROUTER_API_KEY="k",
            TELEGRAM_BOT_TOKEN="t",
            TELEGRAM_CHAT_ID="1",
            PWA_ACCESS_TOKEN="t",
            MATCH_THRESHOLD=150,
        )
```

**Run (RED):**
```bash
cd backend && python -m pytest tests/test_config.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.config'`

**Implementation.**

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\config.py`
```python
"""Application configuration from environment variables."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM
    openrouter_api_key: str
    openrouter_model: str = "anthropic/claude-opus-4.5"

    # Pipeline
    match_threshold: int = 65
    scan_interval_hours: int = 4

    # Telegram
    telegram_bot_token: str
    telegram_chat_id: str

    # App
    pwa_access_token: str
    pwa_base_url: str = "http://localhost:8000"

    # Database
    database_url: str = "sqlite:///./jobfinder.db"

    @field_validator("match_threshold")
    @classmethod
    def threshold_in_range(cls, v: int) -> int:
        if not 0 <= v <= 100:
            raise ValueError("match_threshold must be between 0 and 100")
        return v


settings = Settings()
```

**Run (GREEN):**
```bash
cd backend && python -m pytest tests/test_config.py -v
```
Expected: 3 passed.

**Commit:** `feat: add config module with pydantic-settings`

---

### Task 3 -- Database + All SQLModels

**Failing test first.**

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\tests\conftest.py`
```python
"""Shared test fixtures."""

import pytest
from sqlmodel import SQLModel, Session, create_engine


@pytest.fixture(name="db")
def db_session():
    """In-memory SQLite session for tests."""
    engine = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
```

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\tests\test_models.py`
```python
"""Tests for SQLModel data models."""

import pytest
from datetime import datetime, timezone
from sqlmodel import Session, select

from app.models.company import Company
from app.models.job import Job
from app.models.match import Match
from app.models.cv_variant import CVVariant
from app.models.application import Application


def test_create_company(db: Session):
    company = Company(
        name="Vercel",
        website="https://vercel.com",
        ats_type="greenhouse",
        ats_slug="vercel",
        active=True,
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    assert company.id is not None
    assert company.name == "Vercel"
    assert company.ats_type == "greenhouse"
    assert company.active is True
    assert company.added_at is not None


def test_create_job_with_company(db: Session):
    company = Company(name="Stripe", ats_type="greenhouse", ats_slug="stripe")
    db.add(company)
    db.commit()
    db.refresh(company)

    job = Job(
        company_id=company.id,
        title="Senior Frontend Engineer",
        url="https://boards.greenhouse.io/stripe/jobs/123",
        description_raw="Build payment UIs...",
        location="San Francisco, CA",
        remote=True,
        source="ats_api",
        content_hash="abc123hash",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    assert job.id is not None
    assert job.company_id == company.id
    assert job.content_hash == "abc123hash"


def test_content_hash_unique(db: Session):
    company = Company(name="Co", ats_type="custom")
    db.add(company)
    db.commit()
    db.refresh(company)

    job1 = Job(
        company_id=company.id,
        title="Dev",
        url="http://x.com/1",
        source="ats_api",
        content_hash="samehash",
    )
    db.add(job1)
    db.commit()

    job2 = Job(
        company_id=company.id,
        title="Dev2",
        url="http://x.com/2",
        source="ats_api",
        content_hash="samehash",
    )
    db.add(job2)
    with pytest.raises(Exception):  # IntegrityError
        db.commit()


def test_create_cv_variant(db: Session):
    cv = CVVariant(
        name="frontend-focused",
        file_path="/cvs/frontend.pdf",
        focus_tags='["react","ui","design-systems"]',
        is_active=True,
    )
    db.add(cv)
    db.commit()
    db.refresh(cv)

    assert cv.id is not None
    assert cv.name == "frontend-focused"
    assert cv.is_active is True


def test_create_match(db: Session):
    company = Company(name="Co", ats_type="lever", ats_slug="co")
    db.add(company)
    db.commit()
    db.refresh(company)

    job = Job(
        company_id=company.id,
        title="Dev",
        url="http://x.com",
        source="ats_api",
        content_hash="h1",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    cv = CVVariant(name="general", file_path="/cv.pdf", focus_tags="[]", is_active=True)
    db.add(cv)
    db.commit()
    db.refresh(cv)

    match = Match(
        job_id=job.id,
        score=85,
        reasoning="Strong React + Node fit.",
        cv_variant_id=cv.id,
        status="new",
    )
    db.add(match)
    db.commit()
    db.refresh(match)

    assert match.id is not None
    assert match.score == 85
    assert match.status == "new"
    assert match.matched_at is not None


def test_create_application(db: Session):
    company = Company(name="Co", ats_type="custom")
    db.add(company)
    db.commit()
    db.refresh(company)

    job = Job(company_id=company.id, title="Dev", url="http://x.com", source="ats_api", content_hash="h2")
    db.add(job)
    db.commit()
    db.refresh(job)

    cv = CVVariant(name="v1", file_path="/cv.pdf", focus_tags="[]", is_active=True)
    db.add(cv)
    db.commit()
    db.refresh(cv)

    match = Match(job_id=job.id, score=90, reasoning="Great", cv_variant_id=cv.id, status="applied")
    db.add(match)
    db.commit()
    db.refresh(match)

    app = Application(
        match_id=match.id,
        cv_variant_id=cv.id,
        ats_url="https://boards.greenhouse.io/apply/123",
        outcome_status="pending",
    )
    db.add(app)
    db.commit()
    db.refresh(app)

    assert app.id is not None
    assert app.outcome_status == "pending"
    assert app.applied_at is not None
```

**Run (RED):**
```bash
cd backend && python -m pytest tests/test_models.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.models.company'`

**Implementation.**

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\models\company.py`
```python
"""Company model — the watchlist."""

from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class Company(SQLModel, table=True):
    __tablename__ = "companies"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    website: Optional[str] = None
    ats_type: str  # greenhouse | lever | workday | custom | linkedin
    ats_slug: Optional[str] = None
    linkedin_url: Optional[str] = None
    career_page_url: Optional[str] = None
    active: bool = True
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\models\job.py`
```python
"""Job model — every job ever seen."""

from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id")
    title: str
    url: str
    description_raw: Optional[str] = None
    location: Optional[str] = None
    remote: Optional[bool] = None
    source: str  # ats_api | scrapling | linkedin
    content_hash: str = Field(unique=True)
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\models\cv_variant.py`
```python
"""CV Variant model."""

from typing import Optional
from sqlmodel import SQLModel, Field


class CVVariant(SQLModel, table=True):
    __tablename__ = "cv_variants"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    file_path: str
    focus_tags: str = "[]"  # JSON array stored as text
    is_active: bool = True
```

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\models\match.py`
```python
"""Match model — jobs that entered the pipeline."""

from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class Match(SQLModel, table=True):
    __tablename__ = "matches"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="jobs.id")
    score: int
    reasoning: str
    cv_variant_id: Optional[int] = Field(default=None, foreign_key="cv_variants.id")
    status: str = "new"  # low_match|new|reviewed|skipped|applied|rejected|no_response|interview|offer
    matched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: Optional[datetime] = None
```

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\models\application.py`
```python
"""Application model — created on Apply tap."""

from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class Application(SQLModel, table=True):
    __tablename__ = "applications"

    id: Optional[int] = Field(default=None, primary_key=True)
    match_id: int = Field(foreign_key="matches.id")
    cv_variant_id: int = Field(foreign_key="cv_variants.id")
    ats_url: Optional[str] = None
    applied_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_at: Optional[datetime] = None
    notes: Optional[str] = None
    outcome_status: str = "pending"  # pending | interview | offer | rejected
    last_status_update: Optional[datetime] = None
```

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\models\__init__.py`
```python
"""Models package — import all models so SQLModel.metadata knows about them."""

from app.models.company import Company
from app.models.job import Job
from app.models.match import Match
from app.models.cv_variant import CVVariant
from app.models.application import Application

__all__ = ["Company", "Job", "Match", "CVVariant", "Application"]
```

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\database.py`
```python
"""SQLite engine and session management."""

from sqlmodel import SQLModel, Session, create_engine
from app.config import settings

engine = create_engine(settings.database_url, echo=False)


def create_db_and_tables():
    import app.models  # noqa: F401 — ensure all models are registered
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
```

**Update conftest.py** to import all models so metadata is populated:

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\tests\conftest.py` (updated)
```python
"""Shared test fixtures."""

import pytest
from sqlmodel import SQLModel, Session, create_engine

import app.models  # noqa: F401 — register all models with metadata


@pytest.fixture(name="db")
def db_session():
    """In-memory SQLite session for tests."""
    engine = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
```

**Run (GREEN):**
```bash
cd backend && python -m pytest tests/test_models.py -v
```
Expected: 6 passed.

**Commit:** `feat: add database module and all SQLModel models`

---

## Phase 2: Ingestion Engine (Tasks 4-6)

### Task 4 -- ATS Fetcher (Greenhouse + Lever)

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\tests\test_ats_fetcher.py`
```python
"""Tests for Greenhouse and Lever ATS fetchers."""

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
```

**Run (RED):**
```bash
cd backend && python -m pytest tests/test_ats_fetcher.py -v
```

**Implementation.**

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\ingestion\ats_fetcher.py`
```python
"""Fetchers for Greenhouse and Lever ATS APIs."""

import httpx
import logging

logger = logging.getLogger(__name__)


async def fetch_greenhouse_jobs(slug: str) -> list[dict]:
    """Fetch all jobs from a Greenhouse board."""
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
    """Fetch all postings from a Lever board."""
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
```

**Run (GREEN):**
```bash
cd backend && python -m pytest tests/test_ats_fetcher.py -v
```
Expected: 4 passed.

**Commit:** `feat: add ATS fetcher for Greenhouse and Lever APIs`

---

### Task 5 -- Scrapling Fetcher

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\tests\test_scrapling_fetcher.py`
```python
"""Tests for Scrapling-based fetchers (Workday, custom, LinkedIn)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.ingestion.scrapling_fetcher import fetch_career_page, fetch_linkedin_jobs


@pytest.mark.asyncio
async def test_fetch_career_page():
    """Scrapling StealthyFetcher extracts job listings from a career page."""
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
    """Empty page returns empty list."""
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
    """DynamicFetcher extracts jobs from LinkedIn company page."""
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
    """Network error returns empty list instead of crashing."""
    with patch("app.ingestion.scrapling_fetcher.StealthyFetcher") as MockFetcher:
        instance = MagicMock()
        instance.fetch.side_effect = Exception("Connection refused")
        MockFetcher.return_value = instance

        jobs = await fetch_career_page("https://example.com/careers", "example.com")

    assert jobs == []
```

**Run (RED):**
```bash
cd backend && python -m pytest tests/test_scrapling_fetcher.py -v
```

**Implementation.**

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\ingestion\scrapling_fetcher.py`
```python
"""Scrapling-based fetchers for Workday, custom career pages, and LinkedIn."""

import logging
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

# Lazy imports to avoid import errors in test environments without browsers
StealthyFetcher = None
DynamicFetcher = None


def _load_scrapling():
    global StealthyFetcher, DynamicFetcher
    if StealthyFetcher is None:
        from scrapling import StealthyFetcher as SF, DynamicFetcher as DF
        StealthyFetcher = SF
        DynamicFetcher = DF


# Common CSS selectors for job listing links across career page designs
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
    """Scrape a career page using StealthyFetcher. Returns list of raw job dicts."""
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
    """Scrape LinkedIn company jobs page using DynamicFetcher (Playwright + stealth)."""
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
```

**Run (GREEN):**
```bash
cd backend && python -m pytest tests/test_scrapling_fetcher.py -v
```
Expected: 4 passed.

**Commit:** `feat: add Scrapling fetcher for career pages and LinkedIn`

---

### Task 6 -- Normalizer (dedup + unified schema)

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\tests\test_normalizer.py`
```python
"""Tests for the normalizer — raw dicts → Job models with dedup."""

import pytest
from sqlmodel import Session, select

from app.models.company import Company
from app.models.job import Job
from app.ingestion.normalizer import normalize_and_deduplicate


def test_normalize_new_jobs(db: Session):
    company = Company(name="Vercel", ats_type="greenhouse", ats_slug="vercel")
    db.add(company)
    db.commit()
    db.refresh(company)

    raw_jobs = [
        {
            "title": "Frontend Engineer",
            "url": "https://boards.greenhouse.io/vercel/jobs/1",
            "description_raw": "Build UIs",
            "location": "Remote",
            "source": "ats_api",
        },
        {
            "title": "Backend Engineer",
            "url": "https://boards.greenhouse.io/vercel/jobs/2",
            "description_raw": "Scale APIs",
            "location": "SF",
            "source": "ats_api",
        },
    ]

    new_jobs = normalize_and_deduplicate(raw_jobs, company.id, db)

    assert len(new_jobs) == 2
    assert new_jobs[0].title == "Frontend Engineer"
    assert new_jobs[0].company_id == company.id
    assert new_jobs[0].content_hash is not None

    # Verify persisted
    all_jobs = db.exec(select(Job)).all()
    assert len(all_jobs) == 2


def test_normalize_deduplicates(db: Session):
    company = Company(name="Stripe", ats_type="lever", ats_slug="stripe")
    db.add(company)
    db.commit()
    db.refresh(company)

    raw_jobs = [
        {"title": "Dev", "url": "http://x.com/1", "description_raw": "", "location": "", "source": "ats_api"},
    ]

    first_pass = normalize_and_deduplicate(raw_jobs, company.id, db)
    assert len(first_pass) == 1

    # Same job again → should be skipped
    second_pass = normalize_and_deduplicate(raw_jobs, company.id, db)
    assert len(second_pass) == 0

    # Only 1 total in DB
    all_jobs = db.exec(select(Job)).all()
    assert len(all_jobs) == 1


def test_normalize_handles_remote_detection(db: Session):
    company = Company(name="Co", ats_type="custom")
    db.add(company)
    db.commit()
    db.refresh(company)

    raw = [
        {"title": "Dev", "url": "http://x.com", "description_raw": "", "location": "Remote - US", "source": "ats_api"},
    ]

    jobs = normalize_and_deduplicate(raw, company.id, db)
    assert jobs[0].remote is True


def test_normalize_strips_html(db: Session):
    company = Company(name="Co", ats_type="custom")
    db.add(company)
    db.commit()
    db.refresh(company)

    raw = [
        {
            "title": "Dev",
            "url": "http://x.com",
            "description_raw": "<p>Hello <b>world</b></p>",
            "location": "",
            "source": "ats_api",
        },
    ]

    jobs = normalize_and_deduplicate(raw, company.id, db)
    # description_raw is stored as-is (raw), but content_hash should be stable
    assert jobs[0].description_raw == "<p>Hello <b>world</b></p>"
```

**Run (RED):**
```bash
cd backend && python -m pytest tests/test_normalizer.py -v
```

**Implementation.**

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\ingestion\normalizer.py`
```python
"""Normalize raw job dicts into Job models and deduplicate by content_hash."""

import hashlib
import logging
from sqlmodel import Session, select

from app.models.job import Job

logger = logging.getLogger(__name__)


def compute_content_hash(company_id: int, title: str, url: str) -> str:
    """SHA-256 hash of company_id + title + url for dedup."""
    raw = f"{company_id}:{title}:{url}"
    return hashlib.sha256(raw.encode()).hexdigest()


def detect_remote(location: str, description: str) -> bool:
    """Simple heuristic: check if 'remote' appears in location or description."""
    text = f"{location} {description}".lower()
    return "remote" in text


def normalize_and_deduplicate(
    raw_jobs: list[dict],
    company_id: int,
    session: Session,
) -> list[Job]:
    """Convert raw dicts to Job models, skip duplicates, persist new ones."""
    new_jobs = []

    for raw in raw_jobs:
        title = raw.get("title", "").strip()
        url = raw.get("url", "").strip()
        if not title or not url:
            logger.debug(f"Skipping job with missing title or url: {raw}")
            continue

        content_hash = compute_content_hash(company_id, title, url)

        # Check if already exists
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
```

**Run (GREEN):**
```bash
cd backend && python -m pytest tests/test_normalizer.py -v
```
Expected: 4 passed.

**Commit:** `feat: add normalizer with content_hash dedup`

---

## Phase 3: AI Pipeline (Tasks 7-9)

### Task 7 -- Prompts Module

**No separate test file needed -- prompts are pure string templates tested through the matchmaker tests. But let's define it.**

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\pipeline\prompts.py`
```python
"""LLM prompt templates for the matching pipeline."""

MATCHMAKER_SYSTEM_PROMPT = """You are a job matching assistant. You evaluate how well a job posting matches a candidate's profile.

You MUST respond with valid JSON in this exact format:
{
  "score": <integer 0-100>,
  "reasoning": "<2-3 sentence explanation>",
  "cv_variant": "<name of the best CV variant>"
}

Scoring guidelines:
- 90-100: Near-perfect match — role aligns with core skills, experience level, and interests
- 75-89: Strong match — most key requirements met, minor gaps
- 60-74: Moderate match — some relevant skills, notable gaps
- 40-59: Weak match — few overlapping skills
- 0-39: Poor match — fundamentally different domain or seniority"""

MATCHMAKER_USER_PROMPT = """## Candidate Profile
{user_profile}

## Available CV Variants
{cv_variants}

## Job Posting
**Title:** {job_title}
**Company:** {company_name}
**Location:** {location}
**Description:**
{description}

Evaluate the match and respond with JSON only."""
```

**Commit:** `feat: add LLM prompt templates`

---

### Task 8 -- Matchmaker (OpenRouter scoring)

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\tests\test_matchmaker.py`
```python
"""Tests for the AI matchmaker — OpenRouter scoring."""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

from app.pipeline.matchmaker import score_job


@pytest.mark.asyncio
async def test_score_job_high_match():
    """Job that matches the profile should get a high score."""
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
    """On repeated API failure, return None instead of crashing."""
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
    """If LLM returns non-JSON, return None."""
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
```

**Run (RED):**
```bash
cd backend && python -m pytest tests/test_matchmaker.py -v
```

**Implementation.**

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\pipeline\matchmaker.py`
```python
"""AI Matchmaker — scores jobs against user profile via OpenRouter."""

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
    """Make a single OpenRouter API call with retry."""
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
        resp.raise_for_status()
        return resp.json()


async def score_job(
    job_title: str,
    company_name: str,
    location: str,
    description: str,
    user_profile: str,
    cv_variants_text: str,
) -> dict | None:
    """Score a job against the user profile. Returns {score, reasoning, cv_variant} or None on failure."""
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

        # Validate expected fields
        score = int(parsed["score"])
        reasoning = str(parsed["reasoning"])
        cv_variant = str(parsed["cv_variant"])

        return {
            "score": max(0, min(100, score)),
            "reasoning": reasoning,
            "cv_variant": cv_variant,
        }

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(f"Failed to parse matchmaker response: {e}")
        return None
    except Exception as e:
        logger.error(f"Matchmaker API call failed: {e}")
        return None
```

**Run (GREEN):**
```bash
cd backend && python -m pytest tests/test_matchmaker.py -v
```
Expected: 4 passed.

**Commit:** `feat: add AI matchmaker with OpenRouter integration`

---

### Task 9 -- CV Selector

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\tests\test_cv_selector.py`
```python
"""Tests for CV variant selection logic."""

import pytest
import json
from sqlmodel import Session

from app.models.cv_variant import CVVariant
from app.pipeline.cv_selector import select_cv_variant


def _seed_variants(db: Session) -> list[CVVariant]:
    variants = [
        CVVariant(
            name="frontend-focused",
            file_path="/cv/frontend.pdf",
            focus_tags=json.dumps(["react", "ui", "design-systems", "css"]),
            is_active=True,
        ),
        CVVariant(
            name="fullstack-automation",
            file_path="/cv/fullstack.pdf",
            focus_tags=json.dumps(["node", "deploy", "electron", "automation"]),
            is_active=True,
        ),
        CVVariant(
            name="ai-builder",
            file_path="/cv/ai.pdf",
            focus_tags=json.dumps(["llm", "openai", "langchain", "automation"]),
            is_active=True,
        ),
    ]
    for v in variants:
        db.add(v)
    db.commit()
    for v in variants:
        db.refresh(v)
    return variants


def test_select_by_exact_name(db: Session):
    variants = _seed_variants(db)
    result = select_cv_variant("frontend-focused", variants)
    assert len(result) == 1
    assert result[0].name == "frontend-focused"


def test_select_by_name_case_insensitive(db: Session):
    variants = _seed_variants(db)
    result = select_cv_variant("Frontend-Focused", variants)
    assert len(result) == 1
    assert result[0].name == "frontend-focused"


def test_fallback_to_tag_matching(db: Session):
    variants = _seed_variants(db)
    # Name doesn't match any variant — fall back to tag matching
    result = select_cv_variant("react-specialist", variants)
    # Should match "frontend-focused" since "react" is in its tags
    assert len(result) >= 1
    assert any(v.name == "frontend-focused" for v in result)


def test_ambiguous_returns_multiple(db: Session):
    """When two variants tie on tag overlap, return both."""
    variants = _seed_variants(db)
    # "automation" is in both fullstack-automation and ai-builder
    result = select_cv_variant("automation-expert", variants)
    assert len(result) == 2
    names = {v.name for v in result}
    assert "fullstack-automation" in names
    assert "ai-builder" in names


def test_no_match_returns_first_active(db: Session):
    variants = _seed_variants(db)
    result = select_cv_variant("completely-unrelated-xyz", variants)
    # Falls back to first active variant
    assert len(result) == 1


def test_empty_variants_returns_empty(db: Session):
    result = select_cv_variant("anything", [])
    assert result == []
```

**Run (RED):**
```bash
cd backend && python -m pytest tests/test_cv_selector.py -v
```

**Implementation.**

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\pipeline\cv_selector.py`
```python
"""CV Variant selector — picks the best variant based on matchmaker recommendation."""

import json
import logging
from app.models.cv_variant import CVVariant

logger = logging.getLogger(__name__)


def _extract_keywords(name: str) -> set[str]:
    """Split a variant name or recommendation into lowercase keywords."""
    return {w.lower().strip() for w in name.replace("-", " ").replace("_", " ").split() if w.strip()}


def select_cv_variant(
    recommended_name: str,
    active_variants: list[CVVariant],
) -> list[CVVariant]:
    """Select best CV variant(s) by name match, then tag overlap fallback.

    Returns:
        List of 1 variant (clear winner) or 2 variants (ambiguous tie).
        Empty list if no active variants exist.
    """
    if not active_variants:
        return []

    # 1. Exact name match (case-insensitive)
    for v in active_variants:
        if v.name.lower() == recommended_name.lower():
            return [v]

    # 2. Fallback: score by tag overlap with keywords in the recommended name
    keywords = _extract_keywords(recommended_name)

    scored: list[tuple[int, CVVariant]] = []
    for v in active_variants:
        try:
            tags = set(json.loads(v.focus_tags))
        except (json.JSONDecodeError, TypeError):
            tags = set()
        overlap = len(keywords & {t.lower() for t in tags})
        scored.append((overlap, v))

    scored.sort(key=lambda x: x[0], reverse=True)

    if not scored:
        return []

    best_score = scored[0][0]

    if best_score == 0:
        # No tag overlap at all — return first active as default
        return [active_variants[0]]

    # Check for tie (ambiguous)
    tied = [v for score, v in scored if score == best_score]
    if len(tied) >= 2:
        return tied[:2]  # Return top 2 for user to choose

    return [scored[0][1]]
```

**Run (GREEN):**
```bash
cd backend && python -m pytest tests/test_cv_selector.py -v
```
Expected: 6 passed.

**Commit:** `feat: add CV variant selector with tag-based fallback`

---

## Phase 4: Notifications + Scheduler (Tasks 10-11)

### Task 10 -- Telegram Notifications

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\tests\test_telegram.py`
```python
"""Tests for Telegram notification sender."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.notifications.telegram import send_match_notification, format_match_message


def test_format_match_message():
    msg = format_match_message(
        company_name="Vercel",
        job_title="Senior Frontend Engineer",
        score=88,
        reasoning="Strong React fit. Company builds developer tools.",
        match_id=42,
        pwa_base_url="http://myvm:8000",
    )

    assert "Vercel" in msg
    assert "88%" in msg
    assert "Senior Frontend Engineer" in msg
    assert "Strong React fit" in msg
    assert "http://myvm:8000/matches/42" in msg


def test_format_match_message_special_characters():
    """Telegram MarkdownV2 special chars should be escaped."""
    msg = format_match_message(
        company_name="AT&T",
        job_title="C++ Developer (Senior)",
        score=72,
        reasoning="Good C++ skills. Some gaps in telecom.",
        match_id=1,
        pwa_base_url="http://vm:8000",
    )
    # Should not crash and should contain company name
    assert "AT" in msg
    assert "72%" in msg


@pytest.mark.asyncio
async def test_send_match_notification():
    with patch("app.notifications.telegram.Bot") as MockBot:
        bot_instance = AsyncMock()
        MockBot.return_value = bot_instance

        await send_match_notification(
            company_name="Stripe",
            job_title="Backend Engineer",
            score=91,
            reasoning="Perfect match for backend skills.",
            match_id=7,
        )

        bot_instance.send_message.assert_awaited_once()
        call_kwargs = bot_instance.send_message.call_args
        assert "Stripe" in str(call_kwargs)


@pytest.mark.asyncio
async def test_send_notification_failure_does_not_crash():
    with patch("app.notifications.telegram.Bot") as MockBot:
        bot_instance = AsyncMock()
        bot_instance.send_message.side_effect = Exception("Telegram API error")
        MockBot.return_value = bot_instance

        # Should not raise
        await send_match_notification(
            company_name="Co",
            job_title="Dev",
            score=80,
            reasoning="Good",
            match_id=1,
        )
```

**Run (RED):**
```bash
cd backend && python -m pytest tests/test_telegram.py -v
```

**Implementation.**

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\notifications\telegram.py`
```python
"""Telegram bot notifications for new job matches."""

import logging
from telegram import Bot

from app.config import settings

logger = logging.getLogger(__name__)


def format_match_message(
    company_name: str,
    job_title: str,
    score: int,
    reasoning: str,
    match_id: int,
    pwa_base_url: str,
) -> str:
    """Format a match notification message for Telegram."""
    link = f"{pwa_base_url}/matches/{match_id}"
    return (
        f"\U0001f3af Match at {company_name} \u00b7 {score}%\n"
        f"{job_title}\n\n"
        f"{reasoning}\n\n"
        f"\U0001f517 {link}"
    )


async def send_match_notification(
    company_name: str,
    job_title: str,
    score: int,
    reasoning: str,
    match_id: int,
) -> None:
    """Send a Telegram notification for a new match."""
    try:
        bot = Bot(token=settings.telegram_bot_token)
        message = format_match_message(
            company_name=company_name,
            job_title=job_title,
            score=score,
            reasoning=reasoning,
            match_id=match_id,
            pwa_base_url=settings.pwa_base_url,
        )
        await bot.send_message(
            chat_id=settings.telegram_chat_id,
            text=message,
        )
        logger.info(f"Telegram notification sent for match {match_id}")
    except Exception as e:
        logger.error(f"Failed to send Telegram notification for match {match_id}: {e}")
```

**Run (GREEN):**
```bash
cd backend && python -m pytest tests/test_telegram.py -v
```
Expected: 4 passed.

**Commit:** `feat: add Telegram notification sender`

---

### Task 11 -- Scheduler + Scan Orchestrator

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\tests\test_scheduler.py`
```python
"""Tests for the scan orchestrator and scheduler setup."""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from sqlmodel import Session

from app.models.company import Company
from app.models.cv_variant import CVVariant
from app.scheduler import run_scan_for_company, get_active_companies


def _seed_company(db: Session, **kwargs) -> Company:
    defaults = {"name": "TestCo", "ats_type": "greenhouse", "ats_slug": "testco", "active": True}
    defaults.update(kwargs)
    c = Company(**defaults)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _seed_cv(db: Session) -> CVVariant:
    cv = CVVariant(
        name="fullstack-automation",
        file_path="/cv/fs.pdf",
        focus_tags=json.dumps(["node", "react"]),
        is_active=True,
    )
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return cv


def test_get_active_companies(db: Session):
    _seed_company(db, name="Active1", active=True)
    _seed_company(db, name="Active2", active=True)
    _seed_company(db, name="Inactive", active=False, ats_slug="inactive")

    companies = get_active_companies(db)
    assert len(companies) == 2
    assert all(c.active for c in companies)


@pytest.mark.asyncio
async def test_run_scan_for_greenhouse_company(db: Session):
    company = _seed_company(db)
    cv = _seed_cv(db)

    mock_raw_jobs = [
        {"title": "Dev", "url": "http://x.com/1", "description_raw": "Build stuff", "location": "Remote", "source": "ats_api"},
    ]

    with patch("app.scheduler.fetch_greenhouse_jobs", new_callable=AsyncMock, return_value=mock_raw_jobs), \
         patch("app.scheduler.score_job", new_callable=AsyncMock, return_value={
             "score": 85, "reasoning": "Great fit", "cv_variant": "fullstack-automation"
         }), \
         patch("app.scheduler.send_match_notification", new_callable=AsyncMock) as mock_notify, \
         patch("app.scheduler._load_user_profile", return_value="profile text"), \
         patch("app.scheduler._get_cv_variants_text", return_value="fullstack-automation [node, react]"):

        results = await run_scan_for_company(company, db)

    assert len(results) == 1
    assert results[0]["score"] == 85
    mock_notify.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_scan_low_score_no_notification(db: Session):
    company = _seed_company(db)
    cv = _seed_cv(db)

    mock_raw_jobs = [
        {"title": "Java Architect", "url": "http://x.com/2", "description_raw": "Java EE", "location": "Austin", "source": "ats_api"},
    ]

    with patch("app.scheduler.fetch_greenhouse_jobs", new_callable=AsyncMock, return_value=mock_raw_jobs), \
         patch("app.scheduler.score_job", new_callable=AsyncMock, return_value={
             "score": 30, "reasoning": "Wrong domain", "cv_variant": "fullstack-automation"
         }), \
         patch("app.scheduler.send_match_notification", new_callable=AsyncMock) as mock_notify, \
         patch("app.scheduler._load_user_profile", return_value="profile"), \
         patch("app.scheduler._get_cv_variants_text", return_value="fullstack-automation [node]"):

        results = await run_scan_for_company(company, db)

    assert len(results) == 1
    assert results[0]["score"] == 30
    mock_notify.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_scan_dedup_skips_existing(db: Session):
    company = _seed_company(db)
    cv = _seed_cv(db)

    mock_raw_jobs = [
        {"title": "Dev", "url": "http://x.com/1", "description_raw": "Build", "location": "", "source": "ats_api"},
    ]

    with patch("app.scheduler.fetch_greenhouse_jobs", new_callable=AsyncMock, return_value=mock_raw_jobs), \
         patch("app.scheduler.score_job", new_callable=AsyncMock, return_value={
             "score": 85, "reasoning": "Great", "cv_variant": "fullstack-automation"
         }), \
         patch("app.scheduler.send_match_notification", new_callable=AsyncMock), \
         patch("app.scheduler._load_user_profile", return_value="profile"), \
         patch("app.scheduler._get_cv_variants_text", return_value="fullstack-automation [node]"):

        first = await run_scan_for_company(company, db)
        assert len(first) == 1

        # Second scan — same jobs, should be deduped
        second = await run_scan_for_company(company, db)
        assert len(second) == 0
```

**Run (RED):**
```bash
cd backend && python -m pytest tests/test_scheduler.py -v
```

**Implementation.**

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\scheduler.py`
```python
"""APScheduler setup and scan orchestrator."""

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
from app.models.match import Match
from app.ingestion.ats_fetcher import fetch_greenhouse_jobs, fetch_lever_jobs
from app.ingestion.scrapling_fetcher import fetch_career_page, fetch_linkedin_jobs
from app.ingestion.normalizer import normalize_and_deduplicate
from app.pipeline.matchmaker import score_job
from app.pipeline.cv_selector import select_cv_variant
from app.notifications.telegram import send_match_notification

logger = logging.getLogger(__name__)

# Module-level scheduler instance
scheduler = BackgroundScheduler()

# Scan state for the /scan-status endpoint
scan_state = {
    "last_scan_at": None,
    "next_scan_at": None,
    "last_scan_new_jobs": 0,
    "is_running": False,
}


def _load_user_profile() -> str:
    """Load user profile from user_profile.md."""
    profile_path = Path(__file__).parent.parent / "user_profile.md"
    if profile_path.exists():
        return profile_path.read_text(encoding="utf-8")
    return ""


def _get_cv_variants_text(session: Session) -> str:
    """Format active CV variants for the matchmaker prompt."""
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
    """Return all active companies from the watchlist."""
    return list(session.exec(select(Company).where(Company.active == True)).all())


async def _fetch_jobs_for_company(company: Company) -> list[dict]:
    """Dispatch to the right fetcher based on ATS type."""
    if company.ats_type == "greenhouse" and company.ats_slug:
        return await fetch_greenhouse_jobs(company.ats_slug)
    elif company.ats_type == "lever" and company.ats_slug:
        return await fetch_lever_jobs(company.ats_slug)
    elif company.ats_type == "linkedin" and company.linkedin_url:
        return await fetch_linkedin_jobs(company.linkedin_url)
    elif company.career_page_url:
        return await fetch_career_page(company.career_page_url, company.website or "")
    else:
        logger.warning(f"No fetch strategy for company {company.name} (ats_type={company.ats_type})")
        return []


async def run_scan_for_company(company: Company, session: Session) -> list[dict]:
    """Run the full pipeline for a single company. Returns list of match result dicts."""
    # 1. Fetch raw jobs
    raw_jobs = await _fetch_jobs_for_company(company)
    if not raw_jobs:
        return []

    # 2. Normalize and deduplicate
    new_jobs = normalize_and_deduplicate(raw_jobs, company.id, session)
    if not new_jobs:
        return []

    # 3. Load context for matchmaker
    user_profile = _load_user_profile()
    cv_variants_text = _get_cv_variants_text(session)
    active_variants = list(
        session.exec(select(CVVariant).where(CVVariant.is_active == True)).all()
    )

    results = []

    for job in new_jobs:
        # 4. Score with AI
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

        # 5. Select CV variant
        selected = select_cv_variant(cv_name, active_variants)
        cv_variant_id = selected[0].id if selected else None

        # 6. Determine status
        status = "new" if score >= settings.match_threshold else "low_match"

        # 7. Create match record
        match = Match(
            job_id=job.id,
            score=score,
            reasoning=reasoning,
            cv_variant_id=cv_variant_id,
            status=status,
        )
        session.add(match)
        session.commit()
        session.refresh(match)

        # 8. Send notification for high matches only
        if status == "new":
            await send_match_notification(
                company_name=company.name,
                job_title=job.title,
                score=score,
                reasoning=reasoning,
                match_id=match.id,
            )

        results.append({
            "match_id": match.id,
            "job_title": job.title,
            "score": score,
            "status": status,
        })

    return results


async def run_full_scan(session: Session) -> dict:
    """Run the scan pipeline for all active companies."""
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


def start_scheduler():
    """Start the APScheduler with the configured interval."""
    scheduler.add_job(
        _scheduler_tick,
        trigger=IntervalTrigger(hours=settings.scan_interval_hours),
        id="job_scan",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started — scanning every {settings.scan_interval_hours}h")


def _scheduler_tick():
    """Synchronous wrapper for the async scan — called by APScheduler."""
    import asyncio
    from app.database import get_session

    session = next(get_session())
    try:
        asyncio.run(run_full_scan(session))
    finally:
        session.close()
```

**Run (GREEN):**
```bash
cd backend && python -m pytest tests/test_scheduler.py -v
```
Expected: 4 passed.

**Commit:** `feat: add scheduler and scan orchestrator`

---

## Phase 5: FastAPI API (Tasks 12-16)

### Task 12 -- Auth Middleware + Main App

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\auth.py`
```python
"""Bearer token authentication dependency."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings

security = HTTPBearer()


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Verify the bearer token matches the configured PWA_ACCESS_TOKEN."""
    if credentials.credentials != settings.pwa_access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )
    return credentials.credentials
```

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\main.py`
```python
"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.database import create_db_and_tables
from app.routers import matches, companies, tracker, cv_variants, scanner


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    create_db_and_tables()
    # Start scheduler only if not in test mode
    try:
        from app.scheduler import start_scheduler
        start_scheduler()
    except Exception:
        pass
    yield


app = FastAPI(
    title="JobFinderAgent",
    description="Autonomous Job Hunting Pipeline API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(matches.router, prefix="/matches", tags=["matches"])
app.include_router(companies.router, prefix="/companies", tags=["companies"])
app.include_router(tracker.router, tags=["tracker"])
app.include_router(cv_variants.router, prefix="/cv-variants", tags=["cv-variants"])
app.include_router(scanner.router, tags=["scanner"])

# Serve static PWA build if the directory exists
pwa_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if pwa_dist.exists():
    app.mount("/", StaticFiles(directory=str(pwa_dist), html=True), name="pwa")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "jobfinder-agent"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
```

**Update conftest.py** to add a test client fixture:

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\tests\conftest.py` (final version)
```python
"""Shared test fixtures."""

import pytest
from sqlmodel import SQLModel, Session, create_engine
from fastapi.testclient import TestClient

import app.models  # noqa: F401


@pytest.fixture(name="engine")
def test_engine():
    engine = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(engine)
    yield engine


@pytest.fixture(name="db")
def db_session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def test_client(engine):
    """TestClient with overridden DB session and auth."""
    from app.main import app
    from app.database import get_session
    from app.auth import verify_token

    def override_session():
        with Session(engine) as session:
            yield session

    async def override_auth():
        return "test-token"

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[verify_token] = override_auth

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
```

**Commit:** `feat: add auth middleware, main app, and test client fixture`

---

### Task 13 -- Matches Router

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\tests\test_api_matches.py`
```python
"""Tests for /matches API endpoints."""

import pytest
from sqlmodel import Session
from datetime import datetime, timezone

from app.models.company import Company
from app.models.job import Job
from app.models.match import Match
from app.models.cv_variant import CVVariant
from app.models.application import Application


def _seed_match(db: Session, status="new", score=85) -> tuple:
    company = Company(name="Vercel", ats_type="greenhouse", ats_slug="vercel")
    db.add(company)
    db.commit()
    db.refresh(company)

    job = Job(
        company_id=company.id,
        title="Frontend Engineer",
        url="https://boards.greenhouse.io/vercel/jobs/1",
        description_raw="Build UIs with React",
        location="Remote",
        remote=True,
        source="ats_api",
        content_hash=f"hash_{score}_{status}",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    cv = CVVariant(name="frontend-focused", file_path="/cv/fe.pdf", focus_tags='["react"]', is_active=True)
    db.add(cv)
    db.commit()
    db.refresh(cv)

    match = Match(
        job_id=job.id,
        score=score,
        reasoning="Strong React fit.",
        cv_variant_id=cv.id,
        status=status,
    )
    db.add(match)
    db.commit()
    db.refresh(match)

    return company, job, cv, match


def test_get_pending_matches(client, db):
    _seed_match(db, status="new", score=85)
    _seed_match(db, status="skipped", score=70)

    resp = client.get("/matches")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["status"] == "new"
    assert data[0]["score"] == 85


def test_get_match_detail(client, db):
    _, _, _, match = _seed_match(db)

    resp = client.get(f"/matches/{match.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == match.id
    assert data["job"]["title"] == "Frontend Engineer"
    assert data["company"]["name"] == "Vercel"


def test_get_match_not_found(client):
    resp = client.get("/matches/9999")
    assert resp.status_code == 404


def test_skip_match(client, db):
    _, _, _, match = _seed_match(db)

    resp = client.post(f"/matches/{match.id}/skip")
    assert resp.status_code == 200
    assert resp.json()["status"] == "skipped"


def test_apply_match(client, db):
    _, _, _, match = _seed_match(db)

    resp = client.post(
        f"/matches/{match.id}/applied",
        json={"ats_url": "https://boards.greenhouse.io/apply/1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["match"]["status"] == "applied"
    assert data["application"]["outcome_status"] == "pending"


def test_get_near_misses(client, db):
    _seed_match(db, status="low_match", score=55)
    _seed_match(db, status="new", score=90)

    resp = client.get("/matches/near-misses")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["status"] == "low_match"
```

**Run (RED):**
```bash
cd backend && python -m pytest tests/test_api_matches.py -v
```

**Implementation.**

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\routers\matches.py`
```python
"""Matches API router."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth import verify_token
from app.database import get_session
from app.models.company import Company
from app.models.job import Job
from app.models.match import Match
from app.models.cv_variant import CVVariant
from app.models.application import Application

router = APIRouter(dependencies=[Depends(verify_token)])


# --- Response schemas ---

class JobOut(BaseModel):
    id: int
    title: str
    url: str
    description_raw: Optional[str] = None
    location: Optional[str] = None
    remote: Optional[bool] = None

class CompanyOut(BaseModel):
    id: int
    name: str
    website: Optional[str] = None

class CVVariantOut(BaseModel):
    id: int
    name: str
    file_path: str

class MatchListItem(BaseModel):
    id: int
    score: int
    reasoning: str
    status: str
    matched_at: datetime
    job_title: str
    company_name: str

class MatchDetail(BaseModel):
    id: int
    score: int
    reasoning: str
    status: str
    matched_at: datetime
    reviewed_at: Optional[datetime] = None
    job: JobOut
    company: CompanyOut
    cv_variant: Optional[CVVariantOut] = None

class ApplyRequest(BaseModel):
    ats_url: Optional[str] = None

class ApplyResponse(BaseModel):
    match: MatchListItem
    application: dict


# --- Endpoints ---

@router.get("", response_model=list[MatchListItem])
async def get_pending_matches(session: Session = Depends(get_session)):
    """All matches with status=new, sorted by score descending."""
    matches = session.exec(
        select(Match, Job, Company)
        .join(Job, Match.job_id == Job.id)
        .join(Company, Job.company_id == Company.id)
        .where(Match.status == "new")
        .order_by(Match.score.desc())
    ).all()

    return [
        MatchListItem(
            id=m.id, score=m.score, reasoning=m.reasoning, status=m.status,
            matched_at=m.matched_at, job_title=j.title, company_name=c.name,
        )
        for m, j, c in matches
    ]


@router.get("/near-misses", response_model=list[MatchListItem])
async def get_near_misses(session: Session = Depends(get_session)):
    """Low-match jobs that scored below threshold."""
    matches = session.exec(
        select(Match, Job, Company)
        .join(Job, Match.job_id == Job.id)
        .join(Company, Job.company_id == Company.id)
        .where(Match.status == "low_match")
        .order_by(Match.score.desc())
    ).all()

    return [
        MatchListItem(
            id=m.id, score=m.score, reasoning=m.reasoning, status=m.status,
            matched_at=m.matched_at, job_title=j.title, company_name=c.name,
        )
        for m, j, c in matches
    ]


@router.get("/{match_id}", response_model=MatchDetail)
async def get_match_detail(match_id: int, session: Session = Depends(get_session)):
    """Single match with full job, company, and CV variant details."""
    result = session.exec(
        select(Match, Job, Company)
        .join(Job, Match.job_id == Job.id)
        .join(Company, Job.company_id == Company.id)
        .where(Match.id == match_id)
    ).first()

    if not result:
        raise HTTPException(status_code=404, detail="Match not found")

    match, job, company = result

    cv_variant = None
    if match.cv_variant_id:
        cv = session.get(CVVariant, match.cv_variant_id)
        if cv:
            cv_variant = CVVariantOut(id=cv.id, name=cv.name, file_path=cv.file_path)

    return MatchDetail(
        id=match.id, score=match.score, reasoning=match.reasoning,
        status=match.status, matched_at=match.matched_at, reviewed_at=match.reviewed_at,
        job=JobOut(
            id=job.id, title=job.title, url=job.url,
            description_raw=job.description_raw, location=job.location, remote=job.remote,
        ),
        company=CompanyOut(id=company.id, name=company.name, website=company.website),
        cv_variant=cv_variant,
    )


@router.post("/{match_id}/skip")
async def skip_match(match_id: int, session: Session = Depends(get_session)):
    """Mark a match as skipped."""
    match = session.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match.status = "skipped"
    match.reviewed_at = datetime.now(timezone.utc)
    session.add(match)
    session.commit()
    session.refresh(match)
    return {"id": match.id, "status": match.status}


@router.post("/{match_id}/applied")
async def apply_match(
    match_id: int,
    body: ApplyRequest,
    session: Session = Depends(get_session),
):
    """Mark as applied and create an application record."""
    match = session.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match.status = "applied"
    match.reviewed_at = datetime.now(timezone.utc)
    session.add(match)

    application = Application(
        match_id=match.id,
        cv_variant_id=match.cv_variant_id,
        ats_url=body.ats_url,
        outcome_status="pending",
    )
    session.add(application)
    session.commit()
    session.refresh(match)
    session.refresh(application)

    job = session.get(Job, match.job_id)
    company = session.get(Company, job.company_id)

    return {
        "match": MatchListItem(
            id=match.id, score=match.score, reasoning=match.reasoning,
            status=match.status, matched_at=match.matched_at,
            job_title=job.title, company_name=company.name,
        ),
        "application": {
            "id": application.id,
            "outcome_status": application.outcome_status,
            "applied_at": application.applied_at.isoformat(),
        },
    }
```

**Run (GREEN):**
```bash
cd backend && python -m pytest tests/test_api_matches.py -v
```
Expected: 6 passed.

**Commit:** `feat: add matches API router`

---

### Task 14 -- Companies Router

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\tests\test_api_companies.py`
```python
"""Tests for /companies API endpoints."""

import pytest
from app.models.company import Company


def test_list_companies_empty(client):
    resp = client.get("/companies")
    assert resp.status_code == 200
    assert resp.json() == []


def test_add_company(client):
    resp = client.post("/companies", json={
        "name": "Vercel",
        "website": "https://vercel.com",
        "ats_type": "greenhouse",
        "ats_slug": "vercel",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Vercel"
    assert data["ats_type"] == "greenhouse"
    assert data["active"] is True


def test_list_companies_after_add(client):
    client.post("/companies", json={"name": "Co1", "ats_type": "lever", "ats_slug": "co1"})
    client.post("/companies", json={"name": "Co2", "ats_type": "greenhouse", "ats_slug": "co2"})

    resp = client.get("/companies")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_update_company(client):
    resp = client.post("/companies", json={"name": "Old", "ats_type": "custom"})
    cid = resp.json()["id"]

    resp = client.patch(f"/companies/{cid}", json={"name": "New", "active": False})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"
    assert resp.json()["active"] is False


def test_delete_company(client):
    resp = client.post("/companies", json={"name": "ToDelete", "ats_type": "custom"})
    cid = resp.json()["id"]

    resp = client.delete(f"/companies/{cid}")
    assert resp.status_code == 200

    resp = client.get("/companies")
    assert len(resp.json()) == 0


def test_update_nonexistent_company(client):
    resp = client.patch("/companies/9999", json={"name": "X"})
    assert resp.status_code == 404
```

**Run (RED):**
```bash
cd backend && python -m pytest tests/test_api_companies.py -v
```

**Implementation.**

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\routers\companies.py`
```python
"""Companies (watchlist) API router."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth import verify_token
from app.database import get_session
from app.models.company import Company

router = APIRouter(dependencies=[Depends(verify_token)])


class CompanyCreate(BaseModel):
    name: str
    website: Optional[str] = None
    ats_type: str
    ats_slug: Optional[str] = None
    linkedin_url: Optional[str] = None
    career_page_url: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    website: Optional[str] = None
    ats_type: Optional[str] = None
    ats_slug: Optional[str] = None
    linkedin_url: Optional[str] = None
    career_page_url: Optional[str] = None
    active: Optional[bool] = None


@router.get("")
async def list_companies(session: Session = Depends(get_session)):
    return list(session.exec(select(Company)).all())


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_company(body: CompanyCreate, session: Session = Depends(get_session)):
    company = Company(**body.model_dump())
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


@router.patch("/{company_id}")
async def update_company(company_id: int, body: CompanyUpdate, session: Session = Depends(get_session)):
    company = session.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(company, key, value)

    session.add(company)
    session.commit()
    session.refresh(company)
    return company


@router.delete("/{company_id}")
async def delete_company(company_id: int, session: Session = Depends(get_session)):
    company = session.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    session.delete(company)
    session.commit()
    return {"deleted": True, "id": company_id}
```

**Run (GREEN):**
```bash
cd backend && python -m pytest tests/test_api_companies.py -v
```
Expected: 6 passed.

**Commit:** `feat: add companies API router`

---

### Task 15 -- Tracker + Applications Router

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\tests\test_api_tracker.py`
```python
"""Tests for /tracker and /applications API endpoints."""

import pytest
from sqlmodel import Session

from app.models.company import Company
from app.models.job import Job
from app.models.match import Match
from app.models.cv_variant import CVVariant
from app.models.application import Application


def _seed_application(db: Session, outcome="pending") -> Application:
    c = Company(name="Co", ats_type="custom")
    db.add(c)
    db.commit()
    db.refresh(c)

    j = Job(company_id=c.id, title="Dev", url="http://x.com", source="ats_api",
            content_hash=f"h_{outcome}_{id(db)}")
    db.add(j)
    db.commit()
    db.refresh(j)

    cv = CVVariant(name="v1", file_path="/cv.pdf", focus_tags="[]", is_active=True)
    db.add(cv)
    db.commit()
    db.refresh(cv)

    m = Match(job_id=j.id, score=85, reasoning="Good", cv_variant_id=cv.id, status="applied")
    db.add(m)
    db.commit()
    db.refresh(m)

    app = Application(match_id=m.id, cv_variant_id=cv.id, outcome_status=outcome)
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


def test_get_tracker(client, db):
    _seed_application(db, "pending")

    resp = client.get("/tracker")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["outcome_status"] == "pending"


def test_update_application(client, db):
    app = _seed_application(db, "pending")

    resp = client.patch(f"/applications/{app.id}", json={
        "outcome_status": "interview",
        "notes": "Phone screen scheduled for next week",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["outcome_status"] == "interview"
    assert data["notes"] == "Phone screen scheduled for next week"


def test_update_nonexistent_application(client):
    resp = client.patch("/applications/9999", json={"outcome_status": "offer"})
    assert resp.status_code == 404
```

**Run (RED):**
```bash
cd backend && python -m pytest tests/test_api_tracker.py -v
```

**Implementation.**

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\routers\tracker.py`
```python
"""Tracker and Applications API router."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth import verify_token
from app.database import get_session
from app.models.application import Application
from app.models.match import Match
from app.models.job import Job
from app.models.company import Company

router = APIRouter(dependencies=[Depends(verify_token)])


class ApplicationUpdate(BaseModel):
    outcome_status: Optional[str] = None
    notes: Optional[str] = None
    confirmed_at: Optional[datetime] = None


@router.get("/tracker")
async def get_tracker(session: Session = Depends(get_session)):
    """All applications with joined match/job/company info."""
    results = session.exec(
        select(Application, Match, Job, Company)
        .join(Match, Application.match_id == Match.id)
        .join(Job, Match.job_id == Job.id)
        .join(Company, Job.company_id == Company.id)
        .order_by(Application.applied_at.desc())
    ).all()

    return [
        {
            "id": app.id,
            "match_id": app.match_id,
            "outcome_status": app.outcome_status,
            "notes": app.notes,
            "applied_at": app.applied_at.isoformat() if app.applied_at else None,
            "confirmed_at": app.confirmed_at.isoformat() if app.confirmed_at else None,
            "job_title": job.title,
            "company_name": company.name,
            "score": match.score,
        }
        for app, match, job, company in results
    ]


@router.patch("/applications/{app_id}")
async def update_application(
    app_id: int,
    body: ApplicationUpdate,
    session: Session = Depends(get_session),
):
    app = session.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(app, key, value)

    app.last_status_update = datetime.now(timezone.utc)
    session.add(app)
    session.commit()
    session.refresh(app)
    return app
```

**Run (GREEN):**
```bash
cd backend && python -m pytest tests/test_api_tracker.py -v
```
Expected: 3 passed.

**Commit:** `feat: add tracker and applications API router`

---

### Task 16 -- CV Variants + Scanner Router

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\tests\test_api_scanner.py`
```python
"""Tests for /cv-variants and /trigger-scan, /scan-status endpoints."""

import pytest
from unittest.mock import patch, AsyncMock


def test_list_cv_variants_empty(client):
    resp = client.get("/cv-variants")
    assert resp.status_code == 200
    assert resp.json() == []


def test_add_cv_variant(client):
    resp = client.post("/cv-variants", json={
        "name": "frontend-focused",
        "file_path": "/cvs/frontend.pdf",
        "focus_tags": '["react","ui"]',
    })
    assert resp.status_code == 201
    assert resp.json()["name"] == "frontend-focused"


def test_delete_cv_variant(client):
    resp = client.post("/cv-variants", json={
        "name": "temp", "file_path": "/cv.pdf", "focus_tags": "[]",
    })
    vid = resp.json()["id"]

    resp = client.delete(f"/cv-variants/{vid}")
    assert resp.status_code == 200

    # Should be deactivated, not deleted
    resp = client.get("/cv-variants")
    # Active variants only
    assert all(v["is_active"] for v in resp.json())


def test_trigger_scan(client):
    with patch("app.routers.scanner.run_full_scan", new_callable=AsyncMock, return_value={
        "last_scan_at": "2026-04-17T10:00:00",
        "last_scan_new_jobs": 3,
        "is_running": False,
    }):
        resp = client.post("/trigger-scan")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Scan triggered"


def test_scan_status(client):
    resp = client.get("/scan-status")
    assert resp.status_code == 200
    assert "last_scan_at" in resp.json()
```

**Run (RED):**
```bash
cd backend && python -m pytest tests/test_api_scanner.py -v
```

**Implementation.**

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\routers\cv_variants.py`
```python
"""CV Variants API router."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth import verify_token
from app.database import get_session
from app.models.cv_variant import CVVariant

router = APIRouter(dependencies=[Depends(verify_token)])


class CVVariantCreate(BaseModel):
    name: str
    file_path: str
    focus_tags: str = "[]"


@router.get("")
async def list_cv_variants(session: Session = Depends(get_session)):
    return list(session.exec(select(CVVariant).where(CVVariant.is_active == True)).all())


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_cv_variant(body: CVVariantCreate, session: Session = Depends(get_session)):
    cv = CVVariant(**body.model_dump())
    session.add(cv)
    session.commit()
    session.refresh(cv)
    return cv


@router.delete("/{variant_id}")
async def deactivate_cv_variant(variant_id: int, session: Session = Depends(get_session)):
    cv = session.get(CVVariant, variant_id)
    if not cv:
        raise HTTPException(status_code=404, detail="CV variant not found")

    cv.is_active = False
    session.add(cv)
    session.commit()
    return {"deactivated": True, "id": variant_id}
```

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\routers\scanner.py`
```python
"""Scanner API router — manual scan trigger and status."""

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlmodel import Session

from app.auth import verify_token
from app.database import get_session
from app.scheduler import run_full_scan, scan_state

router = APIRouter(dependencies=[Depends(verify_token)])


@router.post("/trigger-scan")
async def trigger_scan(
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Trigger a manual scan in the background."""
    if scan_state["is_running"]:
        return {"message": "Scan already in progress"}

    background_tasks.add_task(run_full_scan, session)
    return {"message": "Scan triggered"}


@router.get("/scan-status")
async def get_scan_status():
    """Return current scan state."""
    return scan_state
```

**Run (GREEN):**
```bash
cd backend && python -m pytest tests/test_api_scanner.py -v
```
Expected: 5 passed.

**Commit:** `feat: add CV variants and scanner API routers`

---

## Phase 6: Deployment (Task 17)

### Task 17 -- systemd Service + Deploy Script

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\jobfinder.service`
```ini
[Unit]
Description=JobFinderAgent - Autonomous Job Hunting Pipeline
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/JobFinderAgent/backend
Environment=PATH=/home/ubuntu/JobFinderAgent/backend/venv/bin:/usr/bin
ExecStart=/home/ubuntu/JobFinderAgent/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\scripts\deploy.sh`
```bash
#!/bin/bash
set -euo pipefail

PROJECT_DIR="/home/ubuntu/JobFinderAgent"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

echo "=== Pulling latest code ==="
cd "$PROJECT_DIR"
git pull origin main

echo "=== Backend setup ==="
cd "$BACKEND_DIR"
python3 -m venv venv 2>/dev/null || true
source venv/bin/activate
pip install -r requirements.txt

echo "=== Frontend build ==="
cd "$FRONTEND_DIR"
npm ci
npm run build

echo "=== Install systemd service ==="
sudo cp "$PROJECT_DIR/jobfinder.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable jobfinder
sudo systemctl restart jobfinder

echo "=== Done ==="
sudo systemctl status jobfinder --no-pager
```

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\user_profile.md`
```markdown
# User Profile

(To be filled in with your actual skills, experience, and preferences.
The matchmaker uses this file as context when scoring jobs.)

## Skills
- React, TypeScript, Node.js
- Python, FastAPI
- (Add more...)

## Experience
- (Add your experience summary...)

## Preferences
- Remote preferred
- (Add more...)
```

**Commit:** `chore: add deployment scripts and systemd service`

---

## Phase 7: React PWA Frontend (Tasks 18-24)

### Task 18 -- Frontend Scaffold

**Files to create:**
- `C:\Users\offir\Desktop\Projects\JobFinderAgent\frontend\package.json`
- `C:\Users\offir\Desktop\Projects\JobFinderAgent\frontend\tsconfig.json`
- `C:\Users\offir\Desktop\Projects\JobFinderAgent\frontend\vite.config.ts`
- `C:\Users\offir\Desktop\Projects\JobFinderAgent\frontend\tailwind.config.ts`
- `C:\Users\offir\Desktop\Projects\JobFinderAgent\frontend\index.html`
- `C:\Users\offir\Desktop\Projects\JobFinderAgent\frontend\public\manifest.json`
- `C:\Users\offir\Desktop\Projects\JobFinderAgent\frontend\src\main.tsx`

**package.json:**
```json
{
  "name": "jobfinder-pwa",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:ui": "vitest --ui"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.23.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.4.0",
    "@testing-library/react": "^15.0.0",
    "@testing-library/user-event": "^14.5.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "autoprefixer": "^10.4.0",
    "jsdom": "^24.0.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.4.0",
    "vite": "^5.4.0",
    "vitest": "^1.6.0"
  }
}
```

**vite.config.ts:**
```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/matches": "http://localhost:8000",
      "/companies": "http://localhost:8000",
      "/tracker": "http://localhost:8000",
      "/applications": "http://localhost:8000",
      "/cv-variants": "http://localhost:8000",
      "/trigger-scan": "http://localhost:8000",
      "/scan-status": "http://localhost:8000",
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test-setup.ts",
  },
});
```

**tsconfig.json:**
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
```

**tailwind.config.ts:**
```typescript
import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
} satisfies Config;
```

**index.html:**
```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no" />
    <meta name="theme-color" content="#1a1a2e" />
    <link rel="manifest" href="/manifest.json" />
    <title>JobFinder</title>
  </head>
  <body class="bg-gray-950 text-gray-100">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

**public/manifest.json:**
```json
{
  "name": "JobFinder Agent",
  "short_name": "JobFinder",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#1a1a2e",
  "theme_color": "#1a1a2e",
  "icons": []
}
```

**src/main.tsx:**
```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

**src/index.css:**
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

**src/test-setup.ts:**
```typescript
import "@testing-library/jest-dom";
```

**Run:**
```bash
cd frontend && npm install && npm run build
```

**Commit:** `chore: scaffold React PWA frontend`

---

### Task 19 -- Types + API Client

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\frontend\src\types\index.ts`
```typescript
export interface Company {
  id: number;
  name: string;
  website: string | null;
  ats_type: string;
  ats_slug: string | null;
  linkedin_url: string | null;
  career_page_url: string | null;
  active: boolean;
  added_at: string;
}

export interface Job {
  id: number;
  title: string;
  url: string;
  description_raw: string | null;
  location: string | null;
  remote: boolean | null;
}

export interface CVVariant {
  id: number;
  name: string;
  file_path: string;
  focus_tags: string;
  is_active: boolean;
}

export interface MatchListItem {
  id: number;
  score: number;
  reasoning: string;
  status: string;
  matched_at: string;
  job_title: string;
  company_name: string;
}

export interface MatchDetail {
  id: number;
  score: number;
  reasoning: string;
  status: string;
  matched_at: string;
  reviewed_at: string | null;
  job: Job;
  company: { id: number; name: string; website: string | null };
  cv_variant: { id: number; name: string; file_path: string } | null;
}

export interface Application {
  id: number;
  match_id: number;
  outcome_status: string;
  notes: string | null;
  applied_at: string;
  confirmed_at: string | null;
  job_title: string;
  company_name: string;
  score: number;
}

export interface ScanStatus {
  last_scan_at: string | null;
  next_scan_at: string | null;
  last_scan_new_jobs: number;
  is_running: boolean;
}
```

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\frontend\src\api\client.ts`
```typescript
const BASE_URL = import.meta.env.VITE_API_URL || "";
const TOKEN = import.meta.env.VITE_ACCESS_TOKEN || "";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${TOKEN}`,
      ...init?.headers,
    },
  });

  if (!resp.ok) {
    throw new Error(`API error ${resp.status}: ${await resp.text()}`);
  }

  return resp.json();
}

export const api = {
  // Matches
  getMatches: () => apiFetch<import("../types").MatchListItem[]>("/matches"),
  getMatch: (id: number) => apiFetch<import("../types").MatchDetail>(`/matches/${id}`),
  skipMatch: (id: number) => apiFetch<{ status: string }>(`/matches/${id}/skip`, { method: "POST" }),
  applyMatch: (id: number, atsUrl?: string) =>
    apiFetch<{ match: import("../types").MatchListItem; application: { id: number } }>(
      `/matches/${id}/applied`,
      { method: "POST", body: JSON.stringify({ ats_url: atsUrl }) }
    ),
  getNearMisses: () => apiFetch<import("../types").MatchListItem[]>("/matches/near-misses"),

  // Tracker
  getTracker: () => apiFetch<import("../types").Application[]>("/tracker"),
  updateApplication: (id: number, data: { outcome_status?: string; notes?: string }) =>
    apiFetch<import("../types").Application>(`/applications/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  // Companies
  getCompanies: () => apiFetch<import("../types").Company[]>("/companies"),
  addCompany: (data: Partial<import("../types").Company>) =>
    apiFetch<import("../types").Company>("/companies", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateCompany: (id: number, data: Partial<import("../types").Company>) =>
    apiFetch<import("../types").Company>(`/companies/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteCompany: (id: number) =>
    apiFetch<{ deleted: boolean }>(`/companies/${id}`, { method: "DELETE" }),

  // CV Variants
  getCVVariants: () => apiFetch<import("../types").CVVariant[]>("/cv-variants"),
  addCVVariant: (data: { name: string; file_path: string; focus_tags: string }) =>
    apiFetch<import("../types").CVVariant>("/cv-variants", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Scanner
  triggerScan: () => apiFetch<{ message: string }>("/trigger-scan", { method: "POST" }),
  getScanStatus: () => apiFetch<import("../types").ScanStatus>("/scan-status"),
};
```

**Commit:** `feat: add TypeScript types and API client`

---

### Task 20 -- App Router + Hooks

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\frontend\src\hooks\useMatches.ts`
```typescript
import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";
import type { MatchListItem } from "../types";

export function useMatches() {
  const [matches, setMatches] = useState<MatchListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getMatches();
      setMatches(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load matches");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { matches, loading, error, refresh };
}
```

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\frontend\src\App.tsx`
```tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import MatchQueue from "./pages/MatchQueue";
import Tracker from "./pages/Tracker";
import ApplicationDetail from "./pages/ApplicationDetail";
import Companies from "./pages/Companies";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950 text-gray-100">
        <Routes>
          <Route path="/" element={<Navigate to="/matches" replace />} />
          <Route path="/matches" element={<MatchQueue />} />
          <Route path="/matches/:id" element={<MatchQueue />} />
          <Route path="/tracker" element={<Tracker />} />
          <Route path="/tracker/:id" element={<ApplicationDetail />} />
          <Route path="/companies" element={<Companies />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>

        {/* Bottom navigation bar */}
        <nav className="fixed bottom-0 left-0 right-0 bg-gray-900 border-t border-gray-800 flex justify-around py-3 px-4">
          <a href="/matches" className="text-xs text-center text-gray-400 hover:text-white">
            <div className="text-lg">📋</div>
            Matches
          </a>
          <a href="/tracker" className="text-xs text-center text-gray-400 hover:text-white">
            <div className="text-lg">📊</div>
            Tracker
          </a>
          <a href="/companies" className="text-xs text-center text-gray-400 hover:text-white">
            <div className="text-lg">🏢</div>
            Companies
          </a>
          <a href="/settings" className="text-xs text-center text-gray-400 hover:text-white">
            <div className="text-lg">⚙️</div>
            Settings
          </a>
        </nav>
      </div>
    </BrowserRouter>
  );
}
```

**Commit:** `feat: add App router, navigation, and useMatches hook`

---

### Task 21 -- Shared Components

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\frontend\src\components\StatusBadge.tsx`
```tsx
interface StatusBadgeProps {
  score: number;
  status?: string;
}

const scoreColor = (score: number) => {
  if (score >= 85) return "bg-green-500/20 text-green-400";
  if (score >= 70) return "bg-yellow-500/20 text-yellow-400";
  if (score >= 55) return "bg-orange-500/20 text-orange-400";
  return "bg-red-500/20 text-red-400";
};

const statusColor: Record<string, string> = {
  new: "bg-blue-500/20 text-blue-400",
  applied: "bg-purple-500/20 text-purple-400",
  interview: "bg-green-500/20 text-green-400",
  offer: "bg-emerald-500/20 text-emerald-400",
  rejected: "bg-red-500/20 text-red-400",
  skipped: "bg-gray-500/20 text-gray-400",
  no_response: "bg-gray-500/20 text-gray-500",
};

export default function StatusBadge({ score, status }: StatusBadgeProps) {
  return (
    <div className="flex items-center gap-2">
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${scoreColor(score)}`}>
        {score}%
      </span>
      {status && (
        <span
          className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColor[status] || "bg-gray-500/20 text-gray-400"}`}
        >
          {status}
        </span>
      )}
    </div>
  );
}
```

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\frontend\src\components\MatchCard.tsx`
```tsx
import type { MatchListItem } from "../types";
import StatusBadge from "./StatusBadge";

interface MatchCardProps {
  match: MatchListItem;
  onTap: (id: number) => void;
  onSkip: (id: number) => void;
  onApply: (id: number) => void;
}

export default function MatchCard({ match, onTap, onSkip, onApply }: MatchCardProps) {
  return (
    <div
      className="bg-gray-900 rounded-xl p-4 border border-gray-800 shadow-lg"
      onClick={() => onTap(match.id)}
      role="button"
      tabIndex={0}
      data-testid="match-card"
    >
      <div className="flex items-start justify-between mb-2">
        <div>
          <h3 className="font-semibold text-white">{match.job_title}</h3>
          <p className="text-sm text-gray-400">{match.company_name}</p>
        </div>
        <StatusBadge score={match.score} status={match.status} />
      </div>
      <p className="text-sm text-gray-300 mb-4 line-clamp-2">{match.reasoning}</p>
      <div className="flex gap-3">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onSkip(match.id);
          }}
          className="flex-1 py-2 rounded-lg bg-gray-800 text-gray-400 hover:bg-gray-700 text-sm font-medium"
        >
          Skip
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onApply(match.id);
          }}
          className="flex-1 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-500 text-sm font-medium"
        >
          Apply
        </button>
      </div>
    </div>
  );
}
```

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\frontend\src\components\BottomSheet.tsx`
```tsx
import { useState, useEffect } from "react";

interface BottomSheetProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

export default function BottomSheet({ isOpen, onClose, children }: BottomSheetProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setVisible(true);
    } else {
      const t = setTimeout(() => setVisible(false), 300);
      return () => clearTimeout(t);
    }
  }, [isOpen]);

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-50" data-testid="bottom-sheet">
      <div
        className={`absolute inset-0 bg-black/50 transition-opacity ${isOpen ? "opacity-100" : "opacity-0"}`}
        onClick={onClose}
      />
      <div
        className={`absolute bottom-0 left-0 right-0 bg-gray-900 rounded-t-2xl max-h-[85vh] overflow-y-auto transition-transform ${
          isOpen ? "translate-y-0" : "translate-y-full"
        }`}
      >
        <div className="w-12 h-1.5 bg-gray-600 rounded-full mx-auto mt-3 mb-4" />
        <div className="px-4 pb-8">{children}</div>
      </div>
    </div>
  );
}
```

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\frontend\src\components\ConfirmApplied.tsx`
```tsx
interface ConfirmAppliedProps {
  isOpen: boolean;
  jobTitle: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmApplied({ isOpen, jobTitle, onConfirm, onCancel }: ConfirmAppliedProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" data-testid="confirm-dialog">
      <div className="absolute inset-0 bg-black/60" onClick={onCancel} />
      <div className="relative bg-gray-900 rounded-2xl p-6 mx-4 max-w-sm w-full border border-gray-800">
        <h3 className="text-lg font-semibold text-white mb-2">Did you submit?</h3>
        <p className="text-sm text-gray-400 mb-6">
          Confirm that you completed the application for <strong>{jobTitle}</strong>.
        </p>
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 py-2.5 rounded-lg bg-gray-800 text-gray-400 hover:bg-gray-700 font-medium"
          >
            Not yet
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 py-2.5 rounded-lg bg-green-600 text-white hover:bg-green-500 font-medium"
          >
            Yes, submitted
          </button>
        </div>
      </div>
    </div>
  );
}
```

**Commit:** `feat: add shared UI components (MatchCard, BottomSheet, StatusBadge, ConfirmApplied)`

---

### Task 22 -- MatchQueue Page (with test)

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\frontend\src\components\__tests__\MatchCard.test.tsx`
```tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import MatchCard from "../MatchCard";

const mockMatch = {
  id: 1,
  score: 88,
  reasoning: "Strong React fit.",
  status: "new",
  matched_at: "2026-04-17T10:00:00Z",
  job_title: "Senior Frontend Engineer",
  company_name: "Vercel",
};

describe("MatchCard", () => {
  it("renders job title and company", () => {
    render(
      <MatchCard match={mockMatch} onTap={vi.fn()} onSkip={vi.fn()} onApply={vi.fn()} />
    );
    expect(screen.getByText("Senior Frontend Engineer")).toBeInTheDocument();
    expect(screen.getByText("Vercel")).toBeInTheDocument();
  });

  it("shows score badge", () => {
    render(
      <MatchCard match={mockMatch} onTap={vi.fn()} onSkip={vi.fn()} onApply={vi.fn()} />
    );
    expect(screen.getByText("88%")).toBeInTheDocument();
  });

  it("calls onSkip when Skip is clicked", () => {
    const onSkip = vi.fn();
    render(
      <MatchCard match={mockMatch} onTap={vi.fn()} onSkip={onSkip} onApply={vi.fn()} />
    );
    fireEvent.click(screen.getByText("Skip"));
    expect(onSkip).toHaveBeenCalledWith(1);
  });

  it("calls onApply when Apply is clicked", () => {
    const onApply = vi.fn();
    render(
      <MatchCard match={mockMatch} onTap={vi.fn()} onSkip={vi.fn()} onApply={onApply} />
    );
    fireEvent.click(screen.getByText("Apply"));
    expect(onApply).toHaveBeenCalledWith(1);
  });
});
```

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\frontend\src\pages\MatchQueue.tsx`
```tsx
import { useState } from "react";
import { useParams } from "react-router-dom";
import { useMatches } from "../hooks/useMatches";
import MatchCard from "../components/MatchCard";
import BottomSheet from "../components/BottomSheet";
import ConfirmApplied from "../components/ConfirmApplied";
import { api } from "../api/client";
import type { MatchDetail } from "../types";

export default function MatchQueue() {
  const { id } = useParams();
  const { matches, loading, error, refresh } = useMatches();
  const [selectedMatch, setSelectedMatch] = useState<MatchDetail | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [applyingId, setApplyingId] = useState<number | null>(null);

  const handleTap = async (matchId: number) => {
    try {
      const detail = await api.getMatch(matchId);
      setSelectedMatch(detail);
      setSheetOpen(true);
    } catch {
      // handle error
    }
  };

  const handleSkip = async (matchId: number) => {
    await api.skipMatch(matchId);
    refresh();
  };

  const handleApply = (matchId: number) => {
    setApplyingId(matchId);
    // Open the ATS URL in a new tab
    const match = matches.find((m) => m.id === matchId);
    if (match) {
      // After opening ATS, show confirm dialog
      setConfirmOpen(true);
    }
  };

  const handleConfirm = async () => {
    if (applyingId) {
      await api.applyMatch(applyingId);
      setConfirmOpen(false);
      setApplyingId(null);
      refresh();
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center text-red-400">
        <p>{error}</p>
        <button onClick={refresh} className="mt-2 text-blue-400 underline">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="pb-20 pt-4 px-4">
      <h1 className="text-xl font-bold mb-4">
        New Matches <span className="text-gray-500 text-base">({matches.length})</span>
      </h1>

      {matches.length === 0 ? (
        <div className="text-center text-gray-500 mt-12">
          <p className="text-4xl mb-2">🎯</p>
          <p>No pending matches.</p>
          <p className="text-sm">Check back after the next scan.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {matches.map((match) => (
            <MatchCard
              key={match.id}
              match={match}
              onTap={handleTap}
              onSkip={handleSkip}
              onApply={handleApply}
            />
          ))}
        </div>
      )}

      <BottomSheet isOpen={sheetOpen} onClose={() => setSheetOpen(false)}>
        {selectedMatch && (
          <div>
            <h2 className="text-lg font-bold">{selectedMatch.job.title}</h2>
            <p className="text-sm text-gray-400 mb-2">
              {selectedMatch.company.name} · {selectedMatch.job.location}
            </p>
            <p className="text-sm text-gray-300 mb-4">{selectedMatch.reasoning}</p>
            {selectedMatch.cv_variant && (
              <p className="text-xs text-gray-500 mb-4">
                CV: {selectedMatch.cv_variant.name}
              </p>
            )}
            <div className="prose prose-invert prose-sm max-w-none">
              <div
                dangerouslySetInnerHTML={{
                  __html: selectedMatch.job.description_raw || "No description available.",
                }}
              />
            </div>
          </div>
        )}
      </BottomSheet>

      <ConfirmApplied
        isOpen={confirmOpen}
        jobTitle={matches.find((m) => m.id === applyingId)?.job_title || ""}
        onConfirm={handleConfirm}
        onCancel={() => {
          setConfirmOpen(false);
          setApplyingId(null);
        }}
      />
    </div>
  );
}
```

**Run:**
```bash
cd frontend && npx vitest run
```

**Commit:** `feat: add MatchQueue page with card tests`

---

### Task 23 -- Tracker + Companies + Settings Pages

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\frontend\src\pages\Tracker.tsx`
```tsx
import { useState, useEffect } from "react";
import { api } from "../api/client";
import type { Application } from "../types";
import StatusBadge from "../components/StatusBadge";

const STATUS_COLUMNS = ["pending", "interview", "offer", "rejected"];

export default function Tracker() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getTracker().then(setApplications).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="p-4 text-center text-gray-500">Loading...</div>;
  }

  return (
    <div className="pb-20 pt-4 px-4">
      <h1 className="text-xl font-bold mb-4">Application Tracker</h1>

      {STATUS_COLUMNS.map((status) => {
        const items = applications.filter((a) => a.outcome_status === status);
        return (
          <div key={status} className="mb-6">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-2">
              {status} ({items.length})
            </h2>
            {items.length === 0 ? (
              <p className="text-xs text-gray-600">None</p>
            ) : (
              <div className="space-y-2">
                {items.map((app) => (
                  <a
                    key={app.id}
                    href={`/tracker/${app.id}`}
                    className="block bg-gray-900 rounded-lg p-3 border border-gray-800"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-medium text-sm">{app.job_title}</p>
                        <p className="text-xs text-gray-400">{app.company_name}</p>
                      </div>
                      <StatusBadge score={app.score} />
                    </div>
                  </a>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
```

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\frontend\src\pages\ApplicationDetail.tsx`
```tsx
import { useParams, useNavigate } from "react-router-dom";

export default function ApplicationDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  // Simplified — would fetch full detail in production
  return (
    <div className="pb-20 pt-4 px-4">
      <button onClick={() => navigate("/tracker")} className="text-blue-400 text-sm mb-4">
        &larr; Back to Tracker
      </button>
      <h1 className="text-xl font-bold mb-4">Application #{id}</h1>
      <p className="text-gray-400">Detailed view coming soon.</p>
    </div>
  );
}
```

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\frontend\src\pages\Companies.tsx`
```tsx
import { useState, useEffect } from "react";
import { api } from "../api/client";
import type { Company } from "../types";

export default function Companies() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: "", ats_type: "greenhouse", ats_slug: "", career_page_url: "" });

  const refresh = () => api.getCompanies().then(setCompanies);

  useEffect(() => {
    refresh();
  }, []);

  const handleAdd = async () => {
    await api.addCompany(form);
    setForm({ name: "", ats_type: "greenhouse", ats_slug: "", career_page_url: "" });
    setShowAdd(false);
    refresh();
  };

  const handleDelete = async (id: number) => {
    await api.deleteCompany(id);
    refresh();
  };

  const handleToggle = async (company: Company) => {
    await api.updateCompany(company.id, { active: !company.active });
    refresh();
  };

  return (
    <div className="pb-20 pt-4 px-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-xl font-bold">Watchlist</h1>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm font-medium"
        >
          + Add
        </button>
      </div>

      {showAdd && (
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 mb-4 space-y-3">
          <input
            placeholder="Company name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm"
          />
          <select
            value={form.ats_type}
            onChange={(e) => setForm({ ...form, ats_type: e.target.value })}
            className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm"
          >
            <option value="greenhouse">Greenhouse</option>
            <option value="lever">Lever</option>
            <option value="workday">Workday</option>
            <option value="custom">Custom</option>
            <option value="linkedin">LinkedIn</option>
          </select>
          <input
            placeholder="ATS slug (e.g. vercel)"
            value={form.ats_slug}
            onChange={(e) => setForm({ ...form, ats_slug: e.target.value })}
            className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm"
          />
          <input
            placeholder="Career page URL (for custom/workday)"
            value={form.career_page_url}
            onChange={(e) => setForm({ ...form, career_page_url: e.target.value })}
            className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm"
          />
          <button
            onClick={handleAdd}
            className="w-full py-2 rounded-lg bg-green-600 text-white text-sm font-medium"
          >
            Save
          </button>
        </div>
      )}

      {companies.length === 0 ? (
        <p className="text-center text-gray-500 mt-8">No companies in your watchlist.</p>
      ) : (
        <div className="space-y-2">
          {companies.map((co) => (
            <div
              key={co.id}
              className="flex items-center justify-between bg-gray-900 rounded-lg p-3 border border-gray-800"
            >
              <div>
                <p className={`font-medium text-sm ${co.active ? "" : "text-gray-500 line-through"}`}>
                  {co.name}
                </p>
                <p className="text-xs text-gray-500">{co.ats_type}{co.ats_slug ? ` / ${co.ats_slug}` : ""}</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleToggle(co)}
                  className={`text-xs px-2 py-1 rounded ${co.active ? "bg-green-800 text-green-300" : "bg-gray-800 text-gray-500"}`}
                >
                  {co.active ? "Active" : "Paused"}
                </button>
                <button
                  onClick={() => handleDelete(co.id)}
                  className="text-xs px-2 py-1 rounded bg-red-900/50 text-red-400"
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\frontend\src\pages\Settings.tsx`
```tsx
import { useState, useEffect } from "react";
import { api } from "../api/client";
import type { ScanStatus } from "../types";

export default function Settings() {
  const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null);
  const [scanning, setScanning] = useState(false);

  useEffect(() => {
    api.getScanStatus().then(setScanStatus);
  }, []);

  const handleScan = async () => {
    setScanning(true);
    try {
      await api.triggerScan();
      // Poll status after a short delay
      setTimeout(async () => {
        const status = await api.getScanStatus();
        setScanStatus(status);
        setScanning(false);
      }, 2000);
    } catch {
      setScanning(false);
    }
  };

  return (
    <div className="pb-20 pt-4 px-4">
      <h1 className="text-xl font-bold mb-6">Settings</h1>

      <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 mb-4">
        <h2 className="font-semibold mb-3">Scanner</h2>
        {scanStatus && (
          <div className="text-sm text-gray-400 space-y-1 mb-4">
            <p>Last scan: {scanStatus.last_scan_at || "Never"}</p>
            <p>New jobs found: {scanStatus.last_scan_new_jobs}</p>
            <p>Status: {scanStatus.is_running ? "Running..." : "Idle"}</p>
          </div>
        )}
        <button
          onClick={handleScan}
          disabled={scanning}
          className="w-full py-2.5 rounded-lg bg-blue-600 text-white font-medium disabled:opacity-50"
        >
          {scanning ? "Scanning..." : "Scan Now"}
        </button>
      </div>

      <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
        <h2 className="font-semibold mb-2">About</h2>
        <p className="text-sm text-gray-400">JobFinder Agent v0.1.0</p>
        <p className="text-xs text-gray-600 mt-1">Autonomous job hunting pipeline</p>
      </div>
    </div>
  );
}
```

**Commit:** `feat: add Tracker, Companies, and Settings pages`

---

### Task 24 -- Frontend Component Test + PostCSS Config

**File:** `C:\Users\offir\Desktop\Projects\JobFinderAgent\frontend\postcss.config.js`
```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

**Run full frontend test suite:**
```bash
cd frontend && npx vitest run
```

**Run full backend test suite:**
```bash
cd backend && python -m pytest -v
```

**Commit:** `feat: complete PWA frontend with all pages and tests`

---

## Summary of All Commits (in order)

| # | Commit Message |
|---|---|
| 1 | `chore: scaffold project structure and dependencies` |
| 2 | `feat: add config module with pydantic-settings` |
| 3 | `feat: add database module and all SQLModel models` |
| 4 | `feat: add ATS fetcher for Greenhouse and Lever APIs` |
| 5 | `feat: add Scrapling fetcher for career pages and LinkedIn` |
| 6 | `feat: add normalizer with content_hash dedup` |
| 7 | `feat: add LLM prompt templates` |
| 8 | `feat: add AI matchmaker with OpenRouter integration` |
| 9 | `feat: add CV variant selector with tag-based fallback` |
| 10 | `feat: add Telegram notification sender` |
| 11 | `feat: add scheduler and scan orchestrator` |
| 12 | `feat: add auth middleware, main app, and test client fixture` |
| 13 | `feat: add matches API router` |
| 14 | `feat: add companies API router` |
| 15 | `feat: add tracker and applications API router` |
| 16 | `feat: add CV variants and scanner API routers` |
| 17 | `chore: add deployment scripts and systemd service` |
| 18 | `chore: scaffold React PWA frontend` |
| 19 | `feat: add TypeScript types and API client` |
| 20 | `feat: add App router, navigation, and useMatches hook` |
| 21 | `feat: add shared UI components` |
| 22 | `feat: add MatchQueue page with card tests` |
| 23 | `feat: add Tracker, Companies, and Settings pages` |
| 24 | `feat: complete PWA frontend with all pages and tests` |

## Full Test Run Commands

```bash
# Backend — all tests
cd backend && python -m pytest -v

# Backend — single module
cd backend && python -m pytest tests/test_config.py -v
cd backend && python -m pytest tests/test_models.py -v
cd backend && python -m pytest tests/test_ats_fetcher.py -v
cd backend && python -m pytest tests/test_normalizer.py -v
cd backend && python -m pytest tests/test_matchmaker.py -v
cd backend && python -m pytest tests/test_cv_selector.py -v
cd backend && python -m pytest tests/test_telegram.py -v
cd backend && python -m pytest tests/test_scheduler.py -v
cd backend && python -m pytest tests/test_api_matches.py -v
cd backend && python -m pytest tests/test_api_companies.py -v
cd backend && python -m pytest tests/test_api_tracker.py -v
cd backend && python -m pytest tests/test_api_scanner.py -v

# Frontend
cd frontend && npx vitest run
```

---

### Critical Files for Implementation

- `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\scheduler.py` - Central orchestrator that ties together all pipeline stages (fetch, normalize, match, notify)
- `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\pipeline\matchmaker.py` - Core AI scoring logic with OpenRouter integration and retry handling
- `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\routers\matches.py` - Primary API surface for the PWA, with joined queries across all models
- `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\tests\conftest.py` - Test infrastructure (in-memory DB, FastAPI TestClient with dependency overrides)
- `C:\Users\offir\Desktop\Projects\JobFinderAgent\backend\app\ingestion\normalizer.py` - Deduplication logic that prevents the pipeline from reprocessing seen jobs

---

## Plan Amendments (Post Self-Review)

Six critical gaps were identified in the self-review and are fixed here. Implement these alongside their parent tasks.

---

### Amendment A — Add `telegram_message_id` to Match model (fixes: duplicate Telegram sends)

**Applies to: Task 3 (Models) and Task 10 (Telegram)**

Add one field to `Match` in `backend/app/models/match.py`:
```python
telegram_message_id: Optional[int] = Field(default=None)
```

In `backend/app/notifications/telegram.py`, `send_match_notification()` must:
1. Check if `match.telegram_message_id` is already set → if so, return without sending
2. After sending, update the match row with the returned `message.message_id`

```python
async def send_match_notification(match_id: int, company: str, title: str,
                                   score: int, reasoning: str, pwa_base_url: str,
                                   db: Session) -> None:
    from app.models.match import Match
    match = db.get(Match, match_id)
    if match and match.telegram_message_id:
        return  # already sent — do not duplicate

    bot = Bot(token=settings.telegram_bot_token)
    text = format_match_message(company, title, score, reasoning, pwa_base_url, match_id)
    message = await bot.send_message(chat_id=settings.telegram_chat_id, text=text,
                                     parse_mode="HTML", disable_web_page_preview=True)
    if match:
        match.telegram_message_id = message.message_id
        db.add(match)
        db.commit()
```

**Test to add to `test_telegram.py`:**
```python
@pytest.mark.asyncio
async def test_no_duplicate_send(db: Session):
    """Should not send a second Telegram message if telegram_message_id is already set."""
    match = Match(job_id=1, score=80, reasoning="good", cv_variant_id=1,
                  status="new", telegram_message_id=999)
    db.add(match); db.commit(); db.refresh(match)

    with patch("app.notifications.telegram.Bot") as MockBot:
        await send_match_notification(match.id, "Co", "Dev", 80, "Good", "http://x", db)
        MockBot.return_value.send_message.assert_not_called()
```

---

### Amendment B — ATS Deep Link Pre-fill (fixes: Apply button opens generic URL)

**Applies to: Task 13 (Matches router)**

Add a helper `build_ats_apply_url()` to `backend/app/routers/matches.py`. When the user taps Apply, the backend constructs a pre-filled URL using known ATS query parameter conventions:

```python
from app.config import settings

# User contact info — add these to Settings / .env
# APPLICANT_FIRST_NAME, APPLICANT_LAST_NAME, APPLICANT_EMAIL,
# APPLICANT_LINKEDIN_URL, APPLICANT_PORTFOLIO_URL

def build_ats_apply_url(job_url: str, ats_type: str) -> str:
    """Construct pre-filled application URL for known ATS platforms."""
    from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

    first = getattr(settings, "applicant_first_name", "")
    last  = getattr(settings, "applicant_last_name", "")
    email = getattr(settings, "applicant_email", "")
    linkedin = getattr(settings, "applicant_linkedin_url", "")
    portfolio = getattr(settings, "applicant_portfolio_url", "")

    params: dict = {}
    if ats_type == "greenhouse":
        params = {"first_name": first, "last_name": last, "email": email,
                  "linkedin_profile": linkedin, "website": portfolio}
    elif ats_type == "lever":
        params = {"name": f"{first} {last}".strip(), "email": email,
                  "urls[LinkedIn]": linkedin, "urls[Portfolio]": portfolio}
    # workday / custom: return URL as-is (no standard pre-fill params)

    if not params:
        return job_url

    parsed = urlparse(job_url)
    qs = {k: v for k, v in params.items() if v}  # omit empty values
    return urlunparse(parsed._replace(query=urlencode(qs)))
```

Add these 5 fields to `Settings` in `backend/app/config.py` and `.env.example`:
```python
applicant_first_name: str = ""
applicant_last_name: str = ""
applicant_email: str = ""
applicant_linkedin_url: str = ""
applicant_portfolio_url: str = ""
```

`.env.example` additions:
```
APPLICANT_FIRST_NAME=Offir
APPLICANT_LAST_NAME=YourLastName
APPLICANT_EMAIL=your@email.com
APPLICANT_LINKEDIN_URL=https://linkedin.com/in/yourhandle
APPLICANT_PORTFOLIO_URL=https://yourportfolio.com
```

In the `POST /matches/{id}/applied` handler, replace the raw `ats_url` passthrough with:
```python
# Build pre-filled URL if ats_url not provided by client
if not body.ats_url:
    job = db.get(Job, match.job_id)
    company = db.get(Company, job.company_id) if job else None
    ats_type = company.ats_type if company else "custom"
    ats_url = build_ats_apply_url(job.url if job else "", ats_type)
else:
    ats_url = body.ats_url
```

**Test to add to `test_api_matches.py`:**
```python
def test_apply_generates_prefilled_greenhouse_url(client, db, monkeypatch):
    monkeypatch.setenv("APPLICANT_EMAIL", "test@example.com")
    monkeypatch.setenv("APPLICANT_FIRST_NAME", "Test")
    _, _, _, match = _seed_match(db)  # ats_type="greenhouse"

    resp = client.post(f"/matches/{match.id}/applied", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "email=test%40example.com" in data["ats_url"] or "email=test@example.com" in data["ats_url"]
```

---

### Amendment C — CV Variant Ambiguity Picker UI (fixes: tie between two variants silently picks first)

**Applies to: Task 22 (MatchQueue page)**

When `GET /matches/{id}` returns `cv_variant_id: null` and the match status is `new`, the frontend should check for ambiguous variants.

Add to `GET /matches/{id}` response schema in `backend/app/routers/matches.py`:
```python
class MatchDetail(BaseModel):
    ...
    cv_variant_id: Optional[int]
    ambiguous_variants: list[CVVariantOut] = []  # populated when selector returns 2 variants
```

Update `POST /matches/{id}/applied` to accept the user's chosen variant when ambiguous:
```python
class ApplyRequest(BaseModel):
    ats_url: Optional[str] = None
    chosen_cv_variant_id: Optional[int] = None  # required if ambiguous_variants is non-empty
```

In the MatchQueue page (`frontend/src/pages/MatchQueue.tsx`), add an `AmbiguousVariantPicker` inline component:
```tsx
{match.ambiguous_variants.length > 1 && !chosenVariantId && (
  <div className="bg-yellow-900/30 border border-yellow-700/50 rounded-xl p-4 mb-4">
    <p className="text-sm text-yellow-300 font-medium mb-3">
      Two CVs are equally good — pick one:
    </p>
    <div className="space-y-2">
      {match.ambiguous_variants.map((v) => (
        <button
          key={v.id}
          onClick={() => setChosenVariantId(v.id)}
          className="w-full text-left px-4 py-3 rounded-lg bg-gray-800 border border-gray-700 text-sm hover:border-yellow-600"
        >
          <span className="font-medium text-white">{v.name}</span>
          <span className="ml-2 text-gray-400">{JSON.parse(v.focus_tags || "[]").join(", ")}</span>
        </button>
      ))}
    </div>
  </div>
)}
```

Disable the Apply button until a variant is chosen when ambiguous:
```tsx
const canApply = match.ambiguous_variants.length <= 1 || chosenVariantId !== null;
```

---

### Amendment D — Near-Misses PWA Route (fixes: API exists but unreachable from UI)

**Applies to: Task 20 (App router) and Task 23 (pages)**

Add `/near-misses` route to `frontend/src/App.tsx`:
```tsx
<Route path="/near-misses" element={<NearMisses />} />
```

Create `frontend/src/pages/NearMisses.tsx`:
```tsx
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { MatchListItem } from "../types";
import StatusBadge from "../components/StatusBadge";

export default function NearMisses() {
  const [items, setItems] = useState<MatchListItem[]>([]);

  useEffect(() => {
    api.get("/matches/near-misses").then((r) => setItems(r.data));
  }, []);

  return (
    <div className="min-h-screen bg-gray-950 text-white pb-24">
      <div className="sticky top-0 bg-gray-950/95 backdrop-blur z-10 px-4 py-4 border-b border-gray-800">
        <h1 className="text-lg font-semibold">Near Misses</h1>
        <p className="text-xs text-gray-500">Jobs scored below your threshold — review manually</p>
      </div>
      {items.length === 0 ? (
        <p className="text-center text-gray-500 mt-12">No near misses yet.</p>
      ) : (
        <div className="space-y-2 p-4">
          {items.map((m) => (
            <div key={m.id} className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-semibold text-sm">{m.job_title}</p>
                  <p className="text-xs text-gray-400">{m.company_name}</p>
                </div>
                <StatusBadge score={m.score} status={m.status} />
              </div>
              <p className="text-xs text-gray-500 mt-2">{m.reasoning}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

Add link to Near Misses in the bottom nav (`frontend/src/App.tsx` nav section):
```tsx
<NavLink to="/near-misses" className={navClass}>
  <span className="text-lg">📉</span>
  <span className="text-xs">Near Misses</span>
</NavLink>
```

---

### Amendment E — Unconfirmed Apply Reminder Badge (fixes: 48h reminder missing)

**Applies to: Task 23 (Tracker page)**

No scheduler needed — compute client-side in the Tracker. In `frontend/src/pages/Tracker.tsx`, add a badge next to unconfirmed applications:

```tsx
function isUnconfirmedOverdue(app: Application): boolean {
  if (app.confirmed_at) return false;
  if (!app.applied_at) return false;
  const elapsed = Date.now() - new Date(app.applied_at).getTime();
  return elapsed > 48 * 60 * 60 * 1000; // 48 hours in ms
}

// In render:
{isUnconfirmedOverdue(app) && (
  <span className="ml-2 text-xs bg-yellow-900/50 text-yellow-400 px-2 py-0.5 rounded-full">
    Did you submit?
  </span>
)}
```

---

### Amendment F — Frontend `.env.example` (fixes: missing config for Vite)

**Applies to: Task 18 (Frontend scaffold)**

Create `frontend/.env.example`:
```
VITE_API_URL=http://your-vm-ip:8000
VITE_ACCESS_TOKEN=changeme
```

Create `frontend/.env.local` (gitignored) with actual values during development. The `frontend/src/api/client.ts` already reads from `import.meta.env.VITE_API_URL` and `import.meta.env.VITE_ACCESS_TOKEN`. The `.gitignore` already excludes `.env.local`.

Add to `.gitignore`:
```
frontend/.env.local
```