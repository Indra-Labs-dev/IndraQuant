import math

from src.modules.correlation_engine.domain.correlation import (
    describe_correlation,
    ewma_correlation,
    pearson,
    rolling_correlation,
    spearman,
)


def test_pearson_perfect_positive_correlation():
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [2.0, 4.0, 6.0, 8.0, 10.0]
    assert math.isclose(pearson(x, y), 1.0, abs_tol=1e-9)


def test_pearson_perfect_negative_correlation():
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [10.0, 8.0, 6.0, 4.0, 2.0]
    assert math.isclose(pearson(x, y), -1.0, abs_tol=1e-9)


def test_pearson_none_with_mismatched_lengths():
    assert pearson([1.0, 2.0], [1.0]) is None


def test_pearson_none_with_zero_variance():
    assert pearson([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) is None


def test_spearman_perfect_for_monotonic_nonlinear_relationship():
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [1.0, 4.0, 9.0, 16.0, 25.0]  # monotonic but non-linear (x^2)
    assert math.isclose(spearman(x, y), 1.0, abs_tol=1e-9)
    # Pearson on the same series is high but not exactly 1 (non-linear).
    assert pearson(x, y) < 1.0


def test_spearman_handles_ties():
    x = [1.0, 1.0, 2.0, 3.0]
    y = [1.0, 1.0, 2.0, 3.0]
    assert math.isclose(spearman(x, y), 1.0, abs_tol=1e-9)


def test_rolling_correlation_aligns_with_input_length():
    x = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    y = [2.0, 4.0, 6.0, 8.0, 10.0, 12.0]
    result = rolling_correlation(x, y, window=3)
    assert len(result) == len(x)
    assert result[0] is None and result[1] is None
    assert result[2] is not None
    assert math.isclose(result[-1], 1.0, abs_tol=1e-9)


def test_ewma_correlation_converges_toward_strong_positive():
    x = [1.0 + 0.1 * i for i in range(50)]
    y = [2.0 + 0.2 * i for i in range(50)]
    result = ewma_correlation(x, y, halflife=10)
    assert len(result) == len(x)
    assert result[0] is None
    assert result[-1] is not None
    assert result[-1] > 0.9


def test_describe_correlation_labels():
    assert "forte" in describe_correlation(0.85)
    assert "positive" in describe_correlation(0.85)
    assert "négative" in describe_correlation(-0.85)
    assert "faible" in describe_correlation(0.05)
    assert "indéterminée" in describe_correlation(None)
