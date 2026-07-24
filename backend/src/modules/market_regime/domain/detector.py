"""Market Regime Detector: classifies the current market condition — trend
(bull/bear/range), volatility state (high/low/normal) and a panic-market
flag — from pure price-series analysis. No black box: every classification
traces back to two well-known, explainable statistics (Kaufman's Efficiency
Ratio for trend strength, a rolling-volatility z-score for the volatility
state) rather than a trained model.
"""

from dataclasses import dataclass

from src.modules.feature_engineering.application import service as fe

TrendState = str  # "bull" | "bear" | "range"
VolatilityState = str  # "high" | "low" | "normal"

_TREND_WINDOW = 50
_ER_WINDOW = 20
_VOL_WINDOW = 20
_VOL_HISTORY = 90
_ER_TRENDING_THRESHOLD = 0.35
_SLOPE_THRESHOLD = 0.01


@dataclass(frozen=True)
class MarketRegime:
    trend: TrendState
    volatility: VolatilityState
    is_trending: bool
    is_panic: bool
    confidence: float
    label: str
    explanation: str


def efficiency_ratio(closes: list[float], window: int = _ER_WINDOW) -> float | None:
    """Kaufman's Efficiency Ratio: net displacement over total path length.
    Near 1 = an efficient, strongly trending move; near 0 = a choppy,
    range-bound market (lots of back-and-forth for little net progress)."""
    if len(closes) <= window:
        return None
    segment = closes[-(window + 1):]
    net = abs(segment[-1] - segment[0])
    path = sum(abs(segment[i] - segment[i - 1]) for i in range(1, len(segment)))
    return net / path if path > 0 else 0.0


def detect_regime(
    closes: list[float],
    trend_window: int = _TREND_WINDOW,
    er_window: int = _ER_WINDOW,
    vol_window: int = _VOL_WINDOW,
    vol_history: int = _VOL_HISTORY,
) -> MarketRegime:
    sma = fe.rolling_mean(closes, trend_window)
    returns = fe.returns(closes)
    vols = fe.rolling_std([r if r is not None else 0.0 for r in returns], vol_window)

    if len(closes) <= max(trend_window, er_window) + 5 or sma[-1] is None:
        return MarketRegime(
            "range",
            "normal",
            False,
            False,
            0.0,
            "Indéterminé",
            "Historique insuffisant pour détecter le régime de marché.",
        )

    price = closes[-1]
    sma_now = sma[-1]
    lag_index = -(trend_window // 2) - 1
    sma_past = sma[lag_index] if len(sma) >= abs(lag_index) and sma[lag_index] else None
    sma_slope = (sma_now - sma_past) / sma_past if sma_past else 0.0

    er = efficiency_ratio(closes, er_window) or 0.0
    is_trending = er >= _ER_TRENDING_THRESHOLD

    if is_trending and sma_slope > _SLOPE_THRESHOLD and price > sma_now:
        trend: TrendState = "bull"
    elif is_trending and sma_slope < -_SLOPE_THRESHOLD and price < sma_now:
        trend = "bear"
    else:
        trend = "range"

    valid_vols = [v for v in vols[-vol_history:] if v is not None]
    current_vol = vols[-1]
    z = 0.0
    if current_vol is not None and len(valid_vols) >= 10:
        mean_v = sum(valid_vols) / len(valid_vols)
        std_v = (sum((v - mean_v) ** 2 for v in valid_vols) / len(valid_vols)) ** 0.5
        z = (current_vol - mean_v) / std_v if std_v > 0 else 0.0
    volatility: VolatilityState = "high" if z > 1.0 else "low" if z < -1.0 else "normal"

    last_return = returns[-1] if returns[-1] is not None else 0.0
    is_panic = volatility == "high" and z > 2.5 and last_return < -0.02 and trend != "bull"

    confidence = round(min(0.4 + er * 0.4 + min(abs(z), 2.0) * 0.1, 0.95), 4)
    labels = {
        "bull": "Marché haussier (bull)",
        "bear": "Marché baissier (bear)",
        "range": "Marché en range",
    }
    label = "Panic market" if is_panic else labels[trend]

    explanation = (
        f"Ratio d'efficacité de Kaufman {er:.2f} sur {er_window} bougies "
        f"({'tendance nette' if is_trending else 'marché choppy/range'}), "
        f"pente MM{trend_window} {sma_slope * 100:+.2f} %, "
        f"volatilité {volatility} (z-score {z:+.2f})."
        + (
            " Mouvement brutal et volatilité extrême détectés — régime de panique."
            if is_panic
            else ""
        )
    )

    return MarketRegime(trend, volatility, is_trending, is_panic, confidence, label, explanation)
