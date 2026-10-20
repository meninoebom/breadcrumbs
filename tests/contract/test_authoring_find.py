"""Contract tests for find tools (issue #107).

Spec: docs/specs/authoring-connector.md (FIND-1, FIND-2).
"""

import asyncio
from datetime import datetime, timezone

import pytest
from sqlmodel import Session, SQLModel, create_engine
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


def _add_theme(engine, body_md, created_at=None, breadcrumb=None, tag=None):
    from app.models import Breadcrumb, Tag, Theme, Visibility

    with Session(engine) as s:
        theme = Theme(body_md=body_md, visibility=Visibility.draft)
        if created_at is not None:
            theme.created_at = created_at
        if tag is not None:
            theme.tags = [Tag(name=tag)]
        s.add(theme)
        s.commit()
        s.refresh(theme)
        tid = theme.id
        if breadcrumb is not None:
            s.add(Breadcrumb(body_md=breadcrumb, theme_id=tid))
            s.commit()
        return tid


def test_FIND_1_list_recent_returns_fields_newest_first(engine):
    _add_theme(engine, "older", created_at=datetime(2020, 1, 1, tzinfo=timezone.utc))
    _add_theme(engine, "newer", created_at=datetime(2021, 1, 1, tzinfo=timezone.utc))

    rows = _call("list_recent_themes", {"limit": 10}).data
    assert rows[0]["body_md"] == "newer"
    assert {"id", "visibility", "tags"} <= set(rows[0].keys())


def test_FIND_2_search_matches_body_breadcrumb_tag(engine):
    by_body = _add_theme(engine, "quantum mechanics")
    by_crumb = _add_theme(engine, "plain one", breadcrumb="a note about quantum stuff")
    by_tag = _add_theme(engine, "plain two", tag="quantum")
    unrelated = _add_theme(engine, "nothing relevant here")

    ids = {r["id"] for r in _call("search_themes", {"query": "quantum"}).data}
    assert {by_body, by_crumb, by_tag} <= ids
    assert unrelated not in ids
