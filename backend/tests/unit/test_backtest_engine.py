from datetime import datetime, timedelta

from src.modules.backtesting.domain.engine import (
    BacktestCandle,
    bollinger_breakout_positions,
    macd_crossover_positions,
    run_backtest,
    sma_crossover_positions,
)
from src.modules.risk_management.domain.metrics import historical_var, max_drawdown


def make_candles(closes: list[float]) -> list[BacktestCandle]:
    base = datetime(2026, 1, 1)
    return [
        BacktestCandle(open_time=base + timedelta(hours=i), close=c)
        for i, c in enumerate(closes)
    ]


def test_crossover_positions_flat_before_history():
    closes = [10.0, 11.0, 12.0, 13.0, 14.0]
    positions = sma_crossover_positions(closes, 2, 4)
    assert positions[:3] == [0, 0, 0]
    assert positions[4] == 1  # rising series: fast SMA above slow SMA


def test_backtest_buys_then_sells_and_tracks_equity():
    # Rising then falling series forces one entry and one exit.
    closes = [10.0] * 4 + [11.0, 12.0, 13.0, 14.0, 13.0, 11.0, 9.0, 8.0]
    candles = make_candles(closes)
    positions = sma_crossover_positions(closes, 2, 4)
    result = run_backtest(candles, positions, 1000.0, fee_rate=0.0)

    sides = [t.side for t in result.trades]
    assert sides.count("buy") == sides.count("sell") == 1
    assert len(result.equity_curve) == len(candles)
    assert result.metrics["trade_count"] == 2
    assert result.metrics["win_rate"] is not None


def test_fees_reduce_final_equity():
    closes = [10.0] * 4 + [11.0, 12.0, 13.0, 12.0, 10.0, 9.0]
    candles = make_candles(closes)
    positions = sma_crossover_positions(closes, 2, 4)
    without_fees = run_backtest(candles, positions, 1000.0, fee_rate=0.0)
    with_fees = run_backtest(candles, positions, 1000.0, fee_rate=0.01)
    assert (
        with_fees.metrics["final_equity"] < without_fees.metrics["final_equity"]
    )


def test_max_drawdown_and_var():
    equity = [100.0, 110.0, 99.0, 104.5, 120.0]
    assert abs(max_drawdown(equity) - 0.1) < 1e-9
    returns = [0.01] * 19 + [-0.05]
    assert historical_var(returns) == 0.05


def test_macd_crossover_positions_long_when_macd_above_signal():
    macd_line = [None, 1.0, 2.0, -1.0]
    signal_line = [None, 0.5, 1.5, 0.0]
    assert macd_crossover_positions(macd_line, signal_line) == [0, 1, 1, 0]


def test_macd_crossover_positions_flat_when_missing_history():
    assert macd_crossover_positions([None, None], [None, None]) == [0, 0]


def test_bollinger_breakout_enters_above_upper_band_exits_below_middle():
    closes = [100.0, 100.0, 106.0, 103.0, 98.0]
    upper = [None, None, 105.0, 105.0, 105.0]
    middle = [None, None, 100.0, 100.0, 100.0]
    positions = bollinger_breakout_positions(closes, upper, middle)
    assert positions == [0, 0, 1, 1, 0]
