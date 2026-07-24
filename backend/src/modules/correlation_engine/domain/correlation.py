"""Correlation Engine: Pearson, Spearman, rolling and EWMA ("dynamic")
correlation between two return series. Pure math on stdlib floats only —
no numpy/scipy in the domain layer, matching the existing convention
(risk_management/domain/metrics.py computes variance manually too).
"""

import math


def pearson(x: list[float], y: list[float]) -> float | None:
    n = len(x)
    if n < 2 or n != len(y):
        return None
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    var_x = sum((xi - mean_x) ** 2 for xi in x)
    var_y = sum((yi - mean_y) ** 2 for yi in y)
    denom = math.sqrt(var_x * var_y)
    return cov / denom if denom > 0 else None


def _rank(values: list[float]) -> list[float]:
    """Fractional ranking (ties get the average of their tied positions)."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    return ranks


def spearman(x: list[float], y: list[float]) -> float | None:
    """Spearman rank correlation: Pearson correlation applied to ranks —
    captures monotonic (not necessarily linear) relationships and is more
    robust to outliers than Pearson."""
    if len(x) < 2 or len(x) != len(y):
        return None
    return pearson(_rank(x), _rank(y))


def rolling_correlation(
    x: list[float], y: list[float], window: int
) -> list[float | None]:
    n = len(x)
    result: list[float | None] = [None] * n
    if n != len(y) or window < 2:
        return result
    for i in range(window - 1, n):
        result[i] = pearson(x[i - window + 1 : i + 1], y[i - window + 1 : i + 1])
    return result


def ewma_correlation(
    x: list[float], y: list[float], halflife: int = 20
) -> list[float | None]:
    """'Dynamic' correlation via exponentially-weighted covariance/variance:
    reacts smoothly to changing relationships instead of the hard cutoff of
    a rolling window — a lightweight, fully explainable stand-in for a full
    DCC-GARCH model."""
    n = len(x)
    if n != len(y) or n < 2 or halflife < 1:
        return [None] * n

    alpha = 1.0 - 0.5 ** (1.0 / halflife)
    mean_x, mean_y = x[0], y[0]
    var_x = var_y = cov_xy = 0.0
    result: list[float | None] = [None] * n

    for i in range(1, n):
        mean_x = alpha * x[i] + (1 - alpha) * mean_x
        mean_y = alpha * y[i] + (1 - alpha) * mean_y
        dx, dy = x[i] - mean_x, y[i] - mean_y
        var_x = alpha * dx * dx + (1 - alpha) * var_x
        var_y = alpha * dy * dy + (1 - alpha) * var_y
        cov_xy = alpha * dx * dy + (1 - alpha) * cov_xy
        denom = math.sqrt(var_x * var_y)
        result[i] = cov_xy / denom if denom > 0 else None

    return result


def describe_correlation(value: float | None) -> str:
    if value is None:
        return "Corrélation indéterminée (historique commun insuffisant)."
    strength = (
        "forte" if abs(value) >= 0.7 else "modérée" if abs(value) >= 0.3 else "faible"
    )
    sign = "positive" if value >= 0 else "négative"
    return f"Corrélation {strength} {sign} ({value:+.2f})."
