"""Contract stubs for edit + publish tools (issue #108).

Spec: docs/specs/authoring-connector.md (EDIT-1, EDIT-2, PUB-1, PUB-2).

Skipped until `/workflow:build` activates them for #108.
"""

import pytest

STUB = "contract stub — activated by /workflow:build (#108)"


@pytest.mark.skip(reason=STUB)
def test_EDIT_1_update_breadcrumb_replaces():
    # WHEN update_breadcrumb is called with a valid id and new content
    # THEN the breadcrumb content is replaced and the updated record returned.
    raise NotImplementedError(STUB)


@pytest.mark.skip(reason=STUB)
def test_EDIT_2_update_theme_partial():
    # WHEN update_theme is called with a valid id and some fields
    # THEN only the provided fields change; others are untouched.
    # Assert: set one field, confirm it changed and a sibling field did not.
    raise NotImplementedError(STUB)


@pytest.mark.skip(reason=STUB)
def test_PUB_1_publish_makes_visible():
    # WHEN publish_theme is called on a draft
    # THEN published becomes true and the theme is reader-visible.
    # Assert: the theme appears in the reader (published) feed afterwards.
    raise NotImplementedError(STUB)


@pytest.mark.skip(reason=STUB)
def test_PUB_2_unpublish_removes_from_feed():
    # WHEN unpublish_theme is called on a published theme
    # THEN published becomes false and it leaves the reader feed.
    # Assert: the theme is absent from the reader (published) feed afterwards.
    raise NotImplementedError(STUB)
