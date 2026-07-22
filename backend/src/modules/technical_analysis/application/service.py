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
