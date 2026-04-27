"""Claude-powered tag suggestions for themes."""

import json
import logging
import os
import re

import anthropic

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You suggest concise, reusable tags for blog themes.

Rules:
- Return 3–5 tags as a JSON object: {"tags": ["tag-one", "tag-two"]}
- Prefer existing tags when they fit; only invent new ones when needed
- Tags should be lowercase words or short phrases (e.g. "deep-work", "identity")
- Return ONLY the JSON object — no explanation, no markdown
"""


def suggest_tags(theme_body: str, existing_tag_names: list[str]) -> list[str]:
    """Call Claude Haiku to suggest tags for a theme, normalized to slug format."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    existing_context = (
        f"\n\nExisting tags on this blog (prefer these when relevant): {', '.join(existing_tag_names)}"
        if existing_tag_names
        else ""
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Theme content:\n\n{theme_body}{existing_context}",
            }
        ],
    )

    raw_text = response.content[0].text
    data = json.loads(raw_text)
    raw_tags = data.get("tags", [])
    return [_normalize(t) for t in raw_tags if t]


def _normalize(name: str) -> str:
    v = re.sub(r"\s+", "-", name.strip().lower())
    v = re.sub(r"[^a-z0-9\-]", "", v)
    v = re.sub(r"-{2,}", "-", v)
    return v.strip("-")
