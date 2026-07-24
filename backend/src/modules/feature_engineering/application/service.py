"""Public facade of the feature_engineering module (other modules import
this, never the domain directly — docs/08 import rule)."""

from src.modules.feature_engineering.domain import series


def returns(values: list[float]) -> list[float | None]:
    return series.returns(values)


def log_returns(values: list[float]) -> list[float | None]:
    return series.log_returns(values)


def rolling_mean(values: list[float], window: int) -> list[float | None]:
    return series.rolling_mean(values, window)


def rolling_std(values: list[float], window: int) -> list[float | None]:
    return series.rolling_std(values, window)


def ema(values: list[float], period: int) -> list[float | None]:
    return series.ema(values, period)


def rolling_max(values: list[float], window: int) -> list[float | None]:
    return series.rolling_max(values, window)


def rolling_min(values: list[float], window: int) -> list[float | None]:
    return series.rolling_min(values, window)
