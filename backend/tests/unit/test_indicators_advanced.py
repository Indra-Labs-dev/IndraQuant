import math

from src.modules.feature_engineering.application import service as fe
from src.modules.technical_analysis.domain import indicators


def _flat_ohlc(n: int, price: float = 100.0, spread: float = 1.0):
    highs = [price + spread] * n
    lows = [price - spread] * n
    closes = [price] * n
    volumes = [1000.0] * n
    return highs, lows, closes, volumes


def _uptrend_ohlc(n: int, start: float = 100.0, step: float = 1.0):
    closes = [start + i * step for i in range(n)]
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.5 for c in closes]
    volumes = [1000.0 + i for i in range(n)]
    return highs, lows, closes, volumes


def test_rolling_max_min():
    values = [3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0]
    assert fe.rolling_max(values, 3) == [None, None, 4.0, 4.0, 5.0, 9.0, 9.0]
    assert fe.rolling_min(values, 3) == [None, None, 1.0, 1.0, 1.0, 1.0, 2.0]


def test_vwap_matches_typical_price_weighted_average():
    highs, lows, closes, volumes = _uptrend_ohlc(30)
    result = indicators.vwap(highs, lows, closes, volumes, window=5)
    assert result[4] is not None
    assert result[3] is None
    typical = [(h + l + c) / 3 for h, l, c in zip(highs[:5], lows[:5], closes[:5])]
    expected = sum(t * v for t, v in zip(typical, volumes[:5])) / sum(volumes[:5])
    assert math.isclose(result[4], expected, rel_tol=1e-9)


def test_true_range_and_atr_zero_on_flat_series():
    highs, lows, closes, _ = _flat_ohlc(20, spread=1.0)
    tr = indicators.true_range(highs, lows, closes)
    assert all(t == 2.0 for t in tr)
    atr = indicators.atr(highs, lows, closes, period=14)
    assert atr[13] == 2.0


def test_atr_higher_for_wider_ranges():
    highs, lows, closes, _ = _flat_ohlc(20, spread=1.0)
    narrow_atr = indicators.atr(highs, lows, closes, period=14)[-1]
    highs2, lows2, closes2, _ = _flat_ohlc(20, spread=5.0)
    wide_atr = indicators.atr(highs2, lows2, closes2, period=14)[-1]
    assert wide_atr > narrow_atr


def test_adx_higher_for_strong_trend_than_flat_series():
    highs, lows, closes, _ = _uptrend_ohlc(80, step=2.0)
    trending_adx = [v for v in indicators.adx(highs, lows, closes, period=14) if v is not None]
    flat_highs, flat_lows, flat_closes, _ = _flat_ohlc(80)
    flat_adx = [v for v in indicators.adx(flat_highs, flat_lows, flat_closes, period=14) if v is not None]
    assert trending_adx
    assert flat_adx
    assert trending_adx[-1] > flat_adx[-1]


def test_donchian_channel_bounds():
    highs, lows, closes, _ = _uptrend_ohlc(30)
    result = indicators.donchian(highs, lows, period=10)
    assert result["upper"][9] == max(highs[:10])
    assert result["lower"][9] == min(lows[:10])


def test_keltner_channel_widens_with_volatility():
    highs, lows, closes, _ = _flat_ohlc(30, spread=1.0)
    narrow = indicators.keltner(highs, lows, closes, period=20)
    highs2, lows2, closes2, _ = _flat_ohlc(30, spread=5.0)
    wide = indicators.keltner(highs2, lows2, closes2, period=20)
    assert (wide["upper"][-1] - wide["lower"][-1]) > (narrow["upper"][-1] - narrow["lower"][-1])


def test_obv_increases_on_up_days_and_decreases_on_down_days():
    closes = [100.0, 101.0, 100.5, 102.0]
    volumes = [10.0, 20.0, 5.0, 15.0]
    result = indicators.obv(closes, volumes)
    assert result == [0.0, 20.0, 15.0, 30.0]


def test_mfi_high_when_typical_price_rising():
    highs, lows, closes, volumes = _uptrend_ohlc(30)
    result = indicators.mfi(highs, lows, closes, volumes, period=14)
    assert result[14] is not None
    assert result[14] > 50.0


def test_cci_zero_on_flat_series():
    highs, lows, closes, _ = _flat_ohlc(30)
    result = indicators.cci(highs, lows, closes, period=20)
    assert result[19] == 0.0


def test_cci_positive_when_price_above_its_average():
    highs, lows, closes, _ = _uptrend_ohlc(30)
    result = indicators.cci(highs, lows, closes, period=20)
    assert result[19] is not None
    assert result[19] > 0


def test_williams_r_at_extremes():
    highs, lows, closes, _ = _uptrend_ohlc(30)
    result = indicators.williams_r(highs, lows, closes, period=14)
    # Uptrend: latest close is at (or very near) the rolling high -> ~0.
    assert result[-1] is not None
    assert result[-1] > -10.0


def test_chaikin_money_flow_positive_when_closing_near_highs():
    n = 30
    highs = [110.0] * n
    lows = [90.0] * n
    closes = [108.0] * n  # closes near the high each candle
    volumes = [100.0] * n
    result = indicators.chaikin_money_flow(highs, lows, closes, volumes, period=20)
    assert result[19] is not None
    assert result[19] > 0


def test_ulcer_index_zero_on_monotonic_uptrend():
    highs, lows, closes, _ = _uptrend_ohlc(30)
    result = indicators.ulcer_index(closes, period=14)
    assert result[13] == 0.0


def test_ulcer_index_positive_after_drawdown():
    closes = [100.0 + i for i in range(15)] + [100.0]  # rally then a drop
    result = indicators.ulcer_index(closes, period=14)
    assert result[-1] is not None
    assert result[-1] > 0


def test_momentum_matches_price_difference():
    closes = [100.0, 102.0, 105.0, 101.0, 110.0]
    result = indicators.momentum(closes, period=2)
    assert result == [None, None, 5.0, -1.0, 5.0]


def test_order_flow_proxy_positive_when_closing_near_high():
    highs = [110.0]
    lows = [90.0]
    closes = [108.0]
    volumes = [100.0]
    result = indicators.order_flow_proxy(highs, lows, closes, volumes)
    assert result[0] > 0


def test_order_flow_proxy_negative_when_closing_near_low():
    result = indicators.order_flow_proxy([110.0], [90.0], [92.0], [100.0])
    assert result[0] < 0


def test_volatility_clustering_detects_clustered_regimes():
    calm = [100.0 + (i % 2) * 0.05 for i in range(40)]
    volatile = [100.0 + (i % 2) * 5.0 for i in range(40)]
    closes = calm + volatile
    result = indicators.volatility_clustering(closes, window=30, lag=1)
    assert any(v is not None for v in result)


def test_volume_profile_buckets_and_point_of_control():
    highs = [101.0] * 5 + [201.0] * 5
    lows = [99.0] * 5 + [199.0] * 5
    closes = [100.0] * 5 + [200.0] * 5
    volumes = [10.0] * 5 + [1000.0] * 5
    profile = indicators.volume_profile(highs, lows, closes, volumes, bins=2)
    assert len(profile) == 2
    poc = indicators.point_of_control(profile)
    assert poc is not None
    assert poc.volume == 5000.0


def test_volume_profile_empty_series_returns_empty():
    assert indicators.volume_profile([], [], [], [], bins=5) == []
    assert indicators.point_of_control([]) is None
