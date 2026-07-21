"""Technical indicators as pure functions over close/high/low series.
Values are aligned on the input index; positions without enough history
are None.
"""

from src.modules.feature_engineering.application import service as features


def sma(closes: list[float], period: int) -> list[float | None]:
    return features.rolling_mean(closes, period)


def ema(closes: list[float], period: int) -> list[float | None]:
    return features.ema(closes, period)


def rsi(closes: list[float], period: int = 14) -> list[float | None]:
    if len(closes) < 2:
        return [None] * len(closes)

    gains: list[float] = [0.0]
    losses: list[float] = [0.0]
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    result: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return result

    avg_gain = sum(gains[1 : period + 1]) / period
    avg_loss = sum(losses[1 : period + 1]) / period
    for i in range(period, len(closes)):
        if i > period:
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result[i] = 100.0
        else:
            result[i] = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return result


def macd(
    closes: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, list[float | None]]:
    fast_ema = features.ema(closes, fast)
    slow_ema = features.ema(closes, slow)
    macd_line: list[float | None] = [
        f - s if f is not None and s is not None else None
        for f, s in zip(fast_ema, slow_ema)
    ]

    known = [v for v in macd_line if v is not None]
    signal_known = features.ema(known, signal)
    signal_line: list[float | None] = []
    known_index = 0
    for value in macd_line:
        if value is None:
            signal_line.append(None)
        else:
            signal_line.append(signal_known[known_index])
            known_index += 1

    histogram = [
        m - s if m is not None and s is not None else None
        for m, s in zip(macd_line, signal_line)
    ]
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def bollinger(
    closes: list[float], period: int = 20, num_std: float = 2.0
) -> dict[str, list[float | None]]:
    middle = features.rolling_mean(closes, period)
    std = features.rolling_std(closes, period)
    upper = [
        m + num_std * s if m is not None and s is not None else None
        for m, s in zip(middle, std)
    ]
    lower = [
        m - num_std * s if m is not None and s is not None else None
        for m, s in zip(middle, std)
    ]
    return {"middle": middle, "upper": upper, "lower": lower}
