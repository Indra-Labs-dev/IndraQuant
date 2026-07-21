"""Static macro-calendar source (Phase 5, ADR-018): FOMC 2026 dates are the
official published schedule; CPI and NFP are rule-generated approximations.
Replace with a live provider behind the same interface when a free reliable
source is chosen.
"""

from datetime import date, timedelta

_FOMC_2026 = [
    date(2026, 1, 27),
    date(2026, 1, 28),
    date(2026, 3, 17),
    date(2026, 3, 18),
    date(2026, 4, 28),
    date(2026, 4, 29),
    date(2026, 6, 16),
    date(2026, 6, 17),
    date(2026, 7, 28),
    date(2026, 7, 29),
    date(2026, 9, 15),
    date(2026, 9, 16),
    date(2026, 10, 27),
    date(2026, 10, 28),
    date(2026, 12, 8),
    date(2026, 12, 9),
]


def _first_friday(year: int, month: int) -> date:
    day = date(year, month, 1)
    while day.weekday() != 4:
        day += timedelta(days=1)
    return day


def generate_events(start: date, end: date) -> list[dict]:
    events: list[dict] = []

    for fomc_day in _FOMC_2026:
        if start <= fomc_day <= end:
            events.append(
                {
                    "date": fomc_day,
                    "name": "Réunion FOMC (Fed)",
                    "importance": "haute",
                    "note": "Décision de taux possible — volatilité attendue.",
                }
            )

    month_cursor = date(start.year, start.month, 1)
    while month_cursor <= end:
        nfp = _first_friday(month_cursor.year, month_cursor.month)
        if start <= nfp <= end:
            events.append(
                {
                    "date": nfp,
                    "name": "Emplois non agricoles US (NFP)",
                    "importance": "haute",
                    "note": "Premier vendredi du mois — date approximative.",
                }
            )
        cpi = date(month_cursor.year, month_cursor.month, 13)
        if start <= cpi <= end:
            events.append(
                {
                    "date": cpi,
                    "name": "Inflation US (CPI)",
                    "importance": "haute",
                    "note": "Publication vers le 13 du mois — date approximative.",
                }
            )
        month_cursor = (
            date(month_cursor.year + 1, 1, 1)
            if month_cursor.month == 12
            else date(month_cursor.year, month_cursor.month + 1, 1)
        )

    return events
