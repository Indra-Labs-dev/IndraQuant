import math
import random

from src.modules.machine_learning.domain.features import FEATURE_NAMES, build_features


def test_feature_rows_align_with_labels():
    random.seed(7)
    closes = [100.0]
    for _ in range(120):
        closes.append(closes[-1] * (1 + random.uniform(-0.01, 0.01)))
    volumes = [random.uniform(50, 150) for _ in closes]

    rows, labels, latest = build_features(closes, volumes)

    assert len(rows) == len(labels)
    assert len(rows) > 0
    assert latest is not None
    assert len(latest) == len(FEATURE_NAMES)
    assert all(len(r) == len(FEATURE_NAMES) for r in rows)
    assert all(not math.isnan(v) for r in rows for v in r)
    assert set(labels) <= {0, 1}


def test_not_enough_history_returns_no_rows():
    rows, labels, latest = build_features([100.0] * 10, [1.0] * 10)
    assert rows == []
    assert latest is None
