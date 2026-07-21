import pytest

from src.modules.market_data.domain.value_objects import Timeframe


def test_valid_timeframes_expose_duration_seconds():
    assert Timeframe("1h").seconds == 3600
    assert Timeframe("1d").seconds == 86400


def test_invalid_timeframe_is_rejected():
    with pytest.raises(ValueError):
        Timeframe("2w")
