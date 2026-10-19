"""Contract stubs for the authoring connector (issue #105).

Spec: docs/specs/authoring-connector.md (CONN-1, CONN-2, CONN-3).

These are authored before the MCP server exists. They stay skipped so the suite
is green; `/workflow:build` activates them when implementing #105. Do not weaken
the WHEN/THEN below to make implementation easier — change the spec instead.
"""

import pytest

STUB = "contract stub — activated by /workflow:build (#105)"


@pytest.mark.skip(reason=STUB)
def test_CONN_1_no_token_rejected():
    # WHEN a client connects to /mcp without a valid connector token
    # THEN the request is rejected and no tools are exposed.
    # Assert: a connection/list-tools attempt with a missing or wrong
    # MCP_CONNECTOR_TOKEN returns an auth error and an empty/absent tool list.
    raise NotImplementedError(STUB)


@pytest.mark.skip(reason=STUB)
def test_CONN_2_valid_token_lists_tools():
    # WHEN a client connects with the valid MCP_CONNECTOR_TOKEN
    # THEN the authoring tools are listed over Streamable HTTP.
    # Assert: list_tools() succeeds and includes the authoring tool names
    # (e.g. add_breadcrumb, create_theme) once those issues land.
    raise NotImplementedError(STUB)


@pytest.mark.skip(reason=STUB)
def test_CONN_3_write_requires_admin_key():
    # WHEN an MCP tool performs a write
    # THEN it authenticates to the Breadcrumbs API as an admin machine client
    # (X-API-Key), so an unauthenticated path cannot write.
    # Assert: the write reaches require_admin with a valid X-API-Key; a call
    # made without the admin credential is rejected (no silent unauthenticated write).
    raise NotImplementedError(STUB)
