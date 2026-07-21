"""Minimal smart-money structure detection: swing points, break of
structure (BOS) and liquidity sweeps. Pure functions, explained outputs.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SmcCandle:
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class SmcDetection:
    kind: str
    index: int
    direction: str
    confidence: float
    explanation: str


def swing_highs(candles: list[SmcCandle], lookback: int = 2) -> list[int]:
    return [
        i
        for i in range(lookback, len(candles) - lookback)
        if all(
            candles[i].high >= candles[i + o].high
            for o in range(-lookback, lookback + 1)
        )
    ]


def swing_lows(candles: list[SmcCandle], lookback: int = 2) -> list[int]:
    return [
        i
        for i in range(lookback, len(candles) - lookback)
        if all(
            candles[i].low <= candles[i + o].low
            for o in range(-lookback, lookback + 1)
        )
    ]


def detect_structures(candles: list[SmcCandle]) -> list[SmcDetection]:
    highs = swing_highs(candles)
    lows = swing_lows(candles)
    detections: list[SmcDetection] = []

    for i in range(2, len(candles)):
        last_high = next((h for h in reversed(highs) if h < i - 2), None)
        last_low = next((l for l in reversed(lows) if l < i - 2), None)
        candle = candles[i]

        if last_high is not None:
            level = candles[last_high].high
            if candle.close > level:
                margin = (candle.close - level) / level
                detections.append(
                    SmcDetection(
                        kind="break_of_structure",
                        index=i,
                        direction="bullish",
                        confidence=round(min(0.5 + margin * 50, 0.9), 2),
                        explanation=(
                            f"Cassure de structure haussière : clôture "
                            f"{margin * 100:.2f} % au-dessus du dernier sommet "
                            f"pivot ({level:.2f})."
                        ),
                    )
                )
            elif candle.high > level and candle.close < level:
                detections.append(
                    SmcDetection(
                        kind="liquidity_sweep",
                        index=i,
                        direction="bearish",
                        confidence=0.6,
                        explanation=(
                            f"Prise de liquidité : mèche au-dessus du sommet "
                            f"pivot ({level:.2f}) puis clôture en dessous — "
                            "chasse aux stops probable."
                        ),
                    )
                )

        if last_low is not None:
            level = candles[last_low].low
            if candle.close < level:
                margin = (level - candle.close) / level
                detections.append(
                    SmcDetection(
                        kind="break_of_structure",
                        index=i,
                        direction="bearish",
                        confidence=round(min(0.5 + margin * 50, 0.9), 2),
                        explanation=(
                            f"Cassure de structure baissière : clôture "
                            f"{margin * 100:.2f} % sous le dernier creux pivot "
                            f"({level:.2f})."
                        ),
                    )
                )
            elif candle.low < level and candle.close > level:
                detections.append(
                    SmcDetection(
                        kind="liquidity_sweep",
                        index=i,
                        direction="bullish",
                        confidence=0.6,
                        explanation=(
                            f"Prise de liquidité : mèche sous le creux pivot "
                            f"({level:.2f}) puis clôture au-dessus — chasse aux "
                            "stops probable."
                        ),
                    )
                )

    # Keep only the last detection per (kind, direction, index) burst to
    # avoid duplicates on consecutive candles beyond the same level.
    deduped: list[SmcDetection] = []
    for detection in detections:
        if deduped and (
            deduped[-1].kind == detection.kind
            and deduped[-1].direction == detection.direction
            and detection.index - deduped[-1].index <= 1
        ):
            deduped[-1] = detection
        else:
            deduped.append(detection)
    return deduped
