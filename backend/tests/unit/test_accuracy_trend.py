from src.modules.machine_learning.domain.trend import rolling_accuracy_trend


def test_trend_grows_with_perfect_streak():
    trend = rolling_accuracy_trend([True, True, True])
    assert trend == [1.0, 1.0, 1.0]


def test_trend_reflects_mixed_results():
    trend = rolling_accuracy_trend([True, False, True, True])
    assert trend == [1.0, 0.5, 2 / 3, 0.75]


def test_trend_uses_rolling_window_not_full_history():
    flags = [True] * 20 + [False] * 20
    trend = rolling_accuracy_trend(flags, window=20)
    # First 20 are all correct.
    assert trend[19] == 1.0
    # After 20 more incorrect ones, the window has fully rolled over.
    assert trend[-1] == 0.0


def test_empty_input_returns_empty_trend():
    assert rolling_accuracy_trend([]) == []
