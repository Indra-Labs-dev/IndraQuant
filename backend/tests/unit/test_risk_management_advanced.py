from src.modules.risk_management.domain.advanced import (
    check_exposure,
    expected_shortfall,
    kelly_criterion,
    position_sizing,
    risk_budget_allocation,
    risk_of_ruin,
    stress_test,
)


def test_expected_shortfall_none_with_insufficient_history():
    assert expected_shortfall([0.01] * 5) is None


def test_expected_shortfall_averages_the_worst_tail():
    returns = [0.01] * 18 + [-0.10, -0.20]
    cvar = expected_shortfall(returns, confidence=0.9)
    assert cvar is not None
    assert cvar > 0.10  # worse than the milder of the two tail losses


def test_kelly_criterion_positive_edge():
    result = kelly_criterion(win_rate=0.6, avg_win=0.02, avg_loss=0.01)
    assert result.has_edge is True
    assert result.fraction > 0


def test_kelly_criterion_no_edge_clamped_to_zero():
    result = kelly_criterion(win_rate=0.3, avg_win=0.01, avg_loss=0.02)
    assert result.has_edge is False
    assert result.fraction == 0.0


def test_kelly_criterion_invalid_inputs():
    result = kelly_criterion(win_rate=0.5, avg_win=0.01, avg_loss=0.0)
    assert result.fraction == 0.0
    assert result.has_edge is False


def test_risk_of_ruin_certain_without_edge():
    # Strongly negative edge (low win rate, losses much larger than wins)
    # combined with full-fraction betting over many trades should drive
    # equity below the ruin threshold in almost every simulated path.
    ruin = risk_of_ruin(
        win_rate=0.3, avg_win=0.01, avg_loss=0.05, position_fraction=1.0,
        n_trades=200, n_simulations=200,
    )
    assert ruin > 0.5


def test_risk_of_ruin_low_with_strong_edge_and_small_bets():
    ruin = risk_of_ruin(
        win_rate=0.65, avg_win=0.02, avg_loss=0.01, position_fraction=0.02,
        n_trades=100, n_simulations=500,
    )
    assert ruin < 0.2


def test_risk_of_ruin_invalid_inputs_returns_certain_ruin():
    assert risk_of_ruin(1.5, 0.01, 0.01, 0.1) == 1.0


def test_position_sizing_computes_expected_quantity():
    result = position_sizing(
        capital=10_000.0, risk_per_trade_pct=0.01, entry_price=100.0, stop_price=98.0
    )
    # Risking 1% of 10000 = 100, stop distance 2 -> quantity 50.
    assert result.quantity == 50.0
    assert result.risk_amount == 100.0


def test_position_sizing_invalid_when_stop_equals_entry():
    result = position_sizing(10_000.0, 0.01, 100.0, 100.0)
    assert result.quantity == 0.0


def test_stress_test_applies_shocks_to_portfolio_value():
    scenarios = stress_test(10_000.0, shocks=(-0.10, -0.50))
    assert scenarios[0].resulting_value == 9_000.0
    assert scenarios[0].loss_amount == 1_000.0
    assert scenarios[1].resulting_value == 5_000.0


def test_check_exposure_flags_concentrated_position():
    warnings, total = check_exposure([("BTC/USDT", 60.0), ("ETH/USDT", 40.0)], max_single_pct=50.0)
    assert any(w.instrument == "BTC/USDT" for w in warnings)
    assert total == 100.0


def test_check_exposure_flags_total_leverage():
    warnings, total = check_exposure([("BTC/USDT", 80.0), ("ETH/USDT", 80.0)], max_single_pct=90.0)
    assert any(w.instrument == "TOTAL" for w in warnings)
    assert total == 160.0


def test_check_exposure_no_warnings_when_within_limits():
    warnings, total = check_exposure([("BTC/USDT", 20.0), ("ETH/USDT", 20.0)])
    assert warnings == []
    assert total == 40.0


def test_risk_budget_allocation_inversely_weights_volatility():
    weights = risk_budget_allocation({"low_vol": 0.1, "high_vol": 0.4})
    assert weights["low_vol"] > weights["high_vol"]
    assert abs(sum(weights.values()) - 100.0) < 1e-6


def test_risk_budget_allocation_handles_all_zero_volatility():
    weights = risk_budget_allocation({"a": 0.0, "b": 0.0})
    assert weights == {"a": 0.0, "b": 0.0}
