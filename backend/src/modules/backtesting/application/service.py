"""Public facade of the backtesting module: strategy resolution shared by
run_backtest, walk-forward and paper trading."""

from src.modules.backtesting.application.dto import StrategySpec
from src.modules.backtesting.domain.engine import (
    bollinger_breakout_positions,
    macd_crossover_positions,
    rsi_reversion_positions,
    sma_crossover_positions,
)
from src.modules.technical_analysis.application import service as ta
from src.shared.kernel.errors import AppError

STRATEGY_TYPES = (
    "sma_crossover",
    "rsi_reversion",
    "macd_crossover",
    "bollinger_breakout",
)


def validate_strategy(strategy: StrategySpec) -> None:
    if strategy.type in ("sma_crossover", "macd_crossover"):
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
    elif strategy.type == "bollinger_breakout":
        pass  # num_std > 0 already enforced by StrategySpec's Field bound
    else:
        raise AppError(
            "unknown_strategy", f"Stratégie inconnue : {strategy.type}", 422
        )


def min_history(strategy: StrategySpec) -> int:
    if strategy.type == "sma_crossover":
        return strategy.slow + 2
    if strategy.type == "macd_crossover":
        return strategy.slow + strategy.signal + 2
    return strategy.period + 2


def positions_for(strategy: StrategySpec, closes: list[float]) -> list[int]:
    validate_strategy(strategy)
    if strategy.type == "sma_crossover":
        return sma_crossover_positions(closes, strategy.fast, strategy.slow)
    if strategy.type == "macd_crossover":
        lines = ta.macd(closes, strategy.fast, strategy.slow, strategy.signal)
        return macd_crossover_positions(lines["macd"], lines["signal"])
    if strategy.type == "bollinger_breakout":
        bands = ta.bollinger(closes, strategy.period, strategy.num_std)
        return bollinger_breakout_positions(closes, bands["upper"], bands["middle"])
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
    if strategy.type == "macd_crossover":
        return (
            f"MACD ({strategy.fast}/{strategy.slow}) passé au-dessus de sa "
            f"ligne de signal ({strategy.signal})",
            f"MACD ({strategy.fast}/{strategy.slow}) repassé sous sa ligne "
            f"de signal ({strategy.signal})",
        )
    if strategy.type == "bollinger_breakout":
        return (
            f"Clôture au-dessus de la bande de Bollinger supérieure "
            f"(période {strategy.period}, {strategy.num_std:g}σ)",
            f"Clôture repassée sous la bande médiane (MM {strategy.period})",
        )
    return (
        f"RSI {strategy.period} passé sous {strategy.low:g} (survente)",
        f"RSI {strategy.period} passé au-dessus de {strategy.high:g} (surachat)",
    )


def describe(strategy: StrategySpec) -> str:
    if strategy.type == "sma_crossover":
        return f"Croisement MM {strategy.fast}/{strategy.slow}"
    if strategy.type == "macd_crossover":
        return f"Croisement MACD {strategy.fast}/{strategy.slow}/{strategy.signal}"
    if strategy.type == "bollinger_breakout":
        return f"Cassure de Bollinger {strategy.period} ({strategy.num_std:g}σ)"
    return f"Retour à la moyenne RSI {strategy.period} ({strategy.low:g}/{strategy.high:g})"
