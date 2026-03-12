"""Tests for API key and JWT authentication."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.api import app
from app.db import get_session


@pytest.fixture(name="auth_client")
def auth_client_fixture():
    """TestClient WITHOUT auth overrides — tests real auth paths."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

    SQLModel.metadata.drop_all(engine)


@patch("app.auth.API_KEY", "test-secret-key")
def test_valid_api_key(auth_client):
    r = auth_client.get("/api/themes", headers={"X-API-Key": "test-secret-key"})
    assert r.status_code == 200


@patch("app.auth.API_KEY", "test-secret-key")
def test_invalid_api_key(auth_client):
    r = auth_client.post(
        "/api/themes",
        json={"body_md": "Test"},
        headers={"X-API-Key": "wrong"},
    )
    assert r.status_code == 401


@patch("app.auth.API_KEY", "")
def test_api_key_disabled_when_env_unset(auth_client):
    """When API_KEY env var is empty, any X-API-Key header should fail."""
    r = auth_client.post(
        "/api/themes",
        json={"body_md": "Test"},
        headers={"X-API-Key": "anything"},
    )
    assert r.status_code == 401


def test_no_auth_headers(auth_client):
    r = auth_client.get("/api/themes")
    assert r.status_code == 200  # GET /themes is public


@patch("app.auth.API_KEY", "test-secret-key")
def test_api_key_on_protected_route(auth_client):
    """API key should grant access to admin-protected endpoints."""
    r = auth_client.post(
        "/api/themes",
        json={"body_md": "Test theme"},
        headers={"X-API-Key": "test-secret-key"},
    )
    assert r.status_code == 201
