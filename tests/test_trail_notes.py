"""Tests for Trail Notes: digests, subscribers, sending, and cron."""

import secrets
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import select

from app.models import (
    Digest,
    DigestSend,
    DigestStatus,
    SendStatus,
    Subscriber,
    Theme,
    Breadcrumb,
    Visibility,
)
from app.trail_notes.generate import gather_week_content, get_current_week_bounds
from app.trail_notes.send import markdown_to_html


# ── helpers ──────────────────────────────────────────────────────────


def _make_digest(session, *, status=DigestStatus.draft, period_start=None) -> Digest:
    if period_start is None:
        period_start = date(2026, 2, 17)
    digest = Digest(
        title="Test digest",
        summary_md="Some **markdown** prose.",
        period_start=period_start,
        period_end=period_start + timedelta(days=6),
        status=status,
    )
    session.add(digest)
    session.flush()
    session.refresh(digest)
    return digest


def _make_subscriber(session, *, email="reader@example.com", confirmed=True, unsubscribed=False) -> Subscriber:
    sub = Subscriber(
        email=email,
        confirmation_token=secrets.token_urlsafe(48),
        unsubscribe_token=secrets.token_urlsafe(48),
    )
    if confirmed:
        sub.confirmed_at = datetime.now(timezone.utc)
    if unsubscribed:
        sub.unsubscribed_at = datetime.now(timezone.utc)
    session.add(sub)
    session.flush()
    session.refresh(sub)
    return sub


# ── markdown_to_html ─────────────────────────────────────────────────


def test_markdown_to_html_basic():
    html = markdown_to_html("Hello **world**")
    assert "<strong>world</strong>" in html


def test_markdown_to_html_escapes_raw_html():
    html = markdown_to_html('<script>alert("xss")</script>')
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


# ── get_current_week_bounds ──────────────────────────────────────────


def test_get_current_week_bounds_returns_monday_sunday():
    start, end = get_current_week_bounds()
    assert start.weekday() == 0  # Monday
    assert end.weekday() == 6  # Sunday
    assert end - start == timedelta(days=6)
    assert end < date.today()


# ── gather_week_content ──────────────────────────────────────────────


def test_gather_week_content_empty_when_no_themes(session):
    result = gather_week_content(session, date(2026, 2, 17), date(2026, 2, 23))
    assert result == ""


def test_gather_week_content_includes_published_themes(session):
    theme = Theme(body_md="Thinking about recursion", visibility=Visibility.published)
    theme.created_at = datetime(2026, 2, 18, 12, 0, tzinfo=timezone.utc)
    session.add(theme)
    session.flush()
    session.refresh(theme)

    bc = Breadcrumb(body_md="First breadcrumb", theme_id=theme.id)
    bc.created_at = datetime(2026, 2, 18, 13, 0, tzinfo=timezone.utc)
    session.add(bc)
    session.flush()

    result = gather_week_content(session, date(2026, 2, 17), date(2026, 2, 23))
    assert "Thinking about recursion" in result
    assert "First breadcrumb" in result


def test_gather_week_content_excludes_drafts(session):
    theme = Theme(body_md="Draft thought", visibility=Visibility.draft)
    theme.created_at = datetime(2026, 2, 18, 12, 0, tzinfo=timezone.utc)
    session.add(theme)
    session.flush()

    result = gather_week_content(session, date(2026, 2, 17), date(2026, 2, 23))
    assert result == ""


# ── public digest endpoints ──────────────────────────────────────────


def test_list_digests_empty(client):
    resp = client.get("/api/digests")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_digests_returns_published_and_sent(client, session):
    _make_digest(session, status=DigestStatus.published, period_start=date(2026, 2, 10))
    _make_digest(session, status=DigestStatus.sent, period_start=date(2026, 2, 17))
    _make_digest(session, status=DigestStatus.draft, period_start=date(2026, 2, 24))
    session.commit()

    resp = client.get("/api/digests")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # Newest first
    assert data[0]["period_start"] == "2026-02-17"


def test_get_digest_not_found(client):
    resp = client.get("/api/digests/999")
    assert resp.status_code == 404


def test_get_digest_by_id(client, session):
    d = _make_digest(session, status=DigestStatus.published)
    session.commit()
    resp = client.get(f"/api/digests/{d.id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Test digest"


# ── publish endpoint ─────────────────────────────────────────────────


def test_publish_digest(client, session):
    d = _make_digest(session, status=DigestStatus.draft)
    session.commit()
    resp = client.post(f"/api/digests/{d.id}/publish")
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"


def test_publish_already_published(client, session):
    d = _make_digest(session, status=DigestStatus.published)
    session.commit()
    resp = client.post(f"/api/digests/{d.id}/publish")
    assert resp.status_code == 400


def test_publish_not_found(client):
    resp = client.post("/api/digests/999/publish")
    assert resp.status_code == 404


# ── send endpoint ────────────────────────────────────────────────────


@patch("app.trail_notes.routes.send_digest_to_subscribers")
def test_send_digest(mock_send, client, session):
    d = _make_digest(session, status=DigestStatus.published)
    session.commit()
    mock_send.return_value = {"sent": 1, "failed": 0, "skipped": 0}
    resp = client.post(f"/api/digests/{d.id}/send")
    assert resp.status_code == 200
    assert resp.json()["sent"] == 1


def test_send_draft_rejected(client, session):
    d = _make_digest(session, status=DigestStatus.draft)
    session.commit()
    resp = client.post(f"/api/digests/{d.id}/send")
    assert resp.status_code == 400
    assert "Publish" in resp.json()["detail"]


def test_send_already_sent_rejected(client, session):
    d = _make_digest(session, status=DigestStatus.sent)
    session.commit()
    resp = client.post(f"/api/digests/{d.id}/send")
    assert resp.status_code == 400
    assert "already" in resp.json()["detail"]


# ── send-test endpoint ──────────────────────────────────────────────


@patch("app.trail_notes.routes.send_test_email")
def test_send_test_success(mock_send, client, session):
    d = _make_digest(session)
    session.commit()
    resp = client.post(
        f"/api/digests/{d.id}/send-test",
        json={"email": "test@example.com"},
    )
    assert resp.status_code == 200
    assert "test@example.com" in resp.json()["message"]
    mock_send.assert_called_once()


@patch("app.trail_notes.routes.send_test_email", side_effect=RuntimeError("SMTP down"))
def test_send_test_failure(mock_send, client, session):
    d = _make_digest(session)
    session.commit()
    resp = client.post(
        f"/api/digests/{d.id}/send-test",
        json={"email": "test@example.com"},
    )
    assert resp.status_code == 502


# ── send_digest_to_subscribers (unit) ────────────────────────────────


@patch("app.trail_notes.send._send_one")
def test_send_to_subscribers_happy_path(mock_send_one, session):
    from app.trail_notes.send import send_digest_to_subscribers

    d = _make_digest(session, status=DigestStatus.published)
    sub = _make_subscriber(session)
    session.flush()

    result = send_digest_to_subscribers(session, d)
    assert result == {"sent": 1, "failed": 0, "skipped": 0}
    mock_send_one.assert_called_once()

    # Digest should be marked sent
    session.refresh(d)
    assert d.status == DigestStatus.sent
    assert d.sent_at is not None


@patch("app.trail_notes.send._send_one")
def test_send_skips_already_sent(mock_send_one, session):
    from app.trail_notes.send import send_digest_to_subscribers

    d = _make_digest(session, status=DigestStatus.published)
    sub = _make_subscriber(session)
    session.flush()

    # First send
    send_digest_to_subscribers(session, d)
    mock_send_one.reset_mock()

    # Reset digest status to test idempotency of send records
    d.status = DigestStatus.published
    session.flush()

    result = send_digest_to_subscribers(session, d)
    assert result == {"sent": 0, "failed": 0, "skipped": 1}
    mock_send_one.assert_not_called()


@patch("app.trail_notes.send._send_one", side_effect=Exception("delivery failed"))
def test_send_all_fail_leaves_published(mock_send_one, session):
    from app.trail_notes.send import send_digest_to_subscribers

    d = _make_digest(session, status=DigestStatus.published)
    _make_subscriber(session)
    session.flush()

    result = send_digest_to_subscribers(session, d)
    assert result["sent"] == 0
    assert result["failed"] == 1

    session.refresh(d)
    assert d.status == DigestStatus.published  # NOT sent


@patch("app.trail_notes.send._send_one")
def test_send_excludes_unconfirmed_and_unsubscribed(mock_send_one, session):
    from app.trail_notes.send import send_digest_to_subscribers

    d = _make_digest(session, status=DigestStatus.published)
    _make_subscriber(session, email="unconfirmed@example.com", confirmed=False)
    _make_subscriber(session, email="unsub@example.com", confirmed=True, unsubscribed=True)
    session.flush()

    result = send_digest_to_subscribers(session, d)
    assert result == {"sent": 0, "failed": 0, "skipped": 0}
    mock_send_one.assert_not_called()


# ── subscriber endpoints ─────────────────────────────────────────────


@patch("app.trail_notes.routes.send_confirmation_email")
def test_subscribe_new_email(mock_email, client):
    resp = client.post(
        "/api/subscribers/subscribe",
        json={"email": "new@example.com"},
    )
    assert resp.status_code == 200
    assert "inbox" in resp.json()["message"].lower()
    mock_email.assert_called_once()


@patch("app.trail_notes.routes.send_confirmation_email")
def test_subscribe_already_active(mock_email, client, session):
    _make_subscriber(session, email="active@example.com", confirmed=True)
    session.commit()

    resp = client.post(
        "/api/subscribers/subscribe",
        json={"email": "active@example.com"},
    )
    assert resp.status_code == 200
    assert "already" in resp.json()["message"].lower()
    mock_email.assert_not_called()


@patch("app.trail_notes.routes.send_confirmation_email")
def test_subscribe_resubscribe_after_unsubscribe(mock_email, client, session):
    _make_subscriber(session, email="back@example.com", confirmed=True, unsubscribed=True)
    session.commit()

    resp = client.post(
        "/api/subscribers/subscribe",
        json={"email": "back@example.com"},
    )
    assert resp.status_code == 200
    assert "inbox" in resp.json()["message"].lower()
    mock_email.assert_called_once()


@patch("app.trail_notes.routes.send_confirmation_email", side_effect=Exception("Resend down"))
def test_subscribe_email_failure_returns_502(mock_email, client):
    resp = client.post(
        "/api/subscribers/subscribe",
        json={"email": "fail@example.com"},
    )
    assert resp.status_code == 502


def test_confirm_subscription(client, session):
    sub = _make_subscriber(session, confirmed=False)
    session.commit()

    resp = client.get(f"/api/subscribers/confirm?token={sub.confirmation_token}")
    assert resp.status_code == 200
    assert "confirmed" in resp.json()["message"].lower()

    session.refresh(sub)
    assert sub.is_confirmed


def test_confirm_invalid_token(client):
    resp = client.get("/api/subscribers/confirm?token=bogus")
    assert resp.status_code == 404


def test_confirm_idempotent(client, session):
    sub = _make_subscriber(session, confirmed=True)
    session.commit()

    resp = client.get(f"/api/subscribers/confirm?token={sub.confirmation_token}")
    assert resp.status_code == 200


def test_unsubscribe(client, session):
    sub = _make_subscriber(session, confirmed=True)
    session.commit()

    resp = client.get(f"/api/subscribers/unsubscribe?token={sub.unsubscribe_token}")
    assert resp.status_code == 200
    assert "unsubscribed" in resp.json()["message"].lower()

    session.refresh(sub)
    assert sub.unsubscribed_at is not None


def test_unsubscribe_invalid_token(client):
    resp = client.get("/api/subscribers/unsubscribe?token=bogus")
    assert resp.status_code == 404


def test_unsubscribe_idempotent(client, session):
    sub = _make_subscriber(session, confirmed=True, unsubscribed=True)
    session.commit()

    resp = client.get(f"/api/subscribers/unsubscribe?token={sub.unsubscribe_token}")
    assert resp.status_code == 200


# ── cron endpoint ────────────────────────────────────────────────────


@patch.dict("os.environ", {"CRON_SECRET": "s3cret"})
@patch("app.trail_notes.routes.generate_digest")
@patch("app.trail_notes.routes.get_current_week_bounds", return_value=(date(2026, 2, 17), date(2026, 2, 23)))
def test_cron_generates_draft(mock_bounds, mock_gen, client, session):
    digest = _make_digest(session)
    session.commit()
    mock_gen.return_value = digest

    resp = client.post("/api/internal/weekly-digest?secret=s3cret")
    # Existing digest for this period_start means "existed"
    assert resp.status_code == 201
    assert resp.json()["action"] == "existed"


@patch.dict("os.environ", {"CRON_SECRET": "s3cret"})
def test_cron_rejects_bad_secret(client):
    resp = client.post("/api/internal/weekly-digest?secret=wrong")
    assert resp.status_code == 403


@patch.dict("os.environ", {"CRON_SECRET": ""})
def test_cron_rejects_empty_secret(client):
    resp = client.post("/api/internal/weekly-digest?secret=anything")
    assert resp.status_code == 403


# ── generate endpoint ────────────────────────────────────────────────


@patch("app.trail_notes.routes.generate_digest")
def test_generate_digest_endpoint(mock_gen, client, session):
    digest = _make_digest(session)
    session.commit()
    mock_gen.return_value = digest

    resp = client.post("/api/digests/generate?period_start=2026-03-01&period_end=2026-03-07")
    assert resp.status_code == 201


@patch("app.trail_notes.routes.generate_digest")
def test_generate_digest_conflict(mock_gen, client, session):
    _make_digest(session, period_start=date(2026, 2, 17))
    session.commit()

    resp = client.post("/api/digests/generate?period_start=2026-02-17&period_end=2026-02-23")
    assert resp.status_code == 409


# ── Subscriber model properties ──────────────────────────────────────


def test_subscriber_is_confirmed_false_by_default(session):
    sub = _make_subscriber(session, confirmed=False)
    assert not sub.is_confirmed
    assert not sub.is_active


def test_subscriber_is_active_when_confirmed(session):
    sub = _make_subscriber(session, confirmed=True)
    assert sub.is_confirmed
    assert sub.is_active


def test_subscriber_not_active_when_unsubscribed(session):
    sub = _make_subscriber(session, confirmed=True, unsubscribed=True)
    assert sub.is_confirmed
    assert not sub.is_active
