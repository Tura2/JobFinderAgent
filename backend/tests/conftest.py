import os

import pytest
from sqlmodel import SQLModel, Session, create_engine
from fastapi.testclient import TestClient

# Ensure required env vars are set before any app module is imported at
# collection time (Settings() is instantiated at module level in config.py).
os.environ.setdefault("SESSION_SECRET_KEY", "test-secret")

import app.models  # noqa: F401 — register all models with metadata


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
