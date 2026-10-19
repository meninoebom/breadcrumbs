"""Contract stubs for find tools (issue #107).

Spec: docs/specs/authoring-connector.md (FIND-1, FIND-2).

Skipped until `/workflow:build` activates them for #107.
"""

import pytest

STUB = "contract stub — activated by /workflow:build (#107)"


@pytest.mark.skip(reason=STUB)
def test_FIND_1_list_recent_returns_fields_newest_first():
    # WHEN list_recent_themes is called
    # THEN it returns recent themes with id, title, published state, and tags,
    # most recent first.
    # Assert: results carry those fields and are ordered newest-first.
    raise NotImplementedError(STUB)


@pytest.mark.skip(reason=STUB)
def test_FIND_2_search_matches_body_breadcrumb_tag():
    # WHEN search_themes is called with a query
    # THEN it returns themes matching across theme body, breadcrumb content,
    # and tags.
    # Assert: a theme matched only via breadcrumb text, and one matched only via
    # a tag, both appear; a non-matching theme does not.
    raise NotImplementedError(STUB)
