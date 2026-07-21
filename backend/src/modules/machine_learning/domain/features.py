"""Feature matrix construction for direction models. Pure logic on float
series (uses the feature_engineering public facade). Row i describes candle
i; the label is the direction of candle i+1.
"""

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
]


def build_features(
    closes: list[float], volumes: list[float]
) -> tuple[list[list[float]], list[int], list[float] | None]:
    """Returns (rows, labels, latest_row). Rows only include indices where
    every feature and the label are defined; latest_row is the most recent
    fully-defined feature vector (whose label is still unknown)."""
    from src.modules.technical_analysis.application import service as ta

    returns_1 = fe.returns(closes)
    sma20 = fe.rolling_mean(closes, 20)
    sma50 = fe.rolling_mean(closes, 50)
    vol20 = fe.rolling_std([r for r in _fill(returns_1)], 20)
    rsi14 = ta.rsi(closes, 14)
    vol_mean = fe.rolling_mean(volumes, 20)
    vol_std = fe.rolling_std(volumes, 20)

    def row(i: int) -> list[float] | None:
        needed = [
            _lag_return(closes, i, 1),
            _lag_return(closes, i, 3),
            _lag_return(closes, i, 6),
            vol20[i],
            rsi14[i],
            _distance(closes[i], sma20[i]),
            _distance(closes[i], sma50[i]),
            _zscore(volumes[i], vol_mean[i], vol_std[i]),
        ]
        return None if any(v is None for v in needed) else [float(v) for v in needed]

    rows: list[list[float]] = []
    labels: list[int] = []
    for i in range(len(closes) - 1):
        features = row(i)
        if features is None:
            continue
        rows.append(features)
        labels.append(1 if closes[i + 1] > closes[i] else 0)

    latest = row(len(closes) - 1)
    return rows, labels, latest


def _fill(values: list[float | None]) -> list[float]:
    return [0.0 if v is None else v for v in values]


def _lag_return(closes: list[float], i: int, lag: int) -> float | None:
    if i - lag < 0 or closes[i - lag] == 0:
        return None
    return closes[i] / closes[i - lag] - 1.0


def _distance(price: float, sma: float | None) -> float | None:
    if sma is None or sma == 0:
        return None
    return price / sma - 1.0


def _zscore(
    value: float, mean: float | None, std: float | None
) -> float | None:
    if mean is None or std is None:
        return None
    return (value - mean) / std if std > 0 else 0.0
