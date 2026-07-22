"""Prediction reliability calibration (ADR-020).

This is the mechanism by which the Prediction Engine "learns from its
mistakes" without needing full model retraining: every prediction's raw
confidence is blended with the empirically observed accuracy of past
predictions that fell in the same confidence bucket. As real outcomes
accumulate, the blend shifts away from the raw (possibly over/under
-confident) model output toward what has actually held true historically.
"""

BUCKET_WIDTH = 0.05
_BUCKET_COUNT = int(round(0.5 / BUCKET_WIDTH))
# Pseudo-count anchoring the blend to the raw estimate until enough real
# outcomes have accumulated in a bucket.
PRIOR_STRENGTH = 10


def confidence_bucket(confidence: float) -> tuple[float, float]:
    """Returns the [low, high) bucket a confidence value in [0.5, 1.0] falls into."""
    if not (0.5 <= confidence <= 1.0):
        raise ValueError("confidence must be in [0.5, 1.0]")
    index = min(int((confidence - 0.5) / BUCKET_WIDTH), _BUCKET_COUNT - 1)
    low = 0.5 + index * BUCKET_WIDTH
    return round(low, 4), round(low + BUCKET_WIDTH, 4)


def blend_calibration(
    raw_confidence: float, bucket_accuracy: float | None, bucket_n: int
) -> float:
    """Shrinks the raw confidence toward the bucket's observed accuracy,
    weighted by how many real outcomes back that bucket up (more history =
    more trust in the observed accuracy over the model's raw claim)."""
    if bucket_accuracy is None or bucket_n <= 0:
        return raw_confidence
    weight = bucket_n / (bucket_n + PRIOR_STRENGTH)
    return raw_confidence * (1 - weight) + bucket_accuracy * weight


_MIN_INTERVAL_SCALE = 0.3
_MAX_INTERVAL_SCALE = 3.0


def calibrate_price_interval(
    expected_return: float,
    low_return: float,
    high_return: float,
    empirical_coverage: float | None,
    n_resolved: int,
    declared_confidence: float,
) -> tuple[float, float]:
    """Widens or narrows the price-target interval (ADR-025) based on how
    often past intervals at this timeframe actually contained the real
    outcome (ADR-029) — the same shrinkage philosophy as `blend_calibration`,
    applied to interval width instead of a single confidence number.

    If real coverage has run below the declared confidence, the interval was
    too narrow and gets widened; if it ran above, the interval was too wide
    and gets narrowed. With little or no track record yet, the interval is
    left untouched (scale 1.0)."""
    if empirical_coverage is None or n_resolved <= 0:
        return low_return, high_return

    weight = n_resolved / (n_resolved + PRIOR_STRENGTH)
    coverage_gap = declared_confidence - empirical_coverage
    raw_scale = 1.0 + coverage_gap
    scale = 1.0 * (1 - weight) + raw_scale * weight
    scale = max(_MIN_INTERVAL_SCALE, min(_MAX_INTERVAL_SCALE, scale))

    return (
        expected_return - (expected_return - low_return) * scale,
        expected_return + (high_return - expected_return) * scale,
    )
