"""Seed the local SQLite with realistic data to preview the rolling-window feed.

Writes themes across April (recent + window-straddling), March (straddling),
and February (fully collapsed), plus a monthly digest for February.
"""

from datetime import date, datetime, timedelta, timezone

from sqlmodel import Session, SQLModel

from app.db import engine
from app.models import (
    Breadcrumb,
    Digest,
    DigestStatus,
    DigestType,
    Tag,
    Theme,
    Visibility,
)


def _dt(days_ago: int, hours: int = 12) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_ago, hours=-hours)


def main() -> None:
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # Clean slate — this is a preview DB.
        for model in (Breadcrumb, Theme, Digest, Tag):
            for row in session.query(model).all():
                session.delete(row)
        session.commit()

        tag_seed = Tag(name="seed")
        tag_reflection = Tag(name="reflection")
        tag_walking = Tag(name="walking")
        session.add_all([tag_seed, tag_reflection, tag_walking])
        session.flush()

        def add_theme(body: str, days_ago: int, tags: list[Tag]) -> Theme:
            t = Theme(
                body_md=body,
                visibility=Visibility.published,
                created_at=_dt(days_ago),
            )
            t.tags = tags
            session.add(t)
            session.flush()
            return t

        # Current week (fully in window)
        add_theme("# This week\n\nA fresh trail.", 1, [tag_seed])
        add_theme("# Thinking out loud\n\nAn afternoon walk thought.", 3, [tag_walking])

        # ~2 weeks back (in window)
        add_theme("# Middle April\n\nNotes from mid-month.", 14, [tag_reflection])

        # Crossing the cutoff — March 30-ish (inside 31-day window)
        add_theme("# Late March\n\nStraddles the window edge.", 26, [tag_reflection])

        # Early March (outside window but same month as a theme inside — stays expanded)
        add_theme("# Early March\n\nBeginning of March.", 50, [tag_walking])

        # February (fully outside window — collapses)
        add_theme("# February seed\n\nOne of the 'lost' February themes.", 70, [tag_seed])
        add_theme("# February reflection\n\nAnother February entry.", 75, [tag_reflection])
        add_theme("# Early February\n\nJust after the new year inertia.", 85, [tag_seed])

        # January (also fully outside window — collapses)
        add_theme("# January thought\n\nNew-year energy.", 100, [tag_reflection])

        # Monthly digest for February
        today = date.today()
        feb_month_year = today.year if today.month > 2 else today.year - 1
        session.add(
            Digest(
                title="February 2026 in review",
                summary_md=(
                    "A month spent on quiet reflection, long walks, and seeding ideas. "
                    "The throughline: attention is the first gift you give to a thought."
                ),
                digest_type=DigestType.monthly,
                period_start=date(feb_month_year, 2, 1),
                period_end=date(feb_month_year, 2, 28),
                status=DigestStatus.published,
            )
        )

        # One weekly digest inside February (reveals on expand)
        session.add(
            Digest(
                title="Week of Feb 8",
                summary_md="A week of walking, reading Kastrup, and thinking about attention.",
                digest_type=DigestType.weekly,
                period_start=date(feb_month_year, 2, 8),
                period_end=date(feb_month_year, 2, 14),
                status=DigestStatus.published,
            )
        )

        session.commit()
        print("Seeded preview DB.")


if __name__ == "__main__":
    main()
