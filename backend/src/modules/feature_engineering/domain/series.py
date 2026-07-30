"""Pure series primitives shared by technical analysis and (later) ML
feature construction. Inputs/outputs are plain float lists aligned on the
input index; leading positions without enough history are None.
"""

import math


def returns(values: list[float]) -> list[float | None]:
    return [None] + [
        (values[i] - values[i - 1]) / values[i - 1] if values[i - 1] else None
        for i in range(1, len(values))
    ]


def log_returns(values: list[float]) -> list[float | None]:
    result: list[float | None] = [None]
    for i in range(1, len(values)):
        previous, current = values[i - 1], values[i]
        result.append(
            math.log(current / previous) if previous > 0 and current > 0 else None
        )
    return result


def rolling_mean(values: list[float], window: int) -> list[float | None]:
    result: list[float | None] = []
    window_sum = 0.0
    for i, value in enumerate(values):
        window_sum += value
        if i >= window:
            window_sum -= values[i - window]
        result.append(window_sum / window if i >= window - 1 else None)
    return result


def rolling_std(values: list[float], window: int) -> list[float | None]:
    result: list[float | None] = []
    for i in range(len(values)):
        if i < window - 1:
            result.append(None)
            continue
        chunk = values[i - window + 1 : i + 1]
        mean = sum(chunk) / window
        result.append(math.sqrt(sum((v - mean) ** 2 for v in chunk) / window))
    return result


def rolling_max(values: list[float], window: int) -> list[float | None]:
    return [
        max(values[i - window + 1 : i + 1]) if i >= window - 1 else None
        for i in range(len(values))
    ]


def rolling_min(values: list[float], window: int) -> list[float | None]:
    return [
        min(values[i - window + 1 : i + 1]) if i >= window - 1 else None
        for i in range(len(values))
    ]


def zscore(value: float, mean: float | None, std: float | None) -> float | None:
    """Simple z-score against an already-known mean/std (e.g. from
    `rolling_mean`/`rolling_std` series) — 0.0 when std is zero rather than
    dividing by it."""
    if mean is None or std is None:
        return None
    return (value - mean) / std if std > 0 else 0.0


def windowed_zscore(
    current: float | None, history: list[float | None], min_samples: int = 10
) -> float | None:
    """Z-score of `current` against the last values of `history` (`None`
    entries filtered out first). `None` if there isn't enough history yet or
    `current` itself is undefined — callers decide their own default (some
    treat "not enough signal yet" as 0.0, others want to keep it `None`)."""
    if current is None:
        return None
    valid = [v for v in history if v is not None]
    if len(valid) < min_samples:
        return None
    mean = sum(valid) / len(valid)
    std = (sum((v - mean) ** 2 for v in valid) / len(valid)) ** 0.5
    return zscore(current, mean, std)


def efficiency_ratio(closes: list[float], window: int) -> float | None:
    """Kaufman's Efficiency Ratio: net displacement over total path length
    across the last `window` candles. Near 1 = an efficient, strongly
    trending move; near 0 = a choppy, range-bound market (lots of
    back-and-forth for little net progress). `None` if there isn't enough
    history yet."""
    if len(closes) <= window:
        return None
    segment = closes[-(window + 1):]
    net = abs(segment[-1] - segment[0])
    path = sum(abs(segment[i] - segment[i - 1]) for i in range(1, len(segment)))
    return net / path if path > 0 else 0.0


def rolling_efficiency_ratio(closes: list[float], window: int) -> list[float | None]:
    """`efficiency_ratio` evaluated at every index (aligned like the other
    `rolling_*` series here), for building a per-row ML feature rather than
    just a single latest-value snapshot."""
    return [
        efficiency_ratio(closes[: i + 1], window) if i >= window else None
        for i in range(len(closes))
    ]


def ema(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = []
    multiplier = 2 / (period + 1)
    previous: float | None = None
    for i, value in enumerate(values):
        if i < period - 1:
            result.append(None)
        elif previous is None:
            previous = sum(values[: period]) / period
            result.append(previous)
        else:
            previous = (value - previous) * multiplier + previous
            result.append(previous)
    return result
