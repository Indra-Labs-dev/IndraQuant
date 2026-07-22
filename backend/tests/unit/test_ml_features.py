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
