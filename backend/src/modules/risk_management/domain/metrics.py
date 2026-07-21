"""Risk metrics as pure functions over an equity curve (list of floats)."""

import math


def period_returns(equity: list[float]) -> list[float]:
    return [
        equity[i] / equity[i - 1] - 1.0
        for i in range(1, len(equity))
        if equity[i - 1] > 0
    ]


def historical_var(returns: list[float], confidence: float = 0.95) -> float | None:
    """Historical Value-at-Risk: the loss threshold not exceeded with the
    given confidence, expressed as a positive fraction."""
    if len(returns) < 20:
        return None
    ordered = sorted(returns)
    # Conservative quantile: with n observations the (1-c) tail rounds down
    # to the worse order statistic.
    index = max(int((1.0 - confidence) * len(ordered)) - 1, 0)
    return max(-ordered[index], 0.0)


def max_drawdown(equity: list[float]) -> float:
    peak = equity[0] if equity else 0.0
    drawdown = 0.0
    for value in equity:
        peak = max(peak, value)
        if peak > 0:
            drawdown = max(drawdown, 1.0 - value / peak)
    return drawdown


def annualized_volatility(
    returns: list[float], periods_per_year: float
) -> float | None:
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(variance) * math.sqrt(periods_per_year)
