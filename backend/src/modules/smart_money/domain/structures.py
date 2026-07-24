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


def detect_structures(
    candles: list[SmcCandle], lookback: int = 2, scale: str = ""
) -> list[SmcDetection]:
    """`scale` prefixes the emitted kind (e.g. "internal_break_of_structure")
    when set, letting the same swing/break-of-structure mechanics run at a
    different granularity (docs/roadmap #14 — Internal vs External
    Structure) without touching the unscaled default's existing kind
    strings ("break_of_structure"/"liquidity_sweep"), which the frontend
    and existing tests already depend on."""
    kind_bos = f"{scale}_break_of_structure" if scale else "break_of_structure"
    kind_sweep = f"{scale}_liquidity_sweep" if scale else "liquidity_sweep"
    highs = swing_highs(candles, lookback)
    lows = swing_lows(candles, lookback)
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
                        kind=kind_bos,
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
                        kind=kind_sweep,
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
                        kind=kind_bos,
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
                        kind=kind_sweep,
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


def detect_breaker_blocks(candles: list[SmcCandle], lookback: int = 2) -> list[SmcDetection]:
    """A Breaker Block (docs/roadmap #14) is a former Order Block that
    failed: price later closes back through its far boundary, invalidating
    it as a continuation zone and flipping it into a reversal zone in the
    opposite direction."""
    detections: list[SmcDetection] = []
    for ob in detect_order_block(candles, lookback):
        ob_candle = candles[ob.index]
        if ob.direction == "bullish":
            boundary = ob_candle.low
            invalidation_index = next(
                (j for j in range(ob.index + 1, len(candles)) if candles[j].close < boundary),
                None,
            )
            if invalidation_index is not None:
                detections.append(
                    SmcDetection(
                        kind="breaker_block",
                        index=invalidation_index,
                        direction="bearish",
                        confidence=0.6,
                        explanation=(
                            f"Breaker Block baissier : l'Order Block haussier "
                            f"({boundary:.2f}) a été invalidé par une clôture en "
                            "dessous — la zone devient une résistance attendue "
                            "plutôt qu'un support."
                        ),
                    )
                )
        else:
            boundary = ob_candle.high
            invalidation_index = next(
                (j for j in range(ob.index + 1, len(candles)) if candles[j].close > boundary),
                None,
            )
            if invalidation_index is not None:
                detections.append(
                    SmcDetection(
                        kind="breaker_block",
                        index=invalidation_index,
                        direction="bullish",
                        confidence=0.6,
                        explanation=(
                            f"Breaker Block haussier : l'Order Block baissier "
                            f"({boundary:.2f}) a été invalidé par une clôture "
                            "au-dessus — la zone devient un support attendu "
                            "plutôt qu'une résistance."
                        ),
                    )
                )
    return detections


def detect_mitigation_blocks(candles: list[SmcCandle], lookback: int = 2) -> list[SmcDetection]:
    """A Mitigation Block (docs/roadmap #14) is the last opposite-colored
    candle before a swing point that reverses WITHOUT breaking market
    structure — weaker than an Order Block (which precedes an actual break
    of structure), so any swing point already claimed by an Order Block is
    excluded here rather than double-counted."""
    order_block_indices = {d.index for d in detect_order_block(candles, lookback)}
    highs = swing_highs(candles, lookback)
    lows = swing_lows(candles, lookback)
    detections: list[SmcDetection] = []

    for h in highs:
        mb_index = next(
            (j for j in range(h - 1, -1, -1) if candles[j].close > candles[j].open), None
        )
        if mb_index is not None and mb_index not in order_block_indices:
            mb = candles[mb_index]
            detections.append(
                SmcDetection(
                    kind="mitigation_block",
                    index=mb_index,
                    direction="bearish",
                    confidence=0.5,
                    explanation=(
                        f"Mitigation Block baissier : dernière bougie haussière "
                        f"({mb.open:.2f} → {mb.close:.2f}) avant un sommet pivot "
                        "sans cassure de structure — zone plus faible qu'un Order "
                        "Block, susceptible d'être retestée pour « mitiger » les "
                        "ordres restants."
                    ),
                )
            )

    for l in lows:
        mb_index = next(
            (j for j in range(l - 1, -1, -1) if candles[j].close < candles[j].open), None
        )
        if mb_index is not None and mb_index not in order_block_indices:
            mb = candles[mb_index]
            detections.append(
                SmcDetection(
                    kind="mitigation_block",
                    index=mb_index,
                    direction="bullish",
                    confidence=0.5,
                    explanation=(
                        f"Mitigation Block haussier : dernière bougie baissière "
                        f"({mb.open:.2f} → {mb.close:.2f}) avant un creux pivot "
                        "sans cassure de structure — zone plus faible qu'un Order "
                        "Block, susceptible d'être retestée pour « mitiger » les "
                        "ordres restants."
                    ),
                )
            )

    seen: set[tuple[str, str, int]] = set()
    deduped: list[SmcDetection] = []
    for detection in detections:
        key = (detection.kind, detection.direction, detection.index)
        if key not in seen:
            seen.add(key)
            deduped.append(detection)
    return deduped


_LIQUIDITY_POOL_TOLERANCE = 0.001


def detect_liquidity_pools(candles: list[SmcCandle], lookback: int = 2) -> list[SmcDetection]:
    """A Liquidity Pool (docs/roadmap #14) is a cluster of near-equal swing
    highs (buy-side liquidity — breakout/stop orders resting above) or
    near-equal swing lows (sell-side liquidity below): price is often
    drawn to these levels to trigger the resting orders before reversing."""
    highs = swing_highs(candles, lookback)
    lows = swing_lows(candles, lookback)
    detections: list[SmcDetection] = []

    for a, b in zip(highs, highs[1:]):
        level_a, level_b = candles[a].high, candles[b].high
        if level_a and abs(level_a - level_b) / level_a <= _LIQUIDITY_POOL_TOLERANCE:
            detections.append(
                SmcDetection(
                    kind="liquidity_pool",
                    index=b,
                    direction="bearish",
                    confidence=0.55,
                    explanation=(
                        f"Pool de liquidité (côté acheteur) : sommets égaux autour "
                        f"de {level_a:.2f} — ordres stop probablement regroupés "
                        "au-dessus, cible fréquente d'une chasse à la liquidité."
                    ),
                )
            )

    for a, b in zip(lows, lows[1:]):
        level_a, level_b = candles[a].low, candles[b].low
        if level_a and abs(level_a - level_b) / level_a <= _LIQUIDITY_POOL_TOLERANCE:
            detections.append(
                SmcDetection(
                    kind="liquidity_pool",
                    index=b,
                    direction="bullish",
                    confidence=0.55,
                    explanation=(
                        f"Pool de liquidité (côté vendeur) : creux égaux autour de "
                        f"{level_a:.2f} — ordres stop probablement regroupés en "
                        "dessous, cible fréquente d'une chasse à la liquidité."
                    ),
                )
            )
    return detections


_PREMIUM_DISCOUNT_WINDOW = 20


def detect_premium_discount_zone(
    candles: list[SmcCandle], window: int = _PREMIUM_DISCOUNT_WINDOW
) -> list[SmcDetection]:
    """Splits the most recent swing range into a Premium zone (upper half —
    SMC convention favors looking for shorts here) and a Discount zone
    (lower half — favors longs), relative to the range's 50 % equilibrium
    (docs/roadmap #14). Reports only the current candle's zone, not a
    historical series — this is a standing context, not a discrete event."""
    if len(candles) < window:
        return []
    recent = candles[-window:]
    range_high = max(c.high for c in recent)
    range_low = min(c.low for c in recent)
    if range_high == range_low:
        return []

    equilibrium = (range_high + range_low) / 2
    current = candles[-1].close
    position_pct = (current - range_low) / (range_high - range_low)
    index = len(candles) - 1

    if current >= equilibrium:
        return [
            SmcDetection(
                kind="premium_zone",
                index=index,
                direction="bearish",
                confidence=round(min(0.4 + (position_pct - 0.5) * 0.8, 0.85), 2),
                explanation=(
                    f"Zone Premium : prix actuel ({current:.2f}) au-dessus de "
                    f"l'équilibre ({equilibrium:.2f}) du range récent "
                    f"[{range_low:.2f}, {range_high:.2f}] — recherche de vente "
                    "privilégiée en théorie SMC."
                ),
            )
        ]
    return [
        SmcDetection(
            kind="discount_zone",
            index=index,
            direction="bullish",
            confidence=round(min(0.4 + (0.5 - position_pct) * 0.8, 0.85), 2),
            explanation=(
                f"Zone Discount : prix actuel ({current:.2f}) sous l'équilibre "
                f"({equilibrium:.2f}) du range récent [{range_low:.2f}, "
                f"{range_high:.2f}] — recherche d'achat privilégiée en théorie SMC."
            ),
        )
    ]


_MIN_IMBALANCE_PCT = 0.0005


def detect_volume_imbalance(candles: list[SmcCandle]) -> list[SmcDetection]:
    """A Volume Imbalance (docs/roadmap #14) is a body-to-body gap between
    consecutive candles (this candle's open vs. the prior candle's close) —
    distinct from a Fair Value Gap, which is a 3-candle high/low imbalance.
    One side traded through a price level so fast the opening auction
    never met the prior close, leaving a thinner-traded pocket that's
    often refilled."""
    detections: list[SmcDetection] = []
    for i in range(1, len(candles)):
        prev, curr = candles[i - 1], candles[i]
        if not prev.close:
            continue
        gap_pct = (curr.open - prev.close) / prev.close
        if gap_pct > _MIN_IMBALANCE_PCT:
            detections.append(
                SmcDetection(
                    kind="volume_imbalance",
                    index=i,
                    direction="bullish",
                    confidence=round(min(0.4 + gap_pct * 50, 0.8), 2),
                    explanation=(
                        f"Volume Imbalance haussier : ouverture ({curr.open:.2f}) "
                        f"au-dessus de la clôture précédente ({prev.close:.2f}) — "
                        "zone à volume plus faible, souvent comblée."
                    ),
                )
            )
        elif gap_pct < -_MIN_IMBALANCE_PCT:
            detections.append(
                SmcDetection(
                    kind="volume_imbalance",
                    index=i,
                    direction="bearish",
                    confidence=round(min(0.4 + abs(gap_pct) * 50, 0.8), 2),
                    explanation=(
                        f"Volume Imbalance baissier : ouverture ({curr.open:.2f}) "
                        f"en dessous de la clôture précédente ({prev.close:.2f}) — "
                        "zone à volume plus faible, souvent comblée."
                    ),
                )
            )
    return detections
