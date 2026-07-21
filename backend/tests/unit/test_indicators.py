import math

from src.modules.feature_engineering.domain.series import (
    log_returns,
    returns,
    rolling_mean,
    rolling_std,
)
from src.modules.technical_analysis.domain.indicators import (
    bollinger,
    ema,
    macd,
    rsi,
    sma,
)


def test_returns_and_log_returns():
    values = [100.0, 110.0, 99.0]
    assert returns(values) == [None, 0.10, -0.10]
    result = log_returns(values)
    assert result[0] is None
    assert math.isclose(result[1], math.log(1.1))


def test_rolling_mean_and_std():
    values = [1.0, 2.0, 3.0, 4.0]
    assert rolling_mean(values, 2) == [None, 1.5, 2.5, 3.5]
    std = rolling_std(values, 2)
    assert std[0] is None
    assert math.isclose(std[1], 0.5)


def test_sma_alignment():
    assert sma([1.0, 2.0, 3.0], 3) == [None, None, 2.0]


def test_ema_starts_from_sma_seed():
    result = ema([1.0, 2.0, 3.0, 4.0], 3)
    assert result[:2] == [None, None]
    assert result[2] == 2.0
    assert math.isclose(result[3], (4.0 - 2.0) * 0.5 + 2.0)


def test_rsi_extremes():
    rising = [float(i) for i in range(1, 20)]
    result = rsi(rising, 14)
    assert result[13] is None
    assert result[-1] == 100.0

    falling = [float(i) for i in range(20, 1, -1)]
    assert rsi(falling, 14)[-1] == 0.0


def test_macd_shapes_and_histogram_consistency():
    closes = [float(i) + (i % 3) for i in range(60)]
    result = macd(closes)
    assert len(result["macd"]) == 60
    for m, s, h in zip(result["macd"], result["signal"], result["histogram"]):
        if m is not None and s is not None:
            assert math.isclose(h, m - s)


def test_bollinger_bands_surround_middle():
    closes = [100.0 + (i % 5) for i in range(40)]
    bands = bollinger(closes, 20)
    for mid, up, low in zip(bands["middle"], bands["upper"], bands["lower"]):
        if mid is not None:
            assert low <= mid <= up
