"""Chartist pattern detection as pure functions. Every detection carries a
confidence score in [0, 1] and a human-readable French explanation — outputs
are probabilistic and explainable, never binary (docs/01).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Ohlc:
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class PatternDetection:
    pattern: str
    index: int
    direction: str
    confidence: float
    explanation: str


def detect_engulfing(candles: list[Ohlc]) -> list[PatternDetection]:
    detections = []
    for i in range(1, len(candles)):
        previous, current = candles[i - 1], candles[i]
        prev_body = abs(previous.close - previous.open)
        curr_body = abs(current.close - current.open)
        if prev_body == 0 or curr_body == 0:
            continue

        bullish = (
            previous.close < previous.open
            and current.close > current.open
            and current.open <= previous.close
            and current.close >= previous.open
        )
        bearish = (
            previous.close > previous.open
            and current.close < current.open
            and current.open >= previous.close
            and current.close <= previous.open
        )
        if not (bullish or bearish):
            continue

        ratio = min(curr_body / prev_body, 3.0)
        confidence = round(min(0.5 + (ratio - 1.0) * 0.25, 0.95), 2)
        if confidence < 0.5:
            continue
        direction = "bullish" if bullish else "bearish"
        label = "haussier" if bullish else "baissier"
        detections.append(
            PatternDetection(
                pattern="engulfing",
                index=i,
                direction=direction,
                confidence=confidence,
                explanation=(
                    f"Avalement {label} : le corps de la bougie couvre "
                    f"{ratio:.1f}× le corps précédent de sens opposé."
                ),
            )
        )
    return detections


def detect_hammer(candles: list[Ohlc]) -> list[PatternDetection]:
    detections = []
    for i, candle in enumerate(candles):
        body = abs(candle.close - candle.open)
        total = candle.high - candle.low
        if total == 0 or body == 0:
            continue
        lower_wick = min(candle.open, candle.close) - candle.low
        upper_wick = candle.high - max(candle.open, candle.close)
        if lower_wick >= 2 * body and upper_wick <= 0.5 * body:
            wick_ratio = min(lower_wick / body, 4.0)
            confidence = round(min(0.5 + (wick_ratio - 2.0) * 0.15, 0.9), 2)
            detections.append(
                PatternDetection(
                    pattern="hammer",
                    index=i,
                    direction="bullish",
                    confidence=confidence,
                    explanation=(
                        f"Marteau : mèche basse {wick_ratio:.1f}× le corps, "
                        "mèche haute négligeable — rejet des prix bas."
                    ),
                )
            )
    return detections


def detect_double_top(
    candles: list[Ohlc], tolerance: float = 0.004, min_gap: int = 5
) -> list[PatternDetection]:
    highs = [c.high for c in candles]
    peaks = [
        i
        for i in range(1, len(highs) - 1)
        if highs[i] >= highs[i - 1] and highs[i] >= highs[i + 1]
    ]
    detections = []
    for a in range(len(peaks)):
        for b in range(a + 1, len(peaks)):
            i, j = peaks[a], peaks[b]
            if j - i < min_gap:
                continue
            difference = abs(highs[i] - highs[j]) / highs[i]
            if difference > tolerance:
                continue
            valley = min(candles[k].low for k in range(i, j + 1))
            depth = (min(highs[i], highs[j]) - valley) / highs[i]
            if depth < 0.005:
                continue
            confidence = round(
                min(0.5 + (tolerance - difference) / tolerance * 0.2 + depth * 10, 0.9),
                2,
            )
            detections.append(
                PatternDetection(
                    pattern="double_top",
                    index=j,
                    direction="bearish",
                    confidence=confidence,
                    explanation=(
                        f"Double sommet : deux pics à {difference * 100:.2f} % "
                        f"l'un de l'autre séparés de {j - i} bougies, creux "
                        f"intermédiaire de {depth * 100:.1f} %."
                    ),
                )
            )
    return detections
