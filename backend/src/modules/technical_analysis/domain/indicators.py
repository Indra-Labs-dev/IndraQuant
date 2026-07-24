"""Technical indicators as pure functions over close/high/low/volume
series (docs/roadmap #11 for the advanced set). Values are aligned on the
input index; positions without enough history are None.
"""

import math
from dataclasses import dataclass

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


# ---------------------------------------------------------------------------
# Advanced Feature Engineering (docs/roadmap #11): indicators that need the
# full OHLCV series (high/low/close/volume), not just closes.
# ---------------------------------------------------------------------------


def vwap(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
    window: int = 20,
) -> list[float | None]:
    """Volume Weighted Average Price over a rolling window — the ratio of
    two rolling sums (rolling means with the same divisor, which cancels)."""
    typical = [(h + l + c) / 3.0 for h, l, c in zip(highs, lows, closes)]
    price_volume = [tp * v for tp, v in zip(typical, volumes)]
    pv_avg = features.rolling_mean(price_volume, window)
    vol_avg = features.rolling_mean(volumes, window)
    return [
        (pv / vol) if pv is not None and vol not in (None, 0) else None
        for pv, vol in zip(pv_avg, vol_avg)
    ]


def true_range(
    highs: list[float], lows: list[float], closes: list[float]
) -> list[float | None]:
    n = len(closes)
    if n == 0:
        return []
    result: list[float | None] = [highs[0] - lows[0]]
    for i in range(1, n):
        result.append(
            max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
        )
    return result


def atr(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> list[float | None]:
    """Average True Range, Wilder-smoothed (same smoothing style as `rsi`)."""
    tr = true_range(highs, lows, closes)
    n = len(tr)
    result: list[float | None] = [None] * n
    if n <= period:
        return result

    avg = sum(tr[:period]) / period
    result[period - 1] = avg
    for i in range(period, n):
        avg = (avg * (period - 1) + tr[i]) / period
        result[i] = avg
    return result


def adx(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> list[float | None]:
    """Average Directional Index (Wilder): trend *strength*, regardless of
    direction — high ADX means a strong trend (up or down), low ADX means
    a range-bound market."""
    n = len(closes)
    result: list[float | None] = [None] * n
    if n <= period * 2:
        return result

    plus_dm = [0.0] * n
    minus_dm = [0.0] * n
    for i in range(1, n):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        plus_dm[i] = up_move if (up_move > down_move and up_move > 0) else 0.0
        minus_dm[i] = down_move if (down_move > up_move and down_move > 0) else 0.0

    tr = true_range(highs, lows, closes)
    tr_smooth = sum(tr[1 : period + 1])
    plus_smooth = sum(plus_dm[1 : period + 1])
    minus_smooth = sum(minus_dm[1 : period + 1])

    dx_values: list[tuple[int, float]] = []
    for i in range(period + 1, n):
        tr_smooth = tr_smooth - (tr_smooth / period) + tr[i]
        plus_smooth = plus_smooth - (plus_smooth / period) + plus_dm[i]
        minus_smooth = minus_smooth - (minus_smooth / period) + minus_dm[i]
        plus_di = 100.0 * plus_smooth / tr_smooth if tr_smooth else 0.0
        minus_di = 100.0 * minus_smooth / tr_smooth if tr_smooth else 0.0
        denom = plus_di + minus_di
        dx = 100.0 * abs(plus_di - minus_di) / denom if denom else 0.0
        dx_values.append((i, dx))

    if len(dx_values) < period:
        return result

    seed = sum(v for _, v in dx_values[:period]) / period
    seed_index = dx_values[period - 1][0]
    result[seed_index] = seed
    running = seed
    for j in range(period, len(dx_values)):
        idx, dx = dx_values[j]
        running = (running * (period - 1) + dx) / period
        result[idx] = running
    return result


def donchian(
    highs: list[float], lows: list[float], period: int = 20
) -> dict[str, list[float | None]]:
    upper = features.rolling_max(highs, period)
    lower = features.rolling_min(lows, period)
    middle = [
        (u + l) / 2.0 if u is not None and l is not None else None
        for u, l in zip(upper, lower)
    ]
    return {"upper": upper, "middle": middle, "lower": lower}


def keltner(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 20,
    multiplier: float = 2.0,
) -> dict[str, list[float | None]]:
    middle = features.ema(closes, period)
    atr_values = atr(highs, lows, closes, period)
    upper = [
        m + multiplier * a if m is not None and a is not None else None
        for m, a in zip(middle, atr_values)
    ]
    lower = [
        m - multiplier * a if m is not None and a is not None else None
        for m, a in zip(middle, atr_values)
    ]
    return {"middle": middle, "upper": upper, "lower": lower}


def obv(closes: list[float], volumes: list[float]) -> list[float]:
    """On-Balance Volume: cumulative volume, added when price rises,
    subtracted when it falls — always defined (no warm-up period)."""
    n = len(closes)
    result: list[float] = [0.0] * n
    for i in range(1, n):
        if closes[i] > closes[i - 1]:
            result[i] = result[i - 1] + volumes[i]
        elif closes[i] < closes[i - 1]:
            result[i] = result[i - 1] - volumes[i]
        else:
            result[i] = result[i - 1]
    return result


def mfi(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
    period: int = 14,
) -> list[float | None]:
    """Money Flow Index: RSI's volume-weighted cousin."""
    n = len(closes)
    typical = [(h + l + c) / 3.0 for h, l, c in zip(highs, lows, closes)]
    raw_flow = [tp * v for tp, v in zip(typical, volumes)]
    result: list[float | None] = [None] * n
    for i in range(period, n):
        positive = 0.0
        negative = 0.0
        for j in range(i - period + 1, i + 1):
            if typical[j] > typical[j - 1]:
                positive += raw_flow[j]
            elif typical[j] < typical[j - 1]:
                negative += raw_flow[j]
        result[i] = (
            100.0 if negative == 0 else 100.0 - 100.0 / (1.0 + positive / negative)
        )
    return result


def cci(
    highs: list[float], lows: list[float], closes: list[float], period: int = 20
) -> list[float | None]:
    """Commodity Channel Index: how far the typical price sits from its
    moving average, scaled by the average absolute deviation."""
    typical = [(h + l + c) / 3.0 for h, l, c in zip(highs, lows, closes)]
    sma_tp = features.rolling_mean(typical, period)
    n = len(closes)
    result: list[float | None] = [None] * n
    for i in range(period - 1, n):
        center = sma_tp[i]
        if center is None:
            continue
        window = typical[i - period + 1 : i + 1]
        mean_deviation = sum(abs(tp - center) for tp in window) / period
        result[i] = (
            (typical[i] - center) / (0.015 * mean_deviation) if mean_deviation > 0 else 0.0
        )
    return result


def williams_r(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> list[float | None]:
    highest = features.rolling_max(highs, period)
    lowest = features.rolling_min(lows, period)
    n = len(closes)
    result: list[float | None] = [None] * n
    for i in range(n):
        high_val, low_val = highest[i], lowest[i]
        if high_val is None or low_val is None:
            continue
        rng = high_val - low_val
        result[i] = -100.0 * (high_val - closes[i]) / rng if rng > 0 else 0.0
    return result


def chaikin_money_flow(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
    period: int = 20,
) -> list[float | None]:
    money_flow_volume = []
    for h, l, c, v in zip(highs, lows, closes, volumes):
        rng = h - l
        multiplier = ((c - l) - (h - c)) / rng if rng > 0 else 0.0
        money_flow_volume.append(multiplier * v)

    mfv_avg = features.rolling_mean(money_flow_volume, period)
    vol_avg = features.rolling_mean(volumes, period)
    return [
        (mv / vol) if mv is not None and vol not in (None, 0) else None
        for mv, vol in zip(mfv_avg, vol_avg)
    ]


def ulcer_index(closes: list[float], period: int = 14) -> list[float | None]:
    """Ulcer Index: root-mean-square of percentage drawdowns from the
    rolling peak — penalizes depth *and* duration of drawdowns, unlike
    plain volatility which treats up and down moves symmetrically."""
    n = len(closes)
    result: list[float | None] = [None] * n
    for i in range(period - 1, n):
        window = closes[i - period + 1 : i + 1]
        peak = window[0]
        squared_drawdowns = []
        for price in window:
            peak = max(peak, price)
            drawdown_pct = 100.0 * (price - peak) / peak if peak > 0 else 0.0
            squared_drawdowns.append(drawdown_pct**2)
        result[i] = math.sqrt(sum(squared_drawdowns) / period)
    return result


def momentum(closes: list[float], period: int = 10) -> list[float | None]:
    return [
        closes[i] - closes[i - period] if i >= period else None
        for i in range(len(closes))
    ]


def order_flow_proxy(
    highs: list[float], lows: list[float], closes: list[float], volumes: list[float]
) -> list[float]:
    """Order Flow Proxy: without real order-book data, infers net buy vs
    sell pressure from where the candle closed within its own range — a
    close near the high implies most volume traded as aggressive buying,
    a close near the low implies aggressive selling. Always defined."""
    result = []
    for h, l, c, v in zip(highs, lows, closes, volumes):
        rng = h - l
        buy_fraction = (c - l) / rng if rng > 0 else 0.5
        buy_volume = v * buy_fraction
        sell_volume = v - buy_volume
        result.append(buy_volume - sell_volume)
    return result


def volatility_clustering(
    closes: list[float], window: int = 30, lag: int = 1
) -> list[float | None]:
    """Volatility clustering score: rolling autocorrelation of absolute
    returns at the given lag — a well-documented "stylized fact" of
    financial markets (large moves tend to be followed by large moves).
    Positive values indicate clustering; near zero means volatility
    behaves like independent noise."""
    returns = features.returns(closes)
    abs_returns = [abs(r) if r is not None else None for r in returns]
    n = len(abs_returns)
    result: list[float | None] = [None] * n

    for i in range(window + lag, n):
        window_vals = abs_returns[i - window + 1 : i + 1]
        if any(v is None for v in window_vals):
            continue
        lagged = window_vals[:-lag]
        current = window_vals[lag:]
        if len(lagged) < 2:
            continue
        mean_a = sum(lagged) / len(lagged)
        mean_b = sum(current) / len(current)
        covariance = sum((a - mean_a) * (b - mean_b) for a, b in zip(lagged, current))
        variance_a = sum((a - mean_a) ** 2 for a in lagged)
        variance_b = sum((b - mean_b) ** 2 for b in current)
        denom = math.sqrt(variance_a * variance_b)
        result[i] = covariance / denom if denom > 0 else 0.0
    return result


@dataclass(frozen=True)
class VolumeProfileBucket:
    price_low: float
    price_high: float
    volume: float


def volume_profile(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
    bins: int = 10,
) -> list[VolumeProfileBucket]:
    """Volume Profile: how much volume traded at each price level over the
    window — a different shape from a per-candle time series (a
    histogram), used to find the Point of Control (the most-traded price)."""
    if not closes:
        return []
    price_min = min(lows)
    price_max = max(highs)
    if price_max <= price_min:
        return []

    bucket_size = (price_max - price_min) / bins
    totals = [0.0] * bins
    for close_price, volume in zip(closes, volumes):
        index = int((close_price - price_min) / bucket_size)
        index = min(max(index, 0), bins - 1)
        totals[index] += volume

    return [
        VolumeProfileBucket(
            price_low=round(price_min + i * bucket_size, 8),
            price_high=round(price_min + (i + 1) * bucket_size, 8),
            volume=round(totals[i], 8),
        )
        for i in range(bins)
    ]


def point_of_control(profile: list[VolumeProfileBucket]) -> VolumeProfileBucket | None:
    return max(profile, key=lambda bucket: bucket.volume) if profile else None
