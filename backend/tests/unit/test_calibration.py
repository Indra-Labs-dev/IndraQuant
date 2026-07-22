import pytest

from src.modules.machine_learning.domain.calibration import (
    blend_calibration,
    calibrate_price_interval,
    confidence_bucket,
)


def test_confidence_bucket_boundaries():
    assert confidence_bucket(0.5) == (0.5, 0.55)
    assert confidence_bucket(0.54) == (0.5, 0.55)
    assert confidence_bucket(0.551) == (0.55, 0.6)
    assert confidence_bucket(1.0) == (0.95, 1.0)


def test_confidence_bucket_rejects_out_of_range():
    with pytest.raises(ValueError):
        confidence_bucket(0.4)
    with pytest.raises(ValueError):
        confidence_bucket(1.1)


def test_blend_returns_raw_when_no_history():
    assert blend_calibration(0.8, None, 0) == 0.8
    assert blend_calibration(0.8, 0.6, 0) == 0.8


def test_blend_shifts_toward_observed_accuracy_with_more_samples():
    small_n = blend_calibration(0.9, 0.5, 5)
    large_n = blend_calibration(0.9, 0.5, 500)
    assert 0.5 < small_n < 0.9
    assert 0.5 < large_n < small_n
    assert abs(large_n - 0.5) < 0.05


def test_blend_leaves_perfectly_calibrated_confidence_unchanged():
    assert blend_calibration(0.7, 0.7, 1000) == pytest.approx(0.7, abs=1e-3)


def test_price_interval_unchanged_with_no_track_record():
    low, high = calibrate_price_interval(0.0, -0.02, 0.03, None, 0, 0.8)
    assert (low, high) == (-0.02, 0.03)


def test_price_interval_widens_when_coverage_below_declared_confidence():
    # Interval only caught the real outcome 50% of the time despite claiming 80%.
    low, high = calibrate_price_interval(0.0, -0.02, 0.02, 0.5, 500, 0.8)
    assert low < -0.02
    assert high > 0.02


def test_price_interval_narrows_when_coverage_above_declared_confidence():
    # Interval caught the real outcome 99% of the time despite only claiming 80%.
    low, high = calibrate_price_interval(0.0, -0.02, 0.02, 0.99, 500, 0.8)
    assert -0.02 < low < 0.0
    assert 0.0 < high < 0.02


def test_price_interval_shrinks_adjustment_toward_raw_with_little_history():
    small_n_low, small_n_high = calibrate_price_interval(0.0, -0.02, 0.02, 0.5, 2, 0.8)
    large_n_low, large_n_high = calibrate_price_interval(0.0, -0.02, 0.02, 0.5, 500, 0.8)
    # Both widen (coverage below target), but a tiny sample should adjust less
    # than a large one — closer to the untouched raw interval.
    assert -0.02 > small_n_low > large_n_low
    assert 0.02 < small_n_high < large_n_high


def test_price_interval_stays_symmetric_around_expected_return():
    expected = 0.01
    low, high = calibrate_price_interval(expected, expected - 0.02, expected + 0.03, 0.6, 200, 0.8)
    assert low < expected < high
