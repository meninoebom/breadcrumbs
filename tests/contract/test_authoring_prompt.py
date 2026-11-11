"""Contract tests for the authoring prompt and confirmation guidance."""

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
        prompts = {p.name: p for p in await client.list_prompts()}
        assert prompts["breadcrumbs_authoring"].title == "Breadcrumbs authoring"
        result = await client.get_prompt("breadcrumbs_authoring")
        return result.messages[0].content.text

    text = _run(_prompt_text)
    assert text == AUTHORING_PROMPT


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
