"""Contract tests for the authoring prompt and confirmation guidance (issue #109)."""

import asyncio

from fastmcp import Client

from app.mcp_server import AUTHORING_PROMPT, build_mcp

TOKEN = "test-connector-token"


def _run(coro_fn):
    async def _go():
        async with Client(build_mcp(TOKEN)) as client:
            return await coro_fn(client)

    return asyncio.run(_go())


def test_authoring_prompt_is_served():
    async def _prompt_text(client):
        names = [p.name for p in await client.list_prompts()]
        assert "breadcrumbs_authoring" in names
        result = await client.get_prompt("breadcrumbs_authoring")
        return result.messages[0].content.text

    text = _run(_prompt_text)
    assert text == AUTHORING_PROMPT


def test_authoring_prompt_carries_voice_and_tag_rules():
    lowered = AUTHORING_PROMPT.lower()
    assert "em-dash" in lowered
    assert "draft" in lowered
    assert "reuse" in lowered and "tag" in lowered
    assert "confirm" in lowered


def test_server_instructions_are_the_authoring_prompt():
    async def _instructions(client):
        return client.initialize_result.instructions

    assert _run(_instructions) == AUTHORING_PROMPT


def test_visible_actions_tell_the_agent_to_confirm_first():
    async def _descriptions(client):
        return {t.name: t.description for t in await client.list_tools()}

    descriptions = _run(_descriptions)
    for name in ("publish_theme", "unpublish_theme", "update_theme", "update_breadcrumb"):
        assert "confirm" in descriptions[name].lower(), name
