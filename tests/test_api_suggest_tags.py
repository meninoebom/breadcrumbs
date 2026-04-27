"""Tests for POST /api/themes/{theme_id}/suggest-tags."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.models import Tag, Theme, Visibility


def _make_claude_response(tags: list[str]) -> MagicMock:
    content_block = MagicMock()
    content_block.text = json.dumps({"tags": tags})
    msg = MagicMock()
    msg.content = [content_block]
    return msg


@pytest.fixture
def theme(session):
    t = Theme(body_md="Reflections on solitude and the nature of attention", visibility=Visibility.draft)
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


@pytest.fixture
def theme_with_tags(session, theme):
    for name in ["mindfulness", "philosophy"]:
        tag = Tag(name=name)
        session.add(tag)
        theme.tags.append(tag)
    session.add(theme)
    session.commit()
    session.refresh(theme)
    return theme


def test_suggest_tags_returns_normalized_tags(client, theme):
    mock_response = _make_claude_response(["solitude", "attention", "reflection"])
    with patch("app.tag_suggester.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value = mock_response
        response = client.post(f"/api/themes/{theme.id}/suggest-tags")

    assert response.status_code == 200
    data = response.json()
    assert "tags" in data
    assert data["tags"] == ["solitude", "attention", "reflection"]


def test_suggest_tags_passes_existing_tags_for_context(client, theme_with_tags):
    mock_response = _make_claude_response(["mindfulness", "focus"])
    with patch("app.tag_suggester.anthropic.Anthropic") as mock_cls:
        mock_instance = mock_cls.return_value
        mock_instance.messages.create.return_value = mock_response
        client.post(f"/api/themes/{theme_with_tags.id}/suggest-tags")

    call_kwargs = mock_instance.messages.create.call_args
    prompt_text = call_kwargs.kwargs["messages"][0]["content"]
    assert "mindfulness" in prompt_text
    assert "philosophy" in prompt_text


def test_suggest_tags_normalizes_raw_output(client, theme):
    mock_response = _make_claude_response(["Deep Work", "mind fullness", "self--care"])
    with patch("app.tag_suggester.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value = mock_response
        response = client.post(f"/api/themes/{theme.id}/suggest-tags")

    assert response.status_code == 200
    assert response.json()["tags"] == ["deep-work", "mind-fullness", "self-care"]


def test_suggest_tags_returns_404_for_missing_theme(client):
    with patch("app.tag_suggester.anthropic.Anthropic"):
        response = client.post("/api/themes/999/suggest-tags")
    assert response.status_code == 404


def test_suggest_tags_returns_503_on_api_error(client, theme):
    import anthropic as anthropic_lib

    with patch("app.tag_suggester.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.side_effect = anthropic_lib.APIError(
            message="rate limited", request=MagicMock(), body=None
        )
        response = client.post(f"/api/themes/{theme.id}/suggest-tags")

    assert response.status_code == 503
