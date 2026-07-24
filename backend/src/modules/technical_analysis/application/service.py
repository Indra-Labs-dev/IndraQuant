"""Public facade of the technical_analysis module (pure indicator functions
re-exported for other modules — docs/08 import rule)."""

from src.modules.technical_analysis.domain import indicators


def sma(closes: list[float], period: int) -> list[float | None]:
    return indicators.sma(closes, period)


def ema(closes: list[float], period: int) -> list[float | None]:
    return indicators.ema(closes, period)


def rsi(closes: list[float], period: int = 14) -> list[float | None]:
    return indicators.rsi(closes, period)


def macd(
    closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> dict[str, list[float | None]]:
    return indicators.macd(closes, fast, slow, signal)


def bollinger(
    closes: list[float], period: int = 20, num_std: float = 2.0
) -> dict[str, list[float | None]]:
    return indicators.bollinger(closes, period, num_std)


def vwap(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
    window: int = 20,
) -> list[float | None]:
    return indicators.vwap(highs, lows, closes, volumes, window)


def atr(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> list[float | None]:
    return indicators.atr(highs, lows, closes, period)


def adx(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> list[float | None]:
    return indicators.adx(highs, lows, closes, period)


def donchian(
    highs: list[float], lows: list[float], period: int = 20
) -> dict[str, list[float | None]]:
    return indicators.donchian(highs, lows, period)


def keltner(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 20,
    multiplier: float = 2.0,
) -> dict[str, list[float | None]]:
    return indicators.keltner(highs, lows, closes, period, multiplier)


def obv(closes: list[float], volumes: list[float]) -> list[float]:
    return indicators.obv(closes, volumes)


def mfi(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
    period: int = 14,
) -> list[float | None]:
    return indicators.mfi(highs, lows, closes, volumes, period)


def cci(
    highs: list[float], lows: list[float], closes: list[float], period: int = 20
) -> list[float | None]:
    return indicators.cci(highs, lows, closes, period)


def williams_r(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> list[float | None]:
    return indicators.williams_r(highs, lows, closes, period)


def chaikin_money_flow(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
    period: int = 20,
) -> list[float | None]:
    return indicators.chaikin_money_flow(highs, lows, closes, volumes, period)


def ulcer_index(closes: list[float], period: int = 14) -> list[float | None]:
    return indicators.ulcer_index(closes, period)


def momentum(closes: list[float], period: int = 10) -> list[float | None]:
    return indicators.momentum(closes, period)


def order_flow_proxy(
    highs: list[float], lows: list[float], closes: list[float], volumes: list[float]
) -> list[float]:
    return indicators.order_flow_proxy(highs, lows, closes, volumes)


def volatility_clustering(
    closes: list[float], window: int = 30, lag: int = 1
) -> list[float | None]:
    return indicators.volatility_clustering(closes, window, lag)


def volume_profile(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
    bins: int = 10,
) -> list[indicators.VolumeProfileBucket]:
    return indicators.volume_profile(highs, lows, closes, volumes, bins)
