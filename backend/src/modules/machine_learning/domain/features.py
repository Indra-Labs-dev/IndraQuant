"""Feature matrix construction for direction and price-target models. Pure
logic on float series (uses the feature_engineering public facade). Row i
describes candle i; the label/return describes the move from candle i to
candle i+1.
"""

import math

from src.modules.feature_engineering.application import service as fe

FEATURE_NAMES = [
    "return_1",
    "return_3",
    "return_6",
    "volatility_20",
    "rsi_14",
    "dist_sma_20",
    "dist_sma_50",
    "volume_zscore_20",
    "macd_histogram",
    "bollinger_position",
    "volatility_zscore_90",
    "efficiency_ratio_20",
    "correlation_btc_20",
]

# Moves smaller than this (in absolute return) are noise for most timeframes —
# spread/fees alone can flip their sign, so a hard binary "up"/"down" label on
# them teaches the model to fit coin-flip micro-noise rather than real
# direction. Rows inside the dead zone are excluded from training entirely
# (not given a third "neutral" class, which would turn this into a 3-class
# problem the rest of the pipeline — calibration, track record — isn't built
# for) (see 2026-07-29 model-validation diagnostic: naive split ~50-53% on
# every timeframe, cross-validated accuracy consistently ~48-52%, i.e. no
# edge above chance once you stop rewarding lucky single splits).
_LABEL_DEAD_ZONE = 0.0005

_ER_WINDOW = 20
_VOL_HISTORY = 90
# When no same-asset-class reference series is available (equities, or BTC/USDT
# itself), the correlation feature is filled with this neutral value rather
# than dropping the row/column — 0.0 reads as "no relationship known", not "no
# correlation observed", but it keeps the feature matrix rectangular without a
# second code path in the model itself.
_CORRELATION_NEUTRAL = 0.0


def build_features(
    closes: list[float],
    volumes: list[float],
    reference_closes: list[float] | None = None,
) -> tuple[list[list[float]], list[int], list[float], list[float] | None]:
    """Returns (rows, labels, log_returns, latest_row). Rows only include
    indices where every feature and the label are defined; `log_returns[i]`
    is the log-return from candle i to i+1 (regression target for price
    targets); `latest_row` is the most recent fully-defined feature vector
    (whose outcome is still unknown).

    `reference_closes` is an optional same-length-ish close series from a
    correlated reference instrument (e.g. BTC/USDT for other crypto pairs) —
    when given, its rolling correlation with `closes`' own returns becomes
    the `correlation_btc_20` feature; when omitted (equities, or the
    reference instrument itself), that feature is filled with a neutral
    constant (see `_CORRELATION_NEUTRAL`)."""
    from src.modules.technical_analysis.application import service as ta

    returns_1 = fe.returns(closes)
    sma20 = fe.rolling_mean(closes, 20)
    sma50 = fe.rolling_mean(closes, 50)
    # Only real, known returns feed the volatility window — a None (start of
    # series) used to be zero-filled here, which silently deflated volatility
    # right after the series start instead of just leaving it undefined like
    # every other feature does.
    known_returns = [r for r in returns_1 if r is not None]
    vol20_known = fe.rolling_std(known_returns, 20)
    vol20: list[float | None] = [None] * (len(returns_1) - len(known_returns)) + vol20_known
    rsi14 = ta.rsi(closes, 14)
    vol_mean = fe.rolling_mean(volumes, 20)
    vol_std = fe.rolling_std(volumes, 20)
    histogram = ta.macd(closes)["histogram"]
    bands = ta.bollinger(closes, 20, 2.0)
    er20 = fe.rolling_efficiency_ratio(closes, _ER_WINDOW)

    reference_returns: list[float | None] | None = (
        fe.returns(reference_closes) if reference_closes else None
    )
    correlation_20: list[float | None] | None = None
    if reference_returns is not None and len(reference_returns) == len(returns_1):
        from src.modules.correlation_engine.domain.correlation import rolling_correlation

        filled_returns = [r if r is not None else 0.0 for r in returns_1]
        filled_reference = [r if r is not None else 0.0 for r in reference_returns]
        correlation_20 = rolling_correlation(filled_returns, filled_reference, 20)

    def row(i: int) -> list[float] | None:
        needed = [
            _lag_return(closes, i, 1),
            _lag_return(closes, i, 3),
            _lag_return(closes, i, 6),
            vol20[i],
            rsi14[i],
            _distance(closes[i], sma20[i]),
            _distance(closes[i], sma50[i]),
            fe.zscore(volumes[i], vol_mean[i], vol_std[i]),
            histogram[i],
            _bollinger_position(closes[i], bands["upper"][i], bands["lower"][i]),
            fe.windowed_zscore(vol20[i], vol20[max(0, i - _VOL_HISTORY) : i]),
            er20[i],
        ]
        if any(v is None for v in needed):
            return None
        correlation = (
            correlation_20[i]
            if correlation_20 is not None and correlation_20[i] is not None
            else _CORRELATION_NEUTRAL
        )
        return [float(v) for v in needed] + [float(correlation)]

    rows: list[list[float]] = []
    labels: list[int] = []
    log_returns: list[float] = []
    for i in range(len(closes) - 1):
        features = row(i)
        if features is None:
            continue
        move = closes[i + 1] / closes[i] - 1.0 if closes[i] > 0 else 0.0
        if abs(move) < _LABEL_DEAD_ZONE:
            continue
        rows.append(features)
        labels.append(1 if move > 0 else 0)
        log_returns.append(
            math.log(closes[i + 1] / closes[i])
            if closes[i] > 0 and closes[i + 1] > 0
            else 0.0
        )

    latest = row(len(closes) - 1)
    return rows, labels, log_returns, latest


def _lag_return(closes: list[float], i: int, lag: int) -> float | None:
    if i - lag < 0 or closes[i - lag] == 0:
        return None
    return closes[i] / closes[i - lag] - 1.0


def _distance(price: float, sma: float | None) -> float | None:
    if sma is None or sma == 0:
        return None
    return price / sma - 1.0


def _bollinger_position(
    price: float, upper: float | None, lower: float | None
) -> float | None:
    """0.0 at the lower band, 1.0 at the upper band — can go outside [0, 1]
    when price pierces a band, which is itself informative (breakout)."""
    if upper is None or lower is None or upper == lower:
        return None
    return (price - lower) / (upper - lower)
