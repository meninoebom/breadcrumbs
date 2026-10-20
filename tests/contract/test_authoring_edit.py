"""Contract tests for edit + publish tools (issue #108).

Spec: docs/specs/authoring-connector.md (EDIT-1, EDIT-2, PUB-1, PUB-2).
"""

import asyncio

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


def _seed_theme(engine, body_md="theme body", visibility="draft"):
    from app.models import Theme, Visibility

    with Session(engine) as s:
        theme = Theme(body_md=body_md, visibility=Visibility(visibility))
        s.add(theme)
        s.commit()
        s.refresh(theme)
        return theme.id


def _seed_breadcrumb(engine, theme_id, body_md="original"):
    from app.models import Breadcrumb

    with Session(engine) as s:
        bc = Breadcrumb(body_md=body_md, theme_id=theme_id)
        s.add(bc)
        s.commit()
        s.refresh(bc)
        return bc.id


def _theme_visibility(engine, theme_id):
    from app.models import Theme

    with Session(engine) as s:
        return s.get(Theme, theme_id).visibility.value


def test_EDIT_1_update_breadcrumb_replaces(engine):
    theme_id = _seed_theme(engine)
    bc_id = _seed_breadcrumb(engine, theme_id, body_md="original")

    res = _call("update_breadcrumb", {"breadcrumb_id": bc_id, "body_md": "revised"})
    assert res.data["body_md"] == "revised"

    from app.models import Breadcrumb

    with Session(engine) as s:
        assert s.get(Breadcrumb, bc_id).body_md == "revised"


def test_EDIT_2_update_theme_partial(engine):
    theme_id = _seed_theme(engine, body_md="orig", visibility="draft")

    res = _call("update_theme", {"theme_id": theme_id, "body_md": "edited"})
    assert res.data["body_md"] == "edited"
    assert res.data["visibility"] == "draft"  # untouched


def test_PUB_1_publish_makes_visible(engine):
    theme_id = _seed_theme(engine, visibility="draft")

    res = _call("publish_theme", {"theme_id": theme_id})
    assert res.data["visibility"] == "published"
    assert _theme_visibility(engine, theme_id) == "published"


def test_PUB_2_unpublish_removes_from_feed(engine):
    theme_id = _seed_theme(engine, visibility="published")

    res = _call("unpublish_theme", {"theme_id": theme_id})
    assert res.data["visibility"] == "draft"
    assert _theme_visibility(engine, theme_id) == "draft"
