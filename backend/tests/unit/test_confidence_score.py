from src.modules.confidence_score.domain.scoring import (
    aggregate_global_score,
    confidence_level,
    correlation_confirmation_factor,
    volatility_penalty_factor,
)


def test_confidence_level_thresholds():
    assert confidence_level(70) == "élevé"
    assert confidence_level(50) == "modéré"
    assert confidence_level(20) == "faible"


def test_correlation_confirmation_boosts_when_peers_agree():
    peers = [(0.8, "bullish"), (0.7, "bullish"), (0.6, "bullish")]
    factor = correlation_confirmation_factor("bullish", peers)
    assert factor.multiplier > 1.0


def test_correlation_confirmation_dampens_when_peers_disagree():
    peers = [(0.8, "bearish"), (0.7, "bearish"), (0.6, "bearish")]
    factor = correlation_confirmation_factor("bullish", peers)
    assert factor.multiplier < 1.0


def test_correlation_confirmation_handles_negative_pearson():
    # Negative correlation: a bearish peer confirms a bullish direction.
    peers = [(-0.8, "bearish"), (-0.7, "bearish"), (-0.6, "bearish")]
    factor = correlation_confirmation_factor("bullish", peers)
    assert factor.multiplier > 1.0


def test_correlation_confirmation_neutral_with_insufficient_peers():
    factor = correlation_confirmation_factor("bullish", [(0.8, "bullish")])
    assert factor.multiplier == 1.0


def test_correlation_confirmation_neutral_when_direction_neutral():
    peers = [(0.8, "bullish"), (0.7, "bullish")]
    factor = correlation_confirmation_factor("neutral", peers)
    assert factor.multiplier == 1.0


def test_correlation_confirmation_ignores_weak_correlations():
    peers = [(0.1, "bullish"), (0.2, "bearish")]
    factor = correlation_confirmation_factor("bullish", peers)
    assert factor.multiplier == 1.0


def test_volatility_penalty_dampens_high_volatility():
    factor = volatility_penalty_factor("high")
    assert factor.multiplier < 1.0


def test_volatility_penalty_neutral_otherwise():
    assert volatility_penalty_factor("normal").multiplier == 1.0
    assert volatility_penalty_factor("low").multiplier == 1.0
    assert volatility_penalty_factor(None).multiplier == 1.0


def test_aggregate_global_score_combines_factors_multiplicatively():
    from src.modules.confidence_score.domain.scoring import ConfidenceFactor

    result = aggregate_global_score(
        0.5,
        [ConfidenceFactor("a", 1.15, "boost"), ConfidenceFactor("b", 0.75, "dampen")],
    )
    assert 0 <= result.score <= 100
    assert abs(result.score - 0.5 * 1.15 * 0.75 * 100) < 0.05
    assert result.level == confidence_level(result.score)


def test_aggregate_global_score_clips_to_valid_range():
    from src.modules.confidence_score.domain.scoring import ConfidenceFactor

    result = aggregate_global_score(0.9, [ConfidenceFactor("a", 2.0, "boost")])
    assert result.score == 100.0
