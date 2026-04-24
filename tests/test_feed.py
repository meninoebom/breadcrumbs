from datetime import date

from app.feed import EXPANDED_WINDOW_DAYS, months_to_collapse, rolling_cutoff


def test_rolling_cutoff_is_31_days_before_today():
    assert rolling_cutoff(date(2026, 4, 24)) == date(2026, 3, 24)


def test_month_with_theme_inside_window_stays_expanded():
    # today=2026-04-24, cutoff=2026-03-24. March has a theme on 2026-03-30,
    # which is inside the window — so March must NOT collapse even though
    # it also has themes from Mar 1-22.
    today = date(2026, 4, 24)
    theme_dates = [
        date(2026, 4, 10),
        date(2026, 3, 30),  # inside window
        date(2026, 3, 5),  # outside window
    ]
    assert months_to_collapse(today, theme_dates) == []


def test_month_entirely_outside_window_collapses():
    today = date(2026, 4, 24)
    theme_dates = [
        date(2026, 4, 10),
        date(2026, 2, 28),
        date(2026, 2, 1),
    ]
    assert months_to_collapse(today, theme_dates) == [(2026, 2)]


def test_multiple_collapsed_months_sorted_newest_first():
    today = date(2026, 4, 24)
    theme_dates = [
        date(2026, 4, 1),
        date(2026, 2, 15),
        date(2026, 1, 3),
        date(2025, 12, 20),
    ]
    assert months_to_collapse(today, theme_dates) == [
        (2026, 2),
        (2026, 1),
        (2025, 12),
    ]


def test_boundary_theme_on_cutoff_stays_expanded():
    # "Last 31 days" is inclusive: today minus 31d = 31 days ago, still inside.
    today = date(2026, 4, 24)
    theme_dates = [date(2026, 3, 24)]
    assert months_to_collapse(today, theme_dates) == []


def test_boundary_theme_one_day_older_than_cutoff_collapses():
    today = date(2026, 4, 24)
    theme_dates = [date(2026, 3, 23)]
    assert months_to_collapse(today, theme_dates) == [(2026, 3)]


def test_no_themes_returns_empty():
    assert months_to_collapse(date(2026, 4, 24), []) == []


def test_window_is_31_days():
    assert EXPANDED_WINDOW_DAYS == 31
