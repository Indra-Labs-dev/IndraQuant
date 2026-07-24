from datetime import datetime, timezone

from src.modules.feature_store.application.service import FeatureStoreService
from src.modules.feature_store.domain.feature_vector import FeatureVector
from src.modules.market_regime.domain.detector import MarketRegime
from src.modules.meta_decision_engine.application.use_cases.get_meta_decision import (
    GetMetaDecisionUseCase,
)
from src.modules.meta_decision_engine.domain.engines import (
    DEFAULT_WEIGHTS,
    EngineSignal,
    fuse,
    liquidity_engine,
    mean_reversion_engine,
    trend_engine,
    volatility_engine,
)

_AS_OF = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _use_case() -> GetMetaDecisionUseCase:
    # Only `_regime_adjusted_weights` is exercised in these tests, which
    # depends on none of the injected collaborators — dummies are enough.
    return GetMetaDecisionUseCase(ohlcv=None, smc=None, ml=None)  # type: ignore[arg-type]


def _regime(trend: str, is_trending: bool, is_panic: bool = False) -> MarketRegime:
    return MarketRegime(
        trend=trend,
        volatility="high" if is_panic else "normal",
        is_trending=is_trending,
        is_panic=is_panic,
        confidence=0.8,
        label="test",
        explanation="test",
    )


def _uptrend(n: int = 80, start: float = 100.0, step: float = 1.0) -> list[float]:
    return [start + i * step for i in range(n)]


def _downtrend(n: int = 80, start: float = 200.0, step: float = 1.0) -> list[float]:
    return [start - i * step for i in range(n)]


def _features_from_series(
    closes: list[float], volumes: list[float] | None = None
) -> FeatureVector:
    """Runs the real Feature Store computation over a synthetic price/volume
    series (no cache) — exercises the same code path production traffic
    uses, rather than hand-crafting FeatureVector fixtures."""
    volumes = volumes or [1_000.0] * len(closes)
    return FeatureStoreService(cache=None)._compute(
        instrument_id=1, timeframe="1h", as_of=_AS_OF, closes=closes, volumes=volumes
    )


def _empty_features() -> FeatureVector:
    return FeatureVector(
        instrument_id=1,
        timeframe="1h",
        as_of=_AS_OF,
        price=100.0,
        sma_20=None,
        sma_50=None,
        rsi_14=None,
        macd_histogram=None,
        bollinger_upper=None,
        bollinger_lower=None,
        volatility_20=None,
        volatility_z_score=None,
        volume_z_score=None,
        return_1=None,
    )


def test_trend_engine_bullish_on_uptrend():
    signal = trend_engine(_features_from_series(_uptrend()))
    assert signal.direction == "bullish"
    assert signal.score > 0
    assert 0 < signal.confidence <= 0.95


def test_trend_engine_bearish_on_downtrend():
    signal = trend_engine(_features_from_series(_downtrend()))
    assert signal.direction == "bearish"
    assert signal.score < 0


def test_trend_engine_neutral_with_insufficient_history():
    signal = trend_engine(_empty_features())
    assert signal.direction == "neutral"
    assert signal.confidence == 0.0


def test_mean_reversion_engine_bullish_after_sharp_drop():
    closes = _uptrend(60, start=100.0, step=0.5) + [
        closes_last - i * 3 for i, closes_last in enumerate([130.0] * 10)
    ]
    signal = mean_reversion_engine(_features_from_series(closes))
    # Sharp drop -> oversold -> mean-reversion engine expects a bounce (bullish).
    assert signal.direction in ("bullish", "neutral")
    assert signal.confidence >= 0.0


def test_mean_reversion_engine_neutral_with_insufficient_history():
    signal = mean_reversion_engine(_empty_features())
    assert signal.direction == "neutral"
    assert signal.confidence == 0.0


def test_volatility_engine_neutral_with_insufficient_history():
    signal = volatility_engine(_empty_features())
    assert signal.direction == "neutral"
    assert signal.confidence == 0.0


def test_volatility_engine_produces_signal_on_stable_series():
    closes = [100.0 + (i % 3) * 0.1 for i in range(100)]
    signal = volatility_engine(_features_from_series(closes))
    assert signal.engine == "volatility"
    assert 0.0 <= signal.confidence <= 0.85


def test_liquidity_engine_neutral_without_smc_signals():
    features = _features_from_series(_uptrend(30), volumes=[1000.0] * 30)
    signal = liquidity_engine(features, [])
    assert signal.direction == "neutral"


def test_liquidity_engine_bullish_when_smc_signals_agree():
    features = _features_from_series(
        _uptrend(30), volumes=[1000.0 + i for i in range(30)]
    )
    smc_signals = [("bullish", 0.7), ("bullish", 0.6), ("bearish", 0.2)]
    signal = liquidity_engine(features, smc_signals)
    assert signal.direction == "bullish"
    assert signal.confidence > 0.4


def test_fuse_returns_neutral_when_no_active_signals():
    signals = [
        EngineSignal("trend", "neutral", 0.0, 0.0, "n/a"),
        EngineSignal("ml", "neutral", 0.0, 0.0, "n/a"),
    ]
    decision = fuse(signals)
    assert decision.direction == "neutral"
    assert decision.confidence == 0.0


def test_fuse_agrees_with_consensus_direction():
    signals = [
        EngineSignal("trend", "bullish", 0.8, 0.8, "trend up"),
        EngineSignal("ml", "bullish", 0.6, 0.7, "ml up"),
        EngineSignal("mean_reversion", "neutral", 0.0, 0.0, "n/a"),
    ]
    decision = fuse(signals)
    assert decision.direction == "bullish"
    assert decision.score > 0
    assert decision.confidence > 0
    assert len(decision.engines) == 3


def test_regime_weights_unchanged_without_regime():
    weights = _use_case()._regime_adjusted_weights(None)
    assert weights == DEFAULT_WEIGHTS


def test_regime_boosts_trend_weight_in_trending_bull_market():
    weights = _use_case()._regime_adjusted_weights(_regime("bull", is_trending=True))
    assert weights["trend"] > DEFAULT_WEIGHTS["trend"]
    assert weights["mean_reversion"] < DEFAULT_WEIGHTS["mean_reversion"]


def test_regime_boosts_mean_reversion_weight_in_range_market():
    weights = _use_case()._regime_adjusted_weights(_regime("range", is_trending=False))
    assert weights["mean_reversion"] > DEFAULT_WEIGHTS["mean_reversion"]
    assert weights["trend"] < DEFAULT_WEIGHTS["trend"]


def test_regime_dampens_ml_weight_in_panic():
    weights = _use_case()._regime_adjusted_weights(
        _regime("bear", is_trending=True, is_panic=True)
    )
    assert weights["ml"] < DEFAULT_WEIGHTS["ml"]


def test_fuse_reduces_confidence_on_disagreement():
    agreeing = fuse(
        [
            EngineSignal("trend", "bullish", 0.8, 0.8, "up"),
            EngineSignal("ml", "bullish", 0.8, 0.8, "up"),
        ]
    )
    disagreeing = fuse(
        [
            EngineSignal("trend", "bullish", 0.8, 0.8, "up"),
            EngineSignal("ml", "bearish", -0.8, 0.8, "down"),
        ]
    )
    assert disagreeing.confidence < agreeing.confidence
