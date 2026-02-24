"""Digest generation: gather the week's themes + breadcrumbs, ask Claude to write a Trail Note."""

import os
from datetime import date, datetime, timedelta, timezone

import anthropic
from sqlmodel import Session, col, select

from app.models import (
    Breadcrumb,
    Digest,
    DigestStatus,
    Tag,
    Theme,
    Visibility,
)

SYSTEM_PROMPT = """\
You are ghostwriting a weekly digest called "Trail Notes" for Brandon's blog, crumb.blog.

Voice: First-person reflective Brandon — not present-tense Brandon writing in the moment, \
but Brandon looking back at his own week and noticing patterns. Warm, curious, self-deprecating, \
with the occasional cultural tangent that makes the point better than a straight explanation would. \
Think: the conversational register of Bytes newsletter meets the essayistic wandering of Ted Gioia \
meets the honest self-examination of Platformer.

Specific voice notes:
- Use "I" naturally but don't start every sentence with it
- Humor arrives sideways, never announced ("I spent an unreasonable amount of time on..." not "LOL")
- Okay to reference the process of thinking itself ("somewhere around Tuesday I got obsessed with...")
- End on something genuinely unresolved — a question you're still sitting with, not a tidy bow
- Never use the word "delve", "utilize", "leverage", or "landscape"
- Never use em-dashes more than once per paragraph

Format (300-500 words of prose, not bullets):

1. **Opening hook** — the one thread that ties the week together (1-2 sentences)
2. **Per-theme recaps** — ordered by richness (most breadcrumbs first). For each:
   - A one-sentence reframe of what the theme was really about
   - A pulled quote from the best breadcrumb (use > blockquote markdown)
   - A "Read it →" link formatted as: [Read it →](/tags/{tag-name}/themes)
3. **Closing thought** — something unresolved, a question still being sat with (1-2 sentences)

Special cases:
- If there's only 1 theme with 3+ breadcrumbs: write a shorter "one thing" format (~200 words)
- If there are 0 themes: respond with exactly "SKIP" and nothing else

Output format: Return ONLY the markdown prose. No metadata, no YAML frontmatter, no "# Title" header. \
The title should be returned separately when asked.
"""

TITLE_PROMPT = """\
Given this weekly digest, write a short evocative title (under 60 chars). \
Style: lowercase feel, no clickbait, sounds like something scrawled in a notebook margin. \
Examples: "On solitude, recursion, and maps" or "Language drift, the smell of rain" or "The one about velocity".

Return ONLY the title text, nothing else.
"""


def gather_week_content(
    session: Session,
    period_start: date,
    period_end: date,
) -> str:
    """Pull published themes and their breadcrumbs for the given week, formatted for Claude."""
    start_dt = datetime.combine(period_start, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(period_end, datetime.max.time(), tzinfo=timezone.utc)

    themes = session.exec(
        select(Theme)
        .where(Theme.visibility == Visibility.published)
        .where(col(Theme.created_at) >= start_dt)
        .where(col(Theme.created_at) <= end_dt)
        .order_by(col(Theme.created_at))
    ).all()

    if not themes:
        return ""

    parts: list[str] = []
    for theme in themes:
        tag_names = [t.name for t in theme.tags]
        tags_str = ", ".join(tag_names) if tag_names else "(untagged)"

        breadcrumbs = session.exec(
            select(Breadcrumb)
            .where(Breadcrumb.theme_id == theme.id)
            .order_by(col(Breadcrumb.created_at))
        ).all()

        section = f"## Theme: {theme.body_md[:80]}...\nTags: {tags_str}\nBreadcrumbs: {len(breadcrumbs)}\n"
        for bc in breadcrumbs:
            section += f"\n- {bc.body_md}"

        parts.append(section)

    return "\n\n---\n\n".join(parts)


def generate_digest(
    session: Session,
    period_start: date,
    period_end: date,
) -> Digest:
    """Generate a Trail Notes digest for the given week using Claude."""
    content = gather_week_content(session, period_start, period_end)

    if not content:
        raise ValueError("No published content found for this period — skipping digest.")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")
    client = anthropic.Anthropic(api_key=api_key)

    # Generate the prose
    try:
        summary_response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Here's what was published on crumb.blog this week "
                    f"({period_start.isoformat()} to {period_end.isoformat()}):\n\n{content}",
                }
            ],
        )
    except anthropic.APIError as e:
        raise ValueError(f"Anthropic API error during digest generation: {e}")

    if not summary_response.content:
        raise ValueError("Anthropic returned an empty response for digest prose.")
    summary_md = summary_response.content[0].text

    if summary_md.strip() == "SKIP":
        raise ValueError("Claude determined there's not enough content for a digest this week.")

    # Generate the title
    try:
        title_response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[
                {"role": "user", "content": f"{TITLE_PROMPT}\n\nDigest:\n{summary_md}"}
            ],
        )
    except anthropic.APIError as e:
        raise ValueError(f"Anthropic API error during title generation: {e}")

    if not title_response.content:
        raise ValueError("Anthropic returned an empty response for digest title.")
    title = title_response.content[0].text.strip().strip('"')

    digest = Digest(
        title=title,
        summary_md=summary_md,
        period_start=period_start,
        period_end=period_end,
        status=DigestStatus.draft,
    )
    session.add(digest)
    session.flush()
    session.refresh(digest)
    return digest


def get_current_week_bounds() -> tuple[date, date]:
    """Return (Monday, Sunday) for the most recently completed week."""
    today = date.today()
    # Go back to last Sunday
    last_sunday = today - timedelta(days=today.isoweekday())
    last_monday = last_sunday - timedelta(days=6)
    return last_monday, last_sunday
