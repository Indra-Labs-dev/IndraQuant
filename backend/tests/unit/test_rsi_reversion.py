from src.modules.backtesting.domain.engine import rsi_reversion_positions


def test_enters_on_oversold_and_exits_on_overbought():
    rsi_values = [None, 50.0, 25.0, 40.0, 60.0, 75.0, 50.0]
    positions = rsi_reversion_positions(rsi_values, low=30.0, high=70.0)
    assert positions == [0, 0, 1, 1, 1, 0, 0]


def test_holds_position_through_missing_rsi_values():
    rsi_values = [25.0, None, None, 75.0]
    positions = rsi_reversion_positions(rsi_values, low=30.0, high=70.0)
    assert positions == [1, 1, 1, 0]
