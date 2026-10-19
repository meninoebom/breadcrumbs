"""Contract stubs for capture tools (issue #106).

Spec: docs/specs/authoring-connector.md (CAP-1..CAP-5).

Skipped until `/workflow:build` activates them for #106. Assert through the MCP
tool interface and resulting DB/API state, never implementation details.
"""

import pytest

STUB = "contract stub — activated by /workflow:build (#106)"


@pytest.mark.skip(reason=STUB)
def test_CAP_1_add_breadcrumb_creates():
    # WHEN add_breadcrumb is called with a valid theme id and content
    # THEN a breadcrumb is created on that theme and its id + timestamp returned.
    # Assert: the tool result carries a breadcrumb id and timestamp, and the
    # breadcrumb is readable on that theme via the API.
    raise NotImplementedError(STUB)


@pytest.mark.skip(reason=STUB)
def test_CAP_2_add_breadcrumb_missing_theme():
    # WHEN add_breadcrumb references a non-existent theme id
    # THEN the tool returns a clear not-found error, not a 500.
    raise NotImplementedError(STUB)


@pytest.mark.skip(reason=STUB)
def test_CAP_3_create_theme_defaults_draft():
    # WHEN create_theme is called with a title and no publish flag
    # THEN the theme is created as a draft (published=false).
    # Assert: the created theme is not present in the reader (published) feed.
    raise NotImplementedError(STUB)


@pytest.mark.skip(reason=STUB)
def test_CAP_4_create_theme_publish_true():
    # WHEN create_theme is called with publish=true
    # THEN the theme is created published and visible to readers.
    # Assert: the created theme appears in the reader (published) feed.
    raise NotImplementedError(STUB)


@pytest.mark.skip(reason=STUB)
def test_CAP_5_suggest_tags_returns_without_applying():
    # WHEN suggest_tags is called for a theme
    # THEN AI-suggested tags are returned for confirmation before any are applied.
    # Assert: the tool returns a non-empty suggestion list, and the theme's own
    # tags are unchanged by the call.
    raise NotImplementedError(STUB)
