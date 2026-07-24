import math

from src.modules.validation.domain.resampling import (
    bootstrap_confidence_interval,
    monte_carlo_permutation_test,
    white_reality_check,
)


def test_bootstrap_insufficient_history():
    result = bootstrap_confidence_interval([0.01] * 5)
    assert result.explanation.startswith("Historique insuffisant")


def test_bootstrap_ci_excludes_zero_for_consistently_positive_returns():
    values = [0.01] * 100
    result = bootstrap_confidence_interval(values, n_iterations=500, seed=1)
    assert result.ci_low > 0
    assert math.isclose(result.mean, 0.01, abs_tol=1e-9)


def test_bootstrap_ci_includes_zero_for_noisy_zero_mean_returns():
    values = [0.02, -0.02] * 50
    result = bootstrap_confidence_interval(values, n_iterations=500, seed=1)
    assert result.ci_low <= 0 <= result.ci_high


def test_monte_carlo_insufficient_history():
    result = monte_carlo_permutation_test([0.01] * 5, [1] * 5)
    assert result.p_value == 1.0


def test_monte_carlo_low_p_value_for_perfect_timing():
    market_returns = [0.03, -0.02, 0.04, -0.01, 0.05, -0.03, 0.02, -0.01] * 5
    positions = [1 if r > 0 else 0 for r in market_returns]
    result = monte_carlo_permutation_test(
        market_returns, positions, n_iterations=500, seed=7
    )
    assert result.observed_return > result.null_mean
    assert result.p_value < 0.1


def test_monte_carlo_constant_positions_has_p_value_one():
    # Shuffling a uniform position mask changes nothing — the observed
    # result is exactly the null distribution's only possible value.
    market_returns = [0.01, -0.01] * 20
    positions = [1] * 40
    result = monte_carlo_permutation_test(
        market_returns, positions, n_iterations=200, seed=1
    )
    assert result.p_value == 1.0


def test_white_reality_check_insufficient_history():
    result = white_reality_check([[0.01] * 5])
    assert result.n_candidates == 1
    assert result.p_value == 1.0


def test_white_reality_check_identifies_best_candidate():
    candidates = [
        [0.001] * 40,
        [0.01] * 40,
        [-0.005] * 40,
    ]
    result = white_reality_check(candidates, n_iterations=300, seed=3)
    assert result.best_candidate_index == 1
    assert math.isclose(result.best_mean_return, 0.01, abs_tol=1e-9)
    # Every candidate is constant, so every bootstrap draw reproduces the
    # exact same mean per candidate — the observed best is clearly better
    # than the (zero-variance) null, giving a p-value of exactly 0.
    assert result.p_value == 0.0
