"""Feed grouping logic for the reader stream.

The reader sees a rolling 31-day expanded window of recent content;
everything older is grouped by calendar month and presented collapsed
behind its monthly digest. A month collapses only if *every* theme in
it is older than the cutoff — so months that straddle the window stay
fully expanded, and users typically see 1–2 months' worth of content
uncollapsed at any time.
"""

from datetime import date, timedelta

EXPANDED_WINDOW_DAYS = 31


def rolling_cutoff(today: date, window_days: int = EXPANDED_WINDOW_DAYS) -> date:
    """The oldest date still inside the expanded window."""
    return today - timedelta(days=window_days)


def months_to_collapse(
    today: date,
    theme_dates: list[date],
    window_days: int = EXPANDED_WINDOW_DAYS,
) -> list[tuple[int, int]]:
    """Return (year, month) pairs for months that should render collapsed.

    A month is collapsed iff every theme date in it is strictly older than
    `today - window_days`. Months with *any* theme inside the window stay
    expanded. Result is sorted newest-first for stable feed order.
    """
    cutoff = rolling_cutoff(today, window_days)

    dates_by_month: dict[tuple[int, int], list[date]] = {}
    for d in theme_dates:
        dates_by_month.setdefault((d.year, d.month), []).append(d)

    collapsed = [
        ym for ym, dates in dates_by_month.items() if max(dates) < cutoff
    ]
    collapsed.sort(reverse=True)
    return collapsed
