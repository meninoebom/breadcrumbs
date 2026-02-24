"""Pytest configuration and fixtures for breadcrumbs tests."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

# Import models to ensure they're registered before creating tables
from app.models import Breadcrumb, Digest, DigestSend, Subscriber, Tag, Theme, ThemeTag
from app.api import app
from app.auth import require_admin
from app.db import get_session


@pytest.fixture(name="session")
def session_fixture():
    """Create a fresh in-memory SQLite database for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session
        session.rollback()

    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create a TestClient with the session dependency overridden."""

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[require_admin] = lambda: None
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
