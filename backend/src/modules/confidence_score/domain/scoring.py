"""Score global de confiance (docs/roadmap #3): a single trust meter for the
current analysis on an instrument, layered on top of the Meta Decision
Engine's already disagreement-aware fused confidence (which itself already
combines IA, Analyse Technique, Smart Money Concepts, Sentiment and Régime de
marché — see meta_decision_engine). This module adds exactly the two
dimensions the roadmap calls out that Meta Decision does not compute:
Corrélations (do correlated peers confirm the same move, or is this an
idiosyncratic, unconfirmed signal?) and an explicit Volatilité penalty.

No black box: every adjustment is a named, explained multiplier — never an
opaque learned weight."""

from dataclasses import dataclass

_MIN_CORRELATION = 0.5
_STRONG_AGREEMENT = 0.66
_STRONG_DISAGREEMENT = 0.33
_CORRELATION_BOOST = 1.15
_CORRELATION_DAMPEN = 0.75
_HIGH_VOLATILITY_DAMPEN = 0.75


@dataclass(frozen=True)
class ConfidenceFactor:
    name: str
    multiplier: float
    explanation: str


@dataclass(frozen=True)
class GlobalConfidenceScore:
    score: float
    level: str
    base_confidence: float
    factors: list[ConfidenceFactor]
    explanation: str


def confidence_level(score: float) -> str:
    if score >= 65:
        return "élevé"
    if score >= 40:
        return "modéré"
    return "faible"


def correlation_confirmation_factor(
    direction: str, peers: list[tuple[float | None, str]]
) -> ConfidenceFactor:
    """`peers`: (pearson correlation with the target, peer's own recent
    direction) for each candidate peer instrument. Only peers with a
    meaningful correlation magnitude and a non-neutral direction of their own
    can confirm or contradict anything."""
    relevant = [
        (pearson, peer_direction)
        for pearson, peer_direction in peers
        if pearson is not None and abs(pearson) >= _MIN_CORRELATION and peer_direction != "neutral"
    ]
    if direction == "neutral" or len(relevant) < 2:
        return ConfidenceFactor(
            "correlation",
            1.0,
            "Corrélations insuffisantes ou signal neutre — aucun ajustement.",
        )

    agreements = 0
    for pearson, peer_direction in relevant:
        expected = (
            peer_direction
            if pearson > 0
            else ("bearish" if peer_direction == "bullish" else "bullish")
        )
        if expected == direction:
            agreements += 1
    ratio = agreements / len(relevant)

    if ratio >= _STRONG_AGREEMENT:
        return ConfidenceFactor(
            "correlation",
            _CORRELATION_BOOST,
            f"{agreements}/{len(relevant)} instrument(s) corrélé(s) confirment la "
            f"direction — confiance renforcée de {(_CORRELATION_BOOST - 1) * 100:.0f} %.",
        )
    if ratio <= _STRONG_DISAGREEMENT:
        return ConfidenceFactor(
            "correlation",
            _CORRELATION_DAMPEN,
            f"Seulement {agreements}/{len(relevant)} instrument(s) corrélé(s) "
            "confirment la direction — signal potentiellement idiosyncratique, "
            f"confiance réduite de {(1 - _CORRELATION_DAMPEN) * 100:.0f} %.",
        )
    return ConfidenceFactor(
        "correlation",
        1.0,
        f"{agreements}/{len(relevant)} instrument(s) corrélé(s) confirment la "
        "direction — signal mitigé, aucun ajustement.",
    )


def volatility_penalty_factor(volatility_state: str | None) -> ConfidenceFactor:
    if volatility_state is None:
        return ConfidenceFactor(
            "volatility", 1.0, "Régime de volatilité indisponible — aucun ajustement."
        )
    if volatility_state == "high":
        return ConfidenceFactor(
            "volatility",
            _HIGH_VOLATILITY_DAMPEN,
            "Volatilité élevée détectée (Market Regime Detector) — signal moins "
            f"fiable dans un marché agité, confiance réduite de "
            f"{(1 - _HIGH_VOLATILITY_DAMPEN) * 100:.0f} %.",
        )
    return ConfidenceFactor(
        "volatility", 1.0, f"Volatilité {volatility_state} — aucun ajustement nécessaire."
    )


def aggregate_global_score(
    base_confidence: float, factors: list[ConfidenceFactor]
) -> GlobalConfidenceScore:
    multiplier = 1.0
    for factor in factors:
        multiplier *= factor.multiplier
    score = round(max(0.0, min(1.0, base_confidence * multiplier)) * 100, 1)
    level = confidence_level(score)
    explanation = (
        f"Score global de confiance : {score:.0f}/100 ({level}). Base (Meta "
        "Decision Engine — fusion IA, Analyse Technique, Smart Money Concepts, "
        f"Sentiment et Régime de marché) : {base_confidence * 100:.0f} %. "
        + " ".join(f.explanation for f in factors)
    )
    return GlobalConfidenceScore(score, level, base_confidence, factors, explanation)
