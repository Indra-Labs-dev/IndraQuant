"""Pure backtest engine: turns a candle series and a position-signal series
into simulated trades, an equity curve and performance metrics. No I/O.
"""

import math
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class BacktestCandle:
    open_time: datetime
    close: float


@dataclass(frozen=True)
class SimulatedTrade:
    side: str
    time: datetime
    price: float
    quantity: float
    fee: float
    reason: str


@dataclass(frozen=True)
class BacktestResult:
    trades: list[SimulatedTrade]
    equity_curve: list[tuple[datetime, float]]
    metrics: dict


def rsi_reversion_positions(
    rsi_values: list[float | None], low: float, high: float
) -> list[int]:
    """Mean-reversion: enter long when RSI drops below `low`, exit when RSI
    rises above `high`. Holds between signals."""
    positions: list[int] = []
    holding = 0
    for value in rsi_values:
        if value is not None:
            if value < low:
                holding = 1
            elif value > high:
                holding = 0
        positions.append(holding)
    return positions


def sma_crossover_positions(
    closes: list[float], fast: int, slow: int
) -> list[int]:
    """Target position per candle: 1 (long) when fast SMA > slow SMA, else 0.
    None-history positions are flat."""
    positions = []
    fast_sum = slow_sum = 0.0
    for i, close in enumerate(closes):
        fast_sum += close
        slow_sum += close
        if i >= fast:
            fast_sum -= closes[i - fast]
        if i >= slow:
            slow_sum -= closes[i - slow]
        if i < slow - 1:
            positions.append(0)
        else:
            positions.append(1 if fast_sum / fast > slow_sum / slow else 0)
    return positions


def run_backtest(
    candles: list[BacktestCandle],
    positions: list[int],
    initial_capital: float,
    fee_rate: float = 0.001,
    periods_per_year: float = 8760.0,
    buy_reason: str = "MM rapide passée au-dessus de la MM lente",
    sell_reason: str = "MM rapide repassée sous la MM lente",
) -> BacktestResult:
    cash = initial_capital
    quantity = 0.0
    trades: list[SimulatedTrade] = []
    equity_curve: list[tuple[datetime, float]] = []
    entry_cost: float | None = None
    round_trips: list[float] = []

    for candle, target in zip(candles, positions):
        if target == 1 and quantity == 0.0 and cash > 0:
            fee = cash * fee_rate
            quantity = (cash - fee) / candle.close
            entry_cost = cash
            cash = 0.0
            trades.append(
                SimulatedTrade(
                    side="buy",
                    time=candle.open_time,
                    price=candle.close,
                    quantity=quantity,
                    fee=fee,
                    reason=buy_reason,
                )
            )
        elif target == 0 and quantity > 0.0:
            gross = quantity * candle.close
            fee = gross * fee_rate
            cash = gross - fee
            trades.append(
                SimulatedTrade(
                    side="sell",
                    time=candle.open_time,
                    price=candle.close,
                    quantity=quantity,
                    fee=fee,
                    reason=sell_reason,
                )
            )
            if entry_cost:
                round_trips.append(cash / entry_cost - 1.0)
            quantity = 0.0
            entry_cost = None
        equity_curve.append((candle.open_time, cash + quantity * candle.close))

    metrics = _metrics(equity_curve, initial_capital, round_trips, periods_per_year)
    metrics["trade_count"] = len(trades)
    return BacktestResult(trades=trades, equity_curve=equity_curve, metrics=metrics)


def _metrics(
    equity_curve: list[tuple[datetime, float]],
    initial_capital: float,
    round_trips: list[float],
    periods_per_year: float,
) -> dict:
    if not equity_curve:
        return {
            "final_equity": initial_capital,
            "total_return": 0.0,
            "max_drawdown": 0.0,
            "sharpe": None,
            "win_rate": None,
        }

    final_equity = equity_curve[-1][1]
    peak = equity_curve[0][1]
    max_drawdown = 0.0
    period_returns = []
    for i, (_, equity) in enumerate(equity_curve):
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, 1.0 - equity / peak)
        if i > 0 and equity_curve[i - 1][1] > 0:
            period_returns.append(equity / equity_curve[i - 1][1] - 1.0)

    sharpe = None
    if len(period_returns) > 1:
        mean = sum(period_returns) / len(period_returns)
        variance = sum((r - mean) ** 2 for r in period_returns) / (
            len(period_returns) - 1
        )
        std = math.sqrt(variance)
        if std > 0:
            sharpe = mean / std * math.sqrt(periods_per_year)

    return {
        "final_equity": final_equity,
        "total_return": final_equity / initial_capital - 1.0,
        "max_drawdown": max_drawdown,
        "sharpe": sharpe,
        "win_rate": (
            sum(1 for r in round_trips if r > 0) / len(round_trips)
            if round_trips
            else None
        ),
    }
