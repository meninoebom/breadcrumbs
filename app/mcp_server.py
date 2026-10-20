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
from typing import Optional

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth import StaticTokenVerifier

# auth.py-style gotcha: this module reads env at import/build time, so load the
# dotenv here rather than relying on another module having loaded it first.
load_dotenv()

SERVER_NAME = "Breadcrumbs Authoring"


def _register_tools(mcp: FastMCP) -> None:
    """Register the authoring tools on the server.

    Issue #105 ships only the connectivity check; the capture, find, edit, and
    publish tools are added by #106-#108. Tools that touch the database import
    their helpers lazily inside the function body to avoid a circular import
    with ``app.api``.
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
