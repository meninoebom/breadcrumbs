"""Unit tests for app.images pure-function logic."""

import pytest

from app.images import (
    STYLE_SUFFIX,
    ImageCommitError,
    _is_allowed_source,
    _looks_like_image,
    build_theme_prompt,
    tags_for_prompt,
)
from app.models import Tag, Theme


def test_build_theme_prompt_includes_snippet_and_suffix():
    theme = Theme(body_md="A short, sharp thought")
    prompt = build_theme_prompt(theme, [])
    assert "A short, sharp thought" in prompt
    assert STYLE_SUFFIX in prompt


def test_build_theme_prompt_uses_first_sentence():
    theme = Theme(body_md="First sentence here. Second sentence we drop.")
    prompt = build_theme_prompt(theme, [])
    assert "First sentence here" in prompt
    assert "Second sentence we drop" not in prompt


def test_build_theme_prompt_truncates_overlong_first_sentence():
    long = "x" * 500
    theme = Theme(body_md=long)
    prompt = build_theme_prompt(theme, [])
    snippet = long[:200]
    assert snippet in prompt
    assert "x" * 201 not in prompt


def test_build_theme_prompt_renders_tags_as_mood():
    theme = Theme(body_md="Body")
    prompt = build_theme_prompt(theme, ["deep-work", "slow-mornings"])
    assert "Mood draws from: deep work, slow mornings" in prompt


def test_build_theme_prompt_no_tags_no_mood_phrase():
    theme = Theme(body_md="Body")
    prompt = build_theme_prompt(theme, [])
    assert "Mood draws from" not in prompt


def test_build_theme_prompt_empty_body():
    theme = Theme(body_md="")
    prompt = build_theme_prompt(theme, [])
    assert STYLE_SUFFIX in prompt


def test_tags_for_prompt_empty_when_none():
    theme = Theme(body_md="x")
    theme.tags = []
    assert tags_for_prompt(theme) == []


def test_tags_for_prompt_extracts_names():
    theme = Theme(body_md="x")
    theme.tags = [Tag(name="alpha"), Tag(name="beta")]
    assert tags_for_prompt(theme) == ["alpha", "beta"]


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://replicate.delivery/xezq/abc/out-0.webp", True),
        ("https://pbxt.replicate.delivery/foo/bar.webp", True),
        ("https://something.replicate.delivery/x.webp", True),
        ("http://replicate.delivery/x.webp", False),  # not https
        ("https://evil.example.com/x.webp", False),
        ("https://localhost/x.webp", False),
        ("https://replicate.delivery.evil.com/x.webp", False),
        ("file:///etc/passwd", False),
    ],
)
def test_is_allowed_source_validates_host_and_scheme(url, expected):
    assert _is_allowed_source(url) is expected


def test_looks_like_image_accepts_known_magic_bytes():
    assert _looks_like_image(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
    assert _looks_like_image(b"\xff\xd8\xff\xe0" + b"\x00" * 8)
    assert _looks_like_image(b"RIFF\x00\x00\x00\x00WEBP")


def test_looks_like_image_rejects_html_and_text():
    assert not _looks_like_image(b"<html><body>Not an image</body></html>")
    assert not _looks_like_image(b'{"error": "expired"}')
    assert not _looks_like_image(b"")


def test_image_commit_error_is_runtime_error():
    """Sanity: ImageCommitError is catchable as RuntimeError for backwards compat."""
    assert issubclass(ImageCommitError, RuntimeError)
