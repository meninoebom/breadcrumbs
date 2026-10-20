"""MCP authoring server, mounted at ``/mcp`` on the main FastAPI app.

This is the transport that lets an agent (the Claude app as a custom connector)
author crumb.blog content from a phone.

Security model: a single auth gate. Every request to ``/mcp`` must carry a bearer
token matching ``MCP_CONNECTOR_TOKEN``, verified at the transport by
``StaticTokenVerifier``. Past that gate the tools run in-process as the trusted
admin principal, writing through the same models the REST API uses. There is no
second credential and no self-HTTP hop.

Fail-safe: when ``MCP_CONNECTOR_TOKEN`` is unset, :func:`build_mcp` returns
``None`` and ``/mcp`` is never mounted, so no unauthenticated path to the
authoring tools can exist.
"""

import os
from contextlib import contextmanager
from typing import Optional

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.auth import StaticTokenVerifier

# auth.py-style gotcha: this module reads env at import/build time, so load the
# dotenv here rather than relying on another module having loaded it first.
load_dotenv()

SERVER_NAME = "Breadcrumbs Authoring"


@contextmanager
def _write_session():
    """A committing DB session for tools, mirroring ``db.get_session``.

    Imports the engine lazily so tests can repoint ``app.db.engine`` at an
    in-memory database before a tool runs.
    """
    from sqlmodel import Session

    from app.db import engine

    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _register_tools(mcp: FastMCP) -> None:
    """Register the authoring tools on the server.

    Tools that touch the database import their helpers lazily inside the
    function body to avoid a circular import with ``app.api``. They call the
    same route-handler functions the REST API uses, so there is one source of
    truth for the logic, and translate the API's ``HTTPException`` into a clean
    ``ToolError`` the agent can read.
    """

    @mcp.tool
    def server_status() -> dict:
        """Confirm the Breadcrumbs authoring connector is reachable and authenticated.

        Call this first to verify the connection before authoring.
        """
        return {
            "ok": True,
            "server": SERVER_NAME,
            "environment": os.getenv("ENVIRONMENT", "development"),
        }

    @mcp.tool
    def add_breadcrumb(theme_id: int, body_md: str) -> dict:
        """Add a breadcrumb (a small thought atom, Markdown) to an existing theme.

        Use `list_recent_themes` or `search_themes` first to find the theme id.
        """
        from fastapi import HTTPException

        from app.api import create_breadcrumb
        from app.models import BreadcrumbCreateInput, BreadcrumbPublic

        payload = BreadcrumbCreateInput(body_md=body_md)
        with _write_session() as session:
            try:
                created = create_breadcrumb(theme_id, payload, session=session, _admin=None)
            except HTTPException as exc:
                raise ToolError(str(exc.detail))
            return BreadcrumbPublic.model_validate(created, from_attributes=True).model_dump(mode="json")

    @mcp.tool
    def create_theme(body_md: str, tags: Optional[list[str]] = None, publish: bool = False) -> dict:
        """Create a new theme (a container for related breadcrumbs), Markdown body.

        Defaults to a DRAFT. Pass publish=true ONLY when the writer explicitly
        says to publish; otherwise leave it as a draft to review later. Reuse
        existing tags where they fit (see `suggest_tags`).
        """
        from app.api import create_theme as create_theme_handler
        from app.models import TagCreate, ThemeCreate, ThemePublic, Visibility

        theme_in = ThemeCreate(
            body_md=body_md,
            visibility=Visibility.published if publish else Visibility.draft,
            tags=[TagCreate(name=t) for t in (tags or [])],
        )
        with _write_session() as session:
            created = create_theme_handler(theme_in, session=session, _admin=None)
            return ThemePublic.model_validate(created, from_attributes=True).model_dump(mode="json")

    @mcp.tool
    def suggest_tags(theme_id: int) -> dict:
        """Return AI-suggested tags for a theme, for the writer to confirm.

        This applies nothing; it only proposes tags. Apply chosen tags with an
        edit once the writer confirms.
        """
        from fastapi import HTTPException

        from app.api import suggest_theme_tags

        with _write_session() as session:
            try:
                result = suggest_theme_tags(theme_id, session=session, _admin=None)
            except HTTPException as exc:
                raise ToolError(str(exc.detail))
            return {"tags": list(result.tags)}

    def _compact(theme) -> dict:
        return {
            "id": theme.id,
            "visibility": theme.visibility.value,
            "tags": [tag.name for tag in theme.tags],
            "body_md": theme.body_md,
        }

    @mcp.tool
    def list_recent_themes(limit: int = 10) -> list[dict]:
        """List recent themes (newest first) so you can pick the right one.

        Returns id, visibility (draft/published), tags, and body for each.
        """
        from app.api import list_themes

        with _write_session() as session:
            # Pass offset explicitly: calling the handler directly bypasses
            # FastAPI, so its Query() defaults are not resolved to ints.
            themes = list_themes(session=session, limit=limit, offset=0)
            return [_compact(t) for t in themes]

    @mcp.tool
    def search_themes(query: str) -> list[dict]:
        """Search themes by a query across theme bodies, breadcrumb text, and tags."""
        from app.api import list_themes

        with _write_session() as session:
            themes = list_themes(session=session, q=query)
            return [_compact(t) for t in themes]


def build_mcp(token: Optional[str] = None) -> Optional[FastMCP]:
    """Build the FastMCP server, or ``None`` when no connector token is set.

    ``token`` defaults to ``MCP_CONNECTOR_TOKEN`` from the environment; it is a
    parameter so tests can build a server without touching global env.
    """
    token = token if token is not None else os.getenv("MCP_CONNECTOR_TOKEN", "")
    if not token:
        return None

    verifier = StaticTokenVerifier(
        tokens={token: {"sub": "writer", "client_id": "claude-connector"}}
    )
    mcp = FastMCP(SERVER_NAME, auth=verifier)
    _register_tools(mcp)
    return mcp


def build_mcp_app(token: Optional[str] = None):
    """Return the mountable ASGI app for ``/mcp``, or ``None`` when no token is set.

    The caller merges ``app.lifespan`` into the host app's lifespan (the
    Streamable HTTP session manager runs there) and mounts the result at
    ``/mcp``.
    """
    mcp = build_mcp(token)
    if mcp is None:
        return None
    return mcp.http_app(path="/")
