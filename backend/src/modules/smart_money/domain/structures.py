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


def detect_fair_value_gap(candles: list[SmcCandle]) -> list[SmcDetection]:
    """A Fair Value Gap is a 3-candle imbalance: the middle candle moves so
    fast that candles on either side don't overlap, leaving a price range
    that traded no volume. Price often revisits ("fills") this gap before
    continuing — a widely-used SMC entry zone."""
    detections: list[SmcDetection] = []
    for i in range(2, len(candles)):
        first, last = candles[i - 2], candles[i]

        if last.low > first.high:
            gap_pct = (last.low - first.high) / first.high if first.high else 0.0
            detections.append(
                SmcDetection(
                    kind="fair_value_gap",
                    index=i,
                    direction="bullish",
                    confidence=round(min(0.5 + gap_pct * 50, 0.9), 2),
                    explanation=(
                        f"Fair Value Gap haussier : aucun échange n'a eu lieu "
                        f"entre {first.high:.2f} et {last.low:.2f} — cette zone "
                        "de déséquilibre est souvent revisitée avant la "
                        "poursuite de la tendance."
                    ),
                )
            )
        elif last.high < first.low:
            gap_pct = (first.low - last.high) / first.low if first.low else 0.0
            detections.append(
                SmcDetection(
                    kind="fair_value_gap",
                    index=i,
                    direction="bearish",
                    confidence=round(min(0.5 + gap_pct * 50, 0.9), 2),
                    explanation=(
                        f"Fair Value Gap baissier : aucun échange n'a eu lieu "
                        f"entre {last.high:.2f} et {first.low:.2f} — cette zone "
                        "de déséquilibre est souvent revisitée avant la "
                        "poursuite de la tendance."
                    ),
                )
            )
    return detections


def detect_order_block(candles: list[SmcCandle], lookback: int = 2) -> list[SmcDetection]:
    """An Order Block is the last opposite-colored candle right before an
    impulsive move that breaks market structure — read as the footprint of
    the large order that triggered the move, and a zone price often retests
    before continuing (same swing-point/break-of-structure basis as
    `detect_structures`)."""
    highs = swing_highs(candles, lookback)
    lows = swing_lows(candles, lookback)
    detections: list[SmcDetection] = []

    for i in range(2, len(candles)):
        last_high = next((h for h in reversed(highs) if h < i - 2), None)
        last_low = next((l for l in reversed(lows) if l < i - 2), None)
        candle = candles[i]

        if last_high is not None and candle.close > candles[last_high].high:
            ob_index = next(
                (j for j in range(i - 1, -1, -1) if candles[j].close < candles[j].open),
                None,
            )
            if ob_index is not None:
                ob = candles[ob_index]
                detections.append(
                    SmcDetection(
                        kind="order_block",
                        index=ob_index,
                        direction="bullish",
                        confidence=0.65,
                        explanation=(
                            f"Order Block haussier : dernière bougie baissière "
                            f"({ob.open:.2f} → {ob.close:.2f}) avant une cassure "
                            "de structure haussière — zone institutionnelle "
                            "probable, souvent retestée avant continuation."
                        ),
                    )
                )

        if last_low is not None and candle.close < candles[last_low].low:
            ob_index = next(
                (j for j in range(i - 1, -1, -1) if candles[j].close > candles[j].open),
                None,
            )
            if ob_index is not None:
                ob = candles[ob_index]
                detections.append(
                    SmcDetection(
                        kind="order_block",
                        index=ob_index,
                        direction="bearish",
                        confidence=0.65,
                        explanation=(
                            f"Order Block baissier : dernière bougie haussière "
                            f"({ob.open:.2f} → {ob.close:.2f}) avant une cassure "
                            "de structure baissière — zone institutionnelle "
                            "probable, souvent retestée avant continuation."
                        ),
                    )
                )

    # An order block's index doesn't advance with the triggering candle (it
    # stays pinned to the impulsive candle that created it), so later closes
    # past the same pivot would otherwise re-report it — dedupe by identity.
    seen: set[tuple[str, str, int]] = set()
    deduped: list[SmcDetection] = []
    for detection in detections:
        key = (detection.kind, detection.direction, detection.index)
        if key not in seen:
            seen.add(key)
            deduped.append(detection)
    return deduped
