"""Trading calendar for asset classes with fixed trading hours (ADR-022).

Crypto trades 24/7. Equities follow standard NYSE/NASDAQ hours
(America/New_York, 09:30-16:00, Monday-Friday) — the single reference
calendar since every equity instrument seeded so far (AAPL, MSFT, TSLA)
trades on one of these two exchanges. The 2026 holiday list is hardcoded
(same pattern as the economic calendar, ADR-018); early-close half days
(e.g. the day after Thanksgiving) are not modeled — an honest, documented
approximation, not a full trading-calendar library.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

_NY = ZoneInfo("America/New_York")
_OPEN_TIME = time(9, 30)
_CLOSE_TIME = time(16, 0)

_NYSE_HOLIDAYS_2026 = {
    date(2026, 1, 1),  # New Year's Day
    date(2026, 1, 19),  # Martin Luther King Jr. Day
    date(2026, 2, 16),  # Washington's Birthday
    date(2026, 4, 3),  # Good Friday
    date(2026, 5, 25),  # Memorial Day
    date(2026, 6, 19),  # Juneteenth
    date(2026, 7, 3),  # Independence Day (observed)
    date(2026, 9, 7),  # Labor Day
    date(2026, 11, 26),  # Thanksgiving
    date(2026, 12, 25),  # Christmas
}


@dataclass(frozen=True)
class MarketStatus:
    is_open: bool
    next_open: datetime | None
    next_close: datetime | None


def is_trading_day(day: date) -> bool:
    return day.weekday() < 5 and day not in _NYSE_HOLIDAYS_2026


def _next_trading_day(day: date) -> date:
    candidate = day + timedelta(days=1)
    while not is_trading_day(candidate):
        candidate += timedelta(days=1)
    return candidate


def equity_market_status(now_utc: datetime) -> MarketStatus:
    now_ny = now_utc.astimezone(_NY)
    today = now_ny.date()

    if is_trading_day(today):
        open_ny = datetime.combine(today, _OPEN_TIME, tzinfo=_NY)
        close_ny = datetime.combine(today, _CLOSE_TIME, tzinfo=_NY)
        if open_ny <= now_ny < close_ny:
            return MarketStatus(
                is_open=True,
                next_open=None,
                next_close=close_ny.astimezone(timezone.utc),
            )
        if now_ny < open_ny:
            return MarketStatus(
                is_open=False, next_open=open_ny.astimezone(timezone.utc), next_close=None
            )

    next_day = _next_trading_day(today)
    next_open_ny = datetime.combine(next_day, _OPEN_TIME, tzinfo=_NY)
    return MarketStatus(
        is_open=False, next_open=next_open_ny.astimezone(timezone.utc), next_close=None
    )


def crypto_market_status() -> MarketStatus:
    return MarketStatus(is_open=True, next_open=None, next_close=None)
