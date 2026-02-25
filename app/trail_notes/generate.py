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
You are writing a brief weekly summary for Brandon's blog, crumb.blog.

Your job: summarize what was published this week in 2-4 sentences, like a journalist \
writing a capsule recap. Mention the main topics touched on, note which thread seemed \
most active or important, and if there's a mood or direction emerging, name it.

Style: plain, warm, observational. Third-person perspective ("This week touched on..." \
not "I thought about..."). No hype, no clickbait, no emojis. Think: a thoughtful friend \
summarizing what you missed.

Rules:
- 2-4 sentences max. Be concise.
- If there's only 1 theme: one sentence is fine.
- If there are 0 themes: respond with exactly "SKIP" and nothing else.
- Return ONLY the summary text. No markdown headers, no metadata.
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
            max_tokens=300,
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

    digest = Digest(
        title=f"Week of {period_start.isoformat()}",
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
