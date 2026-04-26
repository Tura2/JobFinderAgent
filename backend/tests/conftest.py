import os
os.environ.setdefault("SESSION_SECRET_KEY", "test-secret-key-for-testing-32chars!")
os.environ.setdefault("PWA_ACCESS_TOKEN", "changeme")

import pytest
from sqlmodel import SQLModel, Session, create_engine
from fastapi.testclient import TestClient

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
    from app.middleware.session import make_session_cookie
    from app.config import settings

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session

    cookie_val = make_session_cookie(settings.session_secret_key, settings.session_max_age_days)

    with TestClient(app, follow_redirects=False) as c:
        c.cookies.set("session", cookie_val)
        yield c

    app.dependency_overrides.clear()
