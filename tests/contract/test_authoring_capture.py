"""Contract tests for capture tools (issue #106).

Spec: docs/specs/authoring-connector.md (CAP-1..CAP-5).

Tools are driven through the in-memory MCP client. Each test repoints
``app.db.engine`` at a fresh in-memory database, which the tools' write session
picks up via its lazy import.
"""

import asyncio

import pytest
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.mcp_server import build_mcp

TOKEN = "test-connector-token"


@pytest.fixture
def engine(monkeypatch):
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(eng)
    monkeypatch.setattr("app.db.engine", eng)
    return eng


def _call(name, args):
    mcp = build_mcp(TOKEN)

    async def _run():
        from fastmcp import Client

        async with Client(mcp) as c:
            return await c.call_tool(name, args)

    return asyncio.run(_run())


def _seed_theme(engine, body_md="seed", visibility="draft"):
    from app.models import Theme, Visibility

    with Session(engine) as s:
        theme = Theme(body_md=body_md, visibility=Visibility(visibility))
        s.add(theme)
        s.commit()
        s.refresh(theme)
        return theme.id


def test_CAP_1_add_breadcrumb_creates(engine):
    # WHEN add_breadcrumb is called with a valid theme id and content
    # THEN a breadcrumb is created and its id + timestamp are returned.
    theme_id = _seed_theme(engine)
    res = _call("add_breadcrumb", {"theme_id": theme_id, "body_md": "a thought"})
    assert res.data["id"] is not None
    assert res.data["created_at"]

    from app.models import Breadcrumb

    with Session(engine) as s:
        rows = s.exec(select(Breadcrumb).where(Breadcrumb.theme_id == theme_id)).all()
    assert len(rows) == 1
    assert rows[0].body_md == "a thought"


def test_CAP_2_add_breadcrumb_missing_theme(engine):
    # WHEN add_breadcrumb references a non-existent theme id
    # THEN the tool returns a clear not-found error, not a 500.
    with pytest.raises(Exception) as excinfo:
        _call("add_breadcrumb", {"theme_id": 999999, "body_md": "orphan"})
    assert "not found" in str(excinfo.value).lower()


def test_CAP_3_create_theme_defaults_draft(engine):
    # WHEN create_theme is called with no publish flag THEN it is a draft.
    res = _call("create_theme", {"body_md": "a quiet idea"})
    assert res.data["visibility"] == "draft"


def test_CAP_4_create_theme_publish_true(engine):
    # WHEN create_theme is called with publish=true THEN it is published.
    res = _call("create_theme", {"body_md": "a loud idea", "publish": True})
    assert res.data["visibility"] == "published"


def test_CAP_5_suggest_tags_returns_without_applying(engine, monkeypatch):
    # WHEN suggest_tags is called THEN suggestions are returned and none applied.
    monkeypatch.setattr("app.api.suggest_tags", lambda body, existing: ["memory", "ritual"])
    theme_id = _seed_theme(engine, body_md="on remembering")

    res = _call("suggest_tags", {"theme_id": theme_id})
    assert res.data["tags"] == ["memory", "ritual"]

    from app.models import Theme

    with Session(engine) as s:
        theme = s.get(Theme, theme_id)
        assert theme.tags == []  # nothing applied
