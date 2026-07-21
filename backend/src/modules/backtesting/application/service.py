"""Public facade of the backtesting module: strategy resolution shared by
run_backtest, walk-forward and paper trading."""

from src.modules.backtesting.application.dto import StrategySpec
from src.modules.backtesting.domain.engine import (
    rsi_reversion_positions,
    sma_crossover_positions,
)
from src.modules.technical_analysis.application import service as ta
from src.shared.kernel.errors import AppError

STRATEGY_TYPES = ("sma_crossover", "rsi_reversion")


def validate_strategy(strategy: StrategySpec) -> None:
    if strategy.type == "sma_crossover":
        if strategy.fast >= strategy.slow:
            raise AppError(
                "invalid_strategy",
                "La période rapide doit être inférieure à la période lente.",
                422,
            )
    elif strategy.type == "rsi_reversion":
        if strategy.low >= strategy.high:
            raise AppError(
                "invalid_strategy",
                "Le seuil bas du RSI doit être inférieur au seuil haut.",
                422,
            )
    else:
        raise AppError(
            "unknown_strategy", f"Stratégie inconnue : {strategy.type}", 422
        )


def min_history(strategy: StrategySpec) -> int:
    if strategy.type == "sma_crossover":
        return strategy.slow + 2
    return strategy.period + 2


def positions_for(strategy: StrategySpec, closes: list[float]) -> list[int]:
    validate_strategy(strategy)
    if strategy.type == "sma_crossover":
        return sma_crossover_positions(closes, strategy.fast, strategy.slow)
    return rsi_reversion_positions(
        ta.rsi(closes, strategy.period), strategy.low, strategy.high
    )


def latest_target_position(strategy: StrategySpec, closes: list[float]) -> int:
    if len(closes) < min_history(strategy):
        return 0
    return positions_for(strategy, closes)[-1]


def trade_reasons(strategy: StrategySpec) -> tuple[str, str]:
    if strategy.type == "sma_crossover":
        return (
            f"MM {strategy.fast} passée au-dessus de la MM {strategy.slow}",
            f"MM {strategy.fast} repassée sous la MM {strategy.slow}",
        )
    return (
        f"RSI {strategy.period} passé sous {strategy.low:g} (survente)",
        f"RSI {strategy.period} passé au-dessus de {strategy.high:g} (surachat)",
    )


def describe(strategy: StrategySpec) -> str:
    if strategy.type == "sma_crossover":
        return f"Croisement MM {strategy.fast}/{strategy.slow}"
    return f"Retour à la moyenne RSI {strategy.period} ({strategy.low:g}/{strategy.high:g})"
