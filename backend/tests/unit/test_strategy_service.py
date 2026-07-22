import pytest

from src.modules.backtesting.application.dto import StrategySpec
from src.modules.backtesting.application.service import (
    describe,
    min_history,
    positions_for,
    validate_strategy,
)
from src.shared.kernel.errors import AppError


def test_validate_rejects_unknown_strategy_type():
    with pytest.raises(AppError):
        validate_strategy(StrategySpec(type="mystery"))


def test_validate_rejects_inverted_rsi_thresholds():
    with pytest.raises(AppError):
        validate_strategy(StrategySpec(type="rsi_reversion", low=80, high=20))


def test_min_history_depends_on_strategy_type():
    assert min_history(StrategySpec(type="sma_crossover", fast=10, slow=30)) == 32
    assert min_history(StrategySpec(type="rsi_reversion", period=14)) == 16


def test_positions_for_dispatches_to_rsi_strategy():
    closes = [100.0] * 20 + [90.0] * 10 + [110.0] * 10
    positions = positions_for(
        StrategySpec(type="rsi_reversion", period=14, low=30, high=70), closes
    )
    assert len(positions) == len(closes)
    assert set(positions) <= {0, 1}


def test_describe_is_human_readable_french():
    assert "Croisement MM" in describe(StrategySpec(type="sma_crossover"))
    assert "RSI" in describe(StrategySpec(type="rsi_reversion"))


def test_validate_rejects_inverted_macd_periods():
    with pytest.raises(AppError):
        validate_strategy(StrategySpec(type="macd_crossover", fast=26, slow=12))


def test_min_history_for_macd_and_bollinger():
    assert (
        min_history(StrategySpec(type="macd_crossover", fast=12, slow=26, signal=9))
        == 37
    )
    assert min_history(StrategySpec(type="bollinger_breakout", period=20)) == 22


def test_positions_for_dispatches_to_macd_strategy():
    closes = [100.0 + i * 0.5 for i in range(60)]
    positions = positions_for(StrategySpec(type="macd_crossover"), closes)
    assert len(positions) == len(closes)
    assert set(positions) <= {0, 1}


def test_positions_for_dispatches_to_bollinger_strategy():
    closes = [100.0] * 25 + [110.0, 111.0, 112.0] + [95.0, 94.0]
    positions = positions_for(StrategySpec(type="bollinger_breakout"), closes)
    assert len(positions) == len(closes)
    assert set(positions) <= {0, 1}


def test_describe_covers_macd_and_bollinger():
    assert "MACD" in describe(StrategySpec(type="macd_crossover"))
    assert "Bollinger" in describe(StrategySpec(type="bollinger_breakout"))
