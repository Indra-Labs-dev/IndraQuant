from src.modules.market_regime.domain.detector import detect_regime, efficiency_ratio


def _straight_uptrend(n: int = 120, start: float = 100.0, step: float = 1.0) -> list[float]:
    return [start + i * step for i in range(n)]


def _straight_downtrend(n: int = 120, start: float = 300.0, step: float = 1.0) -> list[float]:
    return [start - i * step for i in range(n)]


def _choppy_range(n: int = 120, base: float = 100.0) -> list[float]:
    return [base + (5 if i % 2 == 0 else -5) for i in range(n)]


def test_efficiency_ratio_high_on_straight_trend():
    er = efficiency_ratio(_straight_uptrend(30), window=20)
    assert er is not None
    assert er > 0.9


def test_efficiency_ratio_low_on_choppy_series():
    er = efficiency_ratio(_choppy_range(30), window=20)
    assert er is not None
    assert er < 0.3


def test_efficiency_ratio_none_with_insufficient_history():
    assert efficiency_ratio([100.0, 101.0], window=20) is None


def test_detect_regime_bull_on_strong_uptrend():
    regime = detect_regime(_straight_uptrend())
    assert regime.trend == "bull"
    assert regime.is_trending is True
    assert regime.is_panic is False
    assert regime.confidence > 0


def test_detect_regime_bear_on_strong_downtrend():
    regime = detect_regime(_straight_downtrend())
    assert regime.trend == "bear"
    assert regime.is_trending is True


def test_detect_regime_range_on_choppy_series():
    regime = detect_regime(_choppy_range())
    assert regime.trend == "range"
    assert regime.is_trending is False


def test_detect_regime_indeterminate_with_insufficient_history():
    regime = detect_regime([100.0, 101.0, 102.0])
    assert regime.trend == "range"
    assert regime.confidence == 0.0
    assert regime.label == "Indéterminé"


def test_detect_regime_panic_on_volatility_spike_and_crash():
    # A long, calm history followed by a sudden, sharp drop with a burst
    # of volatility should trip the panic flag.
    calm = [100.0 + (i % 2) * 0.05 for i in range(90)]
    crash = [100.0 - i * 4.0 for i in range(1, 6)]
    regime = detect_regime(calm + crash)
    assert regime.volatility == "high"
    assert regime.is_panic is True
    assert regime.label == "Panic market"
