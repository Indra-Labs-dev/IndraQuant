from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from src.modules.market_data.domain.trading_calendar import (
    crypto_market_status,
    equity_market_status,
    is_trading_day,
)

NY = ZoneInfo("America/New_York")


def ny(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=NY).astimezone(timezone.utc)


def test_crypto_is_always_open():
    status = crypto_market_status()
    assert status.is_open is True
    assert status.next_open is None
    assert status.next_close is None


def test_open_during_regular_trading_hours():
    # Tuesday 2026-07-21, 14:00 ET (well within 09:30-16:00, no DST edge case).
    status = equity_market_status(ny(2026, 7, 21, 14))
    assert status.is_open is True
    assert status.next_open is None
    assert status.next_close is not None
    assert status.next_close.astimezone(NY).time().hour == 16


def test_closed_before_open_same_day():
    status = equity_market_status(ny(2026, 7, 21, 8))
    assert status.is_open is False
    assert status.next_open is not None
    opened = status.next_open.astimezone(NY)
    assert (opened.hour, opened.minute) == (9, 30)
    assert opened.date().day == 21


def test_closed_after_close_rolls_to_next_trading_day():
    # Tuesday 2026-07-21, 18:00 ET -> next open should be Wednesday 09:30 ET.
    status = equity_market_status(ny(2026, 7, 21, 18))
    assert status.is_open is False
    opened = status.next_open.astimezone(NY)
    assert opened.date().day == 22


def test_weekend_rolls_to_monday():
    # Saturday 2026-07-25 -> next open Monday 2026-07-27.
    status = equity_market_status(ny(2026, 7, 25, 12))
    assert status.is_open is False
    opened = status.next_open.astimezone(NY)
    assert opened.date() == datetime(2026, 7, 27).date()


def test_holiday_is_skipped():
    # Christmas 2026-12-25 is a Friday and a holiday -> closed, next open
    # should skip the weekend to Monday 2026-12-28.
    assert is_trading_day(datetime(2026, 12, 25).date()) is False
    status = equity_market_status(ny(2026, 12, 25, 12))
    assert status.is_open is False
    opened = status.next_open.astimezone(NY)
    assert opened.date() == datetime(2026, 12, 28).date()
