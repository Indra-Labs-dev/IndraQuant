"""Advanced Risk Engine (docs/roadmap #10): Kelly Criterion, Expected
Shortfall (CVaR), Risk of Ruin (Monte Carlo simulation, consistent with
the Monte Carlo methodology already used in the Validation module),
Position Sizing, Stress Testing, Exposure Control, and Risk Budget
(inverse-volatility risk parity). Pure functions over plain floats — same
stdlib-only convention as `metrics.py`.
"""

import random
from dataclasses import dataclass

_DEFAULT_STRESS_SHOCKS = (-0.10, -0.20, -0.30, -0.50)


def expected_shortfall(returns: list[float], confidence: float = 0.95) -> float | None:
    """Expected Shortfall / CVaR: the average loss *beyond* the VaR
    threshold — unlike VaR (a single quantile), CVaR captures how bad the
    tail actually is, which is what actually determines ruin risk."""
    if len(returns) < 20:
        return None
    ordered = sorted(returns)
    tail_size = max(int((1.0 - confidence) * len(ordered)), 1)
    tail = ordered[:tail_size]
    return max(-(sum(tail) / len(tail)), 0.0)


@dataclass(frozen=True)
class KellyResult:
    fraction: float
    has_edge: bool
    explanation: str


def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> KellyResult:
    """Kelly Criterion: the capital fraction that maximizes long-run
    geometric growth given a win probability and win/loss odds. A
    non-positive result means the strategy has no statistical edge at
    these odds — betting anything would be expected to lose money over
    time, so the fraction is clamped to 0."""
    if avg_loss <= 0 or not (0.0 <= win_rate <= 1.0):
        return KellyResult(0.0, False, "Paramètres invalides pour calculer le Kelly.")

    odds = avg_win / avg_loss
    raw_fraction = win_rate - (1.0 - win_rate) / odds if odds > 0 else -1.0
    has_edge = raw_fraction > 0
    fraction = max(raw_fraction, 0.0)

    return KellyResult(
        round(fraction, 4),
        has_edge,
        (
            f"Fraction de Kelly {fraction * 100:.1f} % du capital par position "
            f"(taux de réussite {win_rate * 100:.1f} %, ratio gain/perte {odds:.2f})."
            if has_edge
            else "Pas d'avantage statistique à ces cotes (Kelly ≤ 0) — ne pas "
            "miser tant que le taux de réussite ou le ratio gain/perte ne "
            "s'améliore pas."
        ),
    )


def risk_of_ruin(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    position_fraction: float,
    n_trades: int = 200,
    n_simulations: int = 2000,
    ruin_fraction: float = 0.5,
    seed: int = 42,
) -> float:
    """Risk of Ruin via Monte Carlo simulation (not a closed-form
    approximation, to stay consistent and transparent with the Monte
    Carlo approach already used for backtest validation): simulates many
    equity paths under the given win rate / payoff / position-sizing rule
    and reports the fraction of paths that fall to `ruin_fraction` of
    starting capital within `n_trades`."""
    if not (0.0 <= win_rate <= 1.0) or position_fraction <= 0 or avg_win < 0 or avg_loss < 0:
        return 1.0

    rng = random.Random(seed)
    ruined = 0
    for _ in range(n_simulations):
        equity = 1.0
        for _ in range(n_trades):
            stake = equity * position_fraction
            if rng.random() < win_rate:
                equity += stake * avg_win
            else:
                equity -= stake * avg_loss
            if equity <= ruin_fraction:
                ruined += 1
                break
    return ruined / n_simulations


@dataclass(frozen=True)
class PositionSize:
    quantity: float
    risk_amount: float
    position_value: float
    capital_at_risk_pct: float
    explanation: str


def position_sizing(
    capital: float,
    risk_per_trade_pct: float,
    entry_price: float,
    stop_price: float,
) -> PositionSize:
    """Fixed-fractional position sizing: risk a fixed percentage of
    capital per trade, sized so that a stop-loss hit loses exactly that
    percentage — not a percentage of the position's notional value."""
    per_unit_risk = abs(entry_price - stop_price)
    if capital <= 0 or risk_per_trade_pct <= 0 or per_unit_risk <= 0 or entry_price <= 0:
        return PositionSize(0.0, 0.0, 0.0, 0.0, "Paramètres invalides pour dimensionner la position.")

    risk_amount = capital * risk_per_trade_pct
    quantity = risk_amount / per_unit_risk
    position_value = quantity * entry_price

    return PositionSize(
        round(quantity, 8),
        round(risk_amount, 2),
        round(position_value, 2),
        round(risk_per_trade_pct * 100, 2),
        f"Risquer {risk_per_trade_pct * 100:.2f} % du capital ({risk_amount:.2f}) "
        f"avec un stop à {stop_price:g} (écart {per_unit_risk:g} par unité) donne "
        f"une taille de position de {quantity:.6f} unité(s), valeur notionnelle "
        f"{position_value:.2f}.",
    )


@dataclass(frozen=True)
class StressScenario:
    shock_pct: float
    resulting_value: float
    loss_amount: float


def stress_test(
    portfolio_value: float, shocks: tuple[float, ...] = _DEFAULT_STRESS_SHOCKS
) -> list[StressScenario]:
    """Applies a set of hypothetical instantaneous shocks (e.g. -10 %/-20 %/
    -30 %/-50 %) to the current portfolio value — a standard stress-test
    exercise answering "what happens to my capital if the market crashes
    by X %", independent of any historical distribution assumption."""
    return [
        StressScenario(
            shock_pct=shock,
            resulting_value=round(portfolio_value * (1.0 + shock), 2),
            loss_amount=round(portfolio_value * -shock, 2),
        )
        for shock in shocks
    ]


@dataclass(frozen=True)
class ExposureWarning:
    instrument: str
    weight_pct: float
    limit_pct: float
    message: str


def check_exposure(
    allocations: list[tuple[str, float]],
    max_single_pct: float = 25.0,
    max_total_pct: float = 100.0,
) -> tuple[list[ExposureWarning], float]:
    """Exposure Control: flags any single position beyond `max_single_pct`
    of the portfolio, and reports total exposure vs `max_total_pct`
    (exceeding 100 % would imply leverage)."""
    warnings: list[ExposureWarning] = []
    for instrument, weight_pct in allocations:
        if weight_pct > max_single_pct:
            warnings.append(
                ExposureWarning(
                    instrument,
                    round(weight_pct, 2),
                    max_single_pct,
                    f"{instrument} représente {weight_pct:.1f} % du portefeuille, "
                    f"au-dessus de la limite de {max_single_pct:.1f} % par position.",
                )
            )
    total = sum(weight_pct for _, weight_pct in allocations)
    if total > max_total_pct:
        warnings.append(
            ExposureWarning(
                "TOTAL",
                round(total, 2),
                max_total_pct,
                f"Exposition totale {total:.1f} % au-dessus de la limite de "
                f"{max_total_pct:.1f} % — effet de levier implicite.",
            )
        )
    return warnings, round(total, 2)


def risk_budget_allocation(
    volatilities: dict[str, float], total_capital_pct: float = 100.0
) -> dict[str, float]:
    """Risk Budget via inverse-volatility weighting (simple risk parity):
    each position's target capital weight is inversely proportional to
    its own volatility, so that — to a first approximation — every
    position contributes roughly equal risk to the portfolio, rather than
    equal capital contributing wildly different risk."""
    positive = {name: vol for name, vol in volatilities.items() if vol > 0}
    if not positive:
        return {name: 0.0 for name in volatilities}

    inverse = {name: 1.0 / vol for name, vol in positive.items()}
    total_inverse = sum(inverse.values())
    weights = {
        name: round((inv / total_inverse) * total_capital_pct, 2)
        for name, inv in inverse.items()
    }
    for name in volatilities:
        weights.setdefault(name, 0.0)
    return weights
