"""Contract tests for the authoring connector (issue #105).

Spec: docs/specs/authoring-connector.md (CONN-1, CONN-2, CONN-3).

Security model (decided at build): a single auth gate. Every /mcp request must
carry the connector token (StaticTokenVerifier); past it, tools run in-process
as the trusted admin principal. There is no second credential, so CONN-3 asserts
the fail-safe (no token -> no server) rather than an X-API-Key bridge.
"""

import asyncio

from fastapi.testclient import TestClient

from app.api import app
from app.mcp_server import build_mcp, build_mcp_app

# Matches the token conftest sets before app import.
TOKEN = "test-connector-token"

_MCP_BODY = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
_ACCEPT = {"Accept": "application/json, text/event-stream"}


def test_CONN_1_no_token_rejected():
    # WHEN a client connects to /mcp without a valid connector token
    # THEN the request is rejected (401); WHEN it carries the valid token THEN it
    # gets past the auth gate (not 401).
    with TestClient(app) as client:
        unauth = client.post("/mcp/", json=_MCP_BODY, headers=_ACCEPT)
        assert unauth.status_code == 401

        authed = client.post(
            "/mcp/",
            json=_MCP_BODY,
            headers={**_ACCEPT, "Authorization": f"Bearer {TOKEN}"},
        )
        assert authed.status_code != 401


def test_CONN_2_valid_token_lists_tools():
    # WHEN a client connects with the valid token THEN the authoring tools are
    # listed over the MCP server.
    mcp = build_mcp(TOKEN)
    assert mcp is not None

    async def _tool_names():
        from fastmcp import Client

        async with Client(mcp) as c:
            return [t.name for t in await c.list_tools()]

    assert "server_status" in asyncio.run(_tool_names())


def test_CONN_4_bare_mcp_served_without_trailing_slash():
    # Claude's connector UI strips the trailing slash, so requests hit bare /mcp,
    # and its MCP client does not follow a redirect. WHEN a client hits bare /mcp
    # THEN it is routed straight into the MCP app (no redirect, not the SPA): an
    # unauthenticated request reaches the auth gate and is rejected (401), and a
    # valid token gets past it (not 401) -- identical to /mcp/.
    with TestClient(app) as client:
        unauth = client.post(
            "/mcp", json=_MCP_BODY, headers=_ACCEPT, follow_redirects=False
        )
        assert unauth.status_code == 401

        authed = client.post(
            "/mcp",
            json=_MCP_BODY,
            headers={**_ACCEPT, "Authorization": f"Bearer {TOKEN}"},
            follow_redirects=False,
        )
        assert authed.status_code != 401


def test_CONN_3_no_token_means_no_server():
    # WHEN MCP_CONNECTOR_TOKEN is not set THEN no server and no mountable app are
    # built, so no unauthenticated path to the authoring tools can exist.
    assert build_mcp(token="") is None
    assert build_mcp_app(token="") is None
    # And a configured token does build a server (sanity).
    assert build_mcp(token="anything") is not None
