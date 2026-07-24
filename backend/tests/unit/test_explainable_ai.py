import math
from datetime import datetime

from src.modules.explainable_ai.domain.analysis import (
    FeatureContributionPoint,
    aggregate_feature_importance,
    compare_explanations,
    feature_importance_over_time,
)


def _point(feature: str, contribution: float, value: float = 0.0) -> FeatureContributionPoint:
    return FeatureContributionPoint(feature=feature, value=value, contribution=contribution)


def test_aggregate_feature_importance_ranks_by_mean_absolute_contribution():
    history = [
        [_point("rsi_14", 0.5), _point("return_1", 0.1)],
        [_point("rsi_14", -0.4), _point("return_1", 0.05)],
        [_point("rsi_14", 0.3), _point("return_1", 0.02)],
    ]
    ranking = aggregate_feature_importance(history)
    assert ranking[0].feature == "rsi_14"
    assert ranking[0].rank == 1
    assert ranking[1].feature == "return_1"


def test_aggregate_feature_importance_empty_history():
    assert aggregate_feature_importance([]) == []


def test_feature_importance_over_time_orders_chronologically():
    history = [
        (datetime(2026, 1, 3), [_point("rsi_14", 0.2)]),
        (datetime(2026, 1, 1), [_point("rsi_14", 0.5)]),
        (datetime(2026, 1, 2), [_point("rsi_14", -0.1)]),
    ]
    points = feature_importance_over_time(history, "rsi_14")
    assert [p.as_of for p in points] == [
        datetime(2026, 1, 1), datetime(2026, 1, 2), datetime(2026, 1, 3)
    ]
    assert points[0].contribution == 0.5


def test_feature_importance_over_time_skips_predictions_without_the_feature():
    history = [
        (datetime(2026, 1, 1), [_point("rsi_14", 0.5)]),
        (datetime(2026, 1, 2), [_point("return_1", 0.1)]),
    ]
    points = feature_importance_over_time(history, "rsi_14")
    assert len(points) == 1


def test_compare_explanations_identical_vectors_has_similarity_one():
    a = [_point("rsi_14", 0.5), _point("return_1", 0.2)]
    b = [_point("rsi_14", 0.5), _point("return_1", 0.2)]
    result = compare_explanations(a, b)
    assert math.isclose(result.similarity, 1.0, abs_tol=1e-9)
    assert all(d.delta == 0.0 for d in result.deltas)


def test_compare_explanations_opposite_vectors_has_negative_similarity():
    a = [_point("rsi_14", 0.5), _point("return_1", 0.2)]
    b = [_point("rsi_14", -0.5), _point("return_1", -0.2)]
    result = compare_explanations(a, b)
    assert result.similarity < 0


def test_compare_explanations_sorts_deltas_by_magnitude():
    a = [_point("rsi_14", 0.1), _point("return_1", 0.1)]
    b = [_point("rsi_14", 0.9), _point("return_1", 0.15)]
    result = compare_explanations(a, b)
    assert result.deltas[0].feature == "rsi_14"


def test_compare_explanations_handles_missing_features_on_one_side():
    a = [_point("rsi_14", 0.5)]
    b = [_point("return_1", 0.3)]
    result = compare_explanations(a, b)
    features = {d.feature for d in result.deltas}
    assert features == {"rsi_14", "return_1"}


def test_compare_explanations_none_similarity_with_zero_vectors():
    result = compare_explanations([], [])
    assert result.similarity is None
