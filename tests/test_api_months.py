"""API tests for the rolling-window feed endpoints: GET /api/months and
the `since` / `month` query params on GET /api/themes."""

from datetime import date, datetime, timedelta, timezone

from app.models import Digest, DigestStatus, DigestType, Theme, Visibility


def _make_theme(session, body: str, created_at: datetime, published: bool = True) -> Theme:
    theme = Theme(
        body_md=body,
        visibility=Visibility.published if published else Visibility.draft,
        created_at=created_at,
    )
    session.add(theme)
    session.flush()
    session.refresh(theme)
    return theme


def test_list_months_empty_when_all_content_is_recent(client, session):
    now = datetime.now(timezone.utc)
    _make_theme(session, "recent", now - timedelta(days=5))
    session.commit()

    response = client.get("/api/months")
    assert response.status_code == 200
    assert response.json() == []


def test_list_months_returns_old_months_with_counts(client, session):
    now = datetime.now(timezone.utc)
    # Two themes in a month that's definitely fully outside the 31-day window.
    old = now - timedelta(days=120)
    _make_theme(session, "old 1", old)
    _make_theme(session, "old 2", old)
    _make_theme(session, "recent", now - timedelta(days=2))
    session.commit()

    response = client.get("/api/months")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    entry = data[0]
    assert entry["year"] == old.year
    assert entry["month"] == old.month
    assert entry["theme_count"] == 2
    assert entry["monthly_digest"] is None


def test_list_months_skips_draft_themes(client, session):
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=120)
    _make_theme(session, "draft", old, published=False)
    session.commit()

    response = client.get("/api/months")
    assert response.status_code == 200
    assert response.json() == []


def test_list_months_attaches_monthly_digest(client, session):
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=120)
    _make_theme(session, "old", old)

    digest = Digest(
        title=f"{old.strftime('%B')} summary",
        summary_md="Summary of the month",
        digest_type=DigestType.monthly,
        period_start=date(old.year, old.month, 1),
        period_end=date(old.year, old.month, 28),
        status=DigestStatus.published,
    )
    session.add(digest)
    session.commit()

    response = client.get("/api/months")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["monthly_digest"] is not None
    assert data[0]["monthly_digest"]["digest_type"] == "monthly"
    assert data[0]["monthly_digest"]["summary_md"] == "Summary of the month"


def test_themes_since_param_lifts_the_cap(client, session):
    # Create 25 themes within the last week — more than the default 20 cap.
    now = datetime.now(timezone.utc)
    for i in range(25):
        _make_theme(session, f"theme {i}", now - timedelta(hours=i))
    session.commit()

    since = (now - timedelta(days=7)).date().isoformat()
    response = client.get(f"/api/themes?since={since}")
    assert response.status_code == 200
    assert len(response.json()) == 25


def test_themes_month_param_returns_only_that_month(client, session):
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=120)
    _make_theme(session, "in month", old)
    _make_theme(session, "other month", old - timedelta(days=60))
    _make_theme(session, "recent", now - timedelta(days=2))
    session.commit()

    month_str = f"{old.year:04d}-{old.month:02d}"
    response = client.get(f"/api/themes?month={month_str}")
    assert response.status_code == 200
    bodies = {t["body_md"] for t in response.json()}
    assert bodies == {"in month"}


def test_themes_month_param_rejects_invalid_format(client):
    response = client.get("/api/themes?month=2026")
    assert response.status_code == 400


def test_themes_without_scope_still_paginates(client, session):
    now = datetime.now(timezone.utc)
    for i in range(25):
        _make_theme(session, f"theme {i}", now - timedelta(hours=i))
    session.commit()

    response = client.get("/api/themes")
    assert response.status_code == 200
    # Default cap is 20 when no scoped filter is present.
    assert len(response.json()) == 20
