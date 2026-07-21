import pytest

from src.modules.machine_learning.domain.calibration import (
    blend_calibration,
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
