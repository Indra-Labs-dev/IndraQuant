import math
import random

from src.modules.machine_learning.domain.features import FEATURE_NAMES, build_features


def test_feature_rows_align_with_labels_and_returns():
    random.seed(7)
    closes = [100.0]
    for _ in range(120):
        closes.append(closes[-1] * (1 + random.uniform(-0.01, 0.01)))
    volumes = [random.uniform(50, 150) for _ in closes]

    rows, labels, returns, latest = build_features(closes, volumes)

    assert len(rows) == len(labels) == len(returns)
    assert len(rows) > 0
    assert latest is not None
    assert len(latest) == len(FEATURE_NAMES)
    assert all(len(r) == len(FEATURE_NAMES) for r in rows)
    assert all(not math.isnan(v) for r in rows for v in r)
    assert set(labels) <= {0, 1}
    assert all(not math.isnan(r) for r in returns)


def test_returns_are_consistent_with_labels():
    # A positive log-return must always pair with an "up" (1) label and
    # vice versa — same underlying close-to-close move.
    random.seed(3)
    closes = [100.0]
    for _ in range(120):
        closes.append(closes[-1] * (1 + random.uniform(-0.02, 0.02)))
    volumes = [random.uniform(50, 150) for _ in closes]

    _, labels, returns, _ = build_features(closes, volumes)

    for label, log_return in zip(labels, returns):
        assert (log_return > 0) == (label == 1)


def test_not_enough_history_returns_no_rows():
    rows, labels, returns, latest = build_features([100.0] * 10, [1.0] * 10)
    assert rows == []
    assert labels == []
    assert returns == []
    assert latest is None


def test_moves_inside_dead_zone_are_excluded_from_training():
    # A flat series (every candle identical) produces exactly zero-move rows
    # everywhere — all of them must fall inside the dead zone and be dropped,
    # rather than all being hard-labeled "down" (0.0 close-to-close move is
    # not `>` so the old pure-sign rule silently mislabeled it as "down").
    closes = [100.0] * 120
    volumes = [100.0] * 120

    rows, labels, returns, _ = build_features(closes, volumes)

    assert rows == []
    assert labels == []
    assert returns == []


def test_moves_above_dead_zone_are_kept():
    import random

    random.seed(11)
    closes = [100.0]
    for _ in range(120):
        # Moves well above the 0.05% dead zone threshold.
        closes.append(closes[-1] * (1 + random.choice([-1, 1]) * random.uniform(0.01, 0.02)))
    volumes = [random.uniform(50, 150) for _ in closes]

    rows, labels, _, _ = build_features(closes, volumes)

    assert len(rows) > 0
    assert len(rows) == len(labels)


def test_volatility_feature_is_none_only_before_enough_real_returns_exist():
    # Regression test for the zero-fill bug: volatility_20 must be undefined
    # (row dropped) until there are 20 *real* returns, not deflated by
    # treating the missing leading return as a literal 0.0 return.
    random.seed(5)
    closes = [100.0]
    for _ in range(120):
        closes.append(closes[-1] * (1 + random.uniform(-0.03, 0.03)))
    volumes = [random.uniform(50, 150) for _ in closes]

    rows, _, _, _ = build_features(closes, volumes)
    volatility_index = FEATURE_NAMES.index("volatility_20")
    volatilities = [r[volatility_index] for r in rows]

    # With genuinely volatile synthetic data every retained volatility value
    # should be a real, non-trivial positive number (not artificially near
    # zero from a phantom zero-return baked into the first window).
    assert all(v > 0 for v in volatilities)


def test_correlation_feature_uses_reference_series_when_provided():
    random.seed(9)
    closes = [100.0]
    for _ in range(120):
        closes.append(closes[-1] * (1 + random.uniform(-0.02, 0.02)))
    volumes = [random.uniform(50, 150) for _ in closes]
    # Reference series that moves in lockstep with `closes` — correlation
    # should end up strongly positive rather than the neutral fallback.
    reference_closes = [c * 2.0 for c in closes]

    rows, _, _, latest = build_features(closes, volumes, reference_closes)
    correlation_index = FEATURE_NAMES.index("correlation_btc_20")

    assert latest is not None
    assert latest[correlation_index] > 0.9


def test_correlation_feature_is_neutral_without_a_reference_series():
    random.seed(9)
    closes = [100.0]
    for _ in range(120):
        closes.append(closes[-1] * (1 + random.uniform(-0.02, 0.02)))
    volumes = [random.uniform(50, 150) for _ in closes]

    rows, _, _, _ = build_features(closes, volumes)
    correlation_index = FEATURE_NAMES.index("correlation_btc_20")

    assert all(r[correlation_index] == 0.0 for r in rows)
