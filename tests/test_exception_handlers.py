"""Tests for global database exception handlers."""

from unittest.mock import patch

from sqlalchemy.exc import DataError, IntegrityError, OperationalError


def test_integrity_error_returns_409(client):
    """IntegrityError from unhandled constraint violation returns 409."""
    with patch(
        "app.api.Session.get",
        side_effect=IntegrityError("mock", {}, Exception("unique violation")),
    ):
        r = client.get("/api/themes/1")
    assert r.status_code == 409
    assert r.json()["detail"] == "Conflict: a database constraint was violated"
    assert "SQL" not in r.json()["detail"]


def test_operational_error_returns_503(client):
    """OperationalError (e.g. connection failure) returns 503."""
    with patch(
        "app.api.Session.get",
        side_effect=OperationalError("mock", {}, Exception("connection refused")),
    ):
        r = client.get("/api/themes/1")
    assert r.status_code == 503
    assert r.json()["detail"] == "Service temporarily unavailable"


def test_data_error_returns_400(client):
    """DataError (e.g. invalid column value) returns 400."""
    with patch(
        "app.api.Session.get",
        side_effect=DataError("mock", {}, Exception("invalid input")),
    ):
        r = client.get("/api/themes/1")
    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid data submitted"
