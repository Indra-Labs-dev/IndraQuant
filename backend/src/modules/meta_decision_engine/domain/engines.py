"""Meta Decision Engine: specialized signal engines and their fusion.

Each engine is a pure function producing an `EngineSignal` (direction,
score in [-1, 1], confidence in [0, 1], French explanation) from data it is
independently responsible for. `fuse()` combines them into one decision
without hiding disagreement: the fused confidence is reduced whenever
engines vote differently, so the system never looks more certain than the
underlying evidence actually supports (docs/01 — explicable, jamais boîte
noire).
"""

from dataclasses import dataclass

from src.modules.feature_store.domain.feature_vector import FeatureVector

Direction = str  # "bullish" | "bearish" | "neutral"

# Default fusion weights. The ML engine carries the most weight (it already
# aggregates an ensemble model with its own SHAP explanation and calibrated
# track record); macro/news carry the least since they are market-wide,
# not instrument-specific.
DEFAULT_WEIGHTS: dict[str, float] = {
    "ml": 0.30,
    "trend": 0.20,
    "mean_reversion": 0.15,
    "liquidity": 0.15,
    "volatility": 0.08,
    "news": 0.07,
    "macro": 0.05,
}


@dataclass(frozen=True)
class EngineSignal:
    engine: str
    direction: Direction
    score: float
    confidence: float
    explanation: str


@dataclass(frozen=True)
class MetaDecision:
    direction: Direction
    score: float
    confidence: float
    engines: list[EngineSignal]
    explanation: str


def _direction_from_score(score: float, neutral_band: float = 0.05) -> Direction:
    if score > neutral_band:
        return "bullish"
    if score < -neutral_band:
        return "bearish"
    return "neutral"


def trend_engine(features: FeatureVector) -> EngineSignal:
    """SMA20/SMA50/MACD-histogram alignment — classic trend-following read.
    Reads pre-computed values from the Feature Store instead of
    recomputing SMA/MACD from raw closes (docs/roadmap #5)."""
    price = features.price
    s20, s50, h = features.sma_20, features.sma_50, features.macd_histogram

    if s20 is None or s50 is None or h is None or s50 == 0:
        return EngineSignal(
            "trend",
            "neutral",
            0.0,
            0.0,
            "Historique insuffisant pour évaluer la tendance.",
        )

    votes = (1 if price > s20 else -1) + (1 if s20 > s50 else -1) + (1 if h > 0 else -1)
    score = votes / 3.0
    strength = abs((s20 - s50) / s50)
    confidence = round(min(0.5 + strength * 20, 0.95), 4)
    return EngineSignal(
        "trend",
        _direction_from_score(score),
        round(score, 4),
        confidence,
        f"Prix {'au-dessus' if price > s20 else 'en dessous'} de la MM20, "
        f"MM20 {'au-dessus' if s20 > s50 else 'en dessous'} de la MM50, "
        f"histogramme MACD {'positif' if h > 0 else 'négatif'}.",
    )


def mean_reversion_engine(features: FeatureVector) -> EngineSignal:
    """RSI14 + position in Bollinger Bands — extremes suggest a bounce back
    toward the mean rather than continuation. Reads the shared Feature
    Store vector instead of recomputing RSI/Bollinger (docs/roadmap #5)."""
    price = features.price
    r, upper, lower = features.rsi_14, features.bollinger_upper, features.bollinger_lower

    if r is None or upper is None or lower is None or upper == lower:
        return EngineSignal(
            "mean_reversion",
            "neutral",
            0.0,
            0.0,
            "Historique insuffisant pour évaluer un retour à la moyenne.",
        )

    percent_b = (price - lower) / (upper - lower)
    rsi_signal = (50.0 - r) / 50.0
    band_signal = (0.5 - percent_b) * 2
    score = max(min((rsi_signal + band_signal) / 2.0, 1.0), -1.0)
    extreme = max(abs(r - 50) / 50.0, abs(percent_b - 0.5) * 2)
    confidence = round(min(0.4 + extreme * 0.6, 0.9), 4)
    return EngineSignal(
        "mean_reversion",
        _direction_from_score(score, neutral_band=0.15),
        round(score, 4),
        confidence,
        f"RSI 14 à {r:.1f}, position dans les bandes de Bollinger à "
        f"{percent_b * 100:.0f} %.",
    )


def volatility_engine(features: FeatureVector, history: int = 90) -> EngineSignal:
    """Reads volatility clustering: expanding volatility in the direction of
    the latest move is read as a (low-confidence) continuation signal;
    contracting or average volatility carries no directional bias. The
    z-score itself comes pre-computed from the Feature Store (docs/roadmap
    #5) instead of being recomputed from raw closes."""
    z = features.volatility_z_score
    last_return = features.return_1 if features.return_1 is not None else 0.0

    if z is None:
        return EngineSignal(
            "volatility",
            "neutral",
            0.0,
            0.0,
            "Historique insuffisant pour évaluer le régime de volatilité.",
        )

    regime = "élevée" if z > 1.0 else "faible" if z < -1.0 else "normale"
    score = 0.0
    if z > 0.5:
        score = max(min(z, 3.0), -3.0) / 3.0 * (1.0 if last_return >= 0 else -1.0)
    confidence = round(min(0.3 + abs(z) * 0.2, 0.85), 4)
    return EngineSignal(
        "volatility",
        _direction_from_score(score, neutral_band=0.1),
        round(score, 4),
        confidence,
        f"Volatilité {regime} (z-score {z:+.2f} sur {history} bougies) — "
        + (
            "continuation probable dans le sens du dernier mouvement."
            if abs(score) > 0.1
            else "pas de biais directionnel clair."
        ),
    )


def liquidity_engine(
    features: FeatureVector, smc_signals: list[tuple[str, float]]
) -> EngineSignal:
    """Volume z-score (from the Feature Store, docs/roadmap #5) plus recent
    Smart Money Concepts detections (break of structure, liquidity sweep,
    FVG, order block) — each passed in as a plain (direction, confidence)
    pair so this domain stays decoupled from `smart_money`'s own types."""
    volume_z = features.volume_z_score if features.volume_z_score is not None else 0.0

    if not smc_signals:
        return EngineSignal(
            "liquidity",
            "neutral",
            0.0,
            round(min(0.2 + abs(volume_z) * 0.1, 0.5), 4),
            f"Volume actuel z-score {volume_z:+.2f}, aucune structure de "
            "liquidité (SMC) détectée récemment.",
        )

    bullish = sum(c for d, c in smc_signals if d == "bullish")
    bearish = sum(c for d, c in smc_signals if d == "bearish")
    total = bullish + bearish
    score = (bullish - bearish) / total if total > 0 else 0.0
    volume_boost = min(abs(volume_z) * 0.1, 0.2)
    confidence = round(
        min(0.4 + (total / len(smc_signals)) * 0.3 + volume_boost, 0.9), 4
    )
    return EngineSignal(
        "liquidity",
        _direction_from_score(score, neutral_band=0.1),
        round(score, 4),
        confidence,
        f"{len(smc_signals)} structure(s) de liquidité (SMC) récente(s) — "
        f"{bullish:.1f} pt(s) haussier(s) vs {bearish:.1f} pt(s) baissier(s), "
        f"volume z-score {volume_z:+.2f}.",
    )


def fuse(
    signals: list[EngineSignal], weights: dict[str, float] | None = None
) -> MetaDecision:
    """Weighted fusion of engine signals. Confidence is penalized by
    cross-engine disagreement (weighted variance of scores) rather than
    simply averaged away — a fused decision only looks confident when the
    engines actually agree."""
    weights = weights or DEFAULT_WEIGHTS
    active = [s for s in signals if s.confidence > 0]
    if not active:
        return MetaDecision(
            "neutral",
            0.0,
            0.0,
            list(signals),
            "Aucun moteur n'a pu produire de signal exploitable.",
        )

    total_weight = sum(weights.get(s.engine, 0.0) * s.confidence for s in active)
    if total_weight <= 0:
        return MetaDecision(
            "neutral",
            0.0,
            0.0,
            list(signals),
            "Poids cumulés nuls — signal insuffisant pour trancher.",
        )

    fused_score = (
        sum(s.score * weights.get(s.engine, 0.0) * s.confidence for s in active)
        / total_weight
    )
    confidence_weight = sum(weights.get(s.engine, 0.0) for s in active)
    mean_conf = (
        sum(weights.get(s.engine, 0.0) * s.confidence for s in active)
        / confidence_weight
        if confidence_weight > 0
        else 0.0
    )
    variance = (
        sum(
            weights.get(s.engine, 0.0) * s.confidence * (s.score - fused_score) ** 2
            for s in active
        )
        / total_weight
    )
    disagreement = min(variance**0.5, 1.0)
    fused_confidence = max(mean_conf * (1.0 - disagreement), 0.0)

    direction = _direction_from_score(fused_score)
    votes = ", ".join(
        f"{s.engine} ({s.direction}, {s.score:+.2f}, conf. {s.confidence * 100:.0f} %)"
        for s in signals
    )
    explanation = (
        f"Décision fusionnée : {direction} (score {fused_score:+.2f}, "
        f"confiance {fused_confidence * 100:.1f} %). "
        + (
            "Fort consensus entre moteurs."
            if disagreement < 0.2
            else "Désaccord notable entre moteurs — confiance réduite en conséquence."
        )
        + f" Détail par moteur : {votes}."
    )
    return MetaDecision(
        direction, round(fused_score, 4), round(fused_confidence, 4), list(signals), explanation
    )
