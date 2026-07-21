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
