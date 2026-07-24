"""Explainable AI, advanced (docs/roadmap #15): global feature importance,
feature evolution over time, and side-by-side comparison of two SHAP
explanations — all derived from the SHAP contributions the Prediction
Engine already computes and now persists per prediction (migration 006).
Pure functions, no I/O.
"""

import math
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FeatureContributionPoint:
    feature: str
    value: float
    contribution: float


@dataclass(frozen=True)
class GlobalImportance:
    feature: str
    mean_absolute_contribution: float
    rank: int


def aggregate_feature_importance(
    history: list[list[FeatureContributionPoint]],
) -> list[GlobalImportance]:
    """Global feature importance: the mean *absolute* SHAP contribution of
    each feature across many past predictions. A feature that swings a
    single prediction a lot but is usually irrelevant averages out here —
    this ranks what matters overall, not what mattered once."""
    sums: dict[str, float] = {}
    counts: dict[str, int] = {}
    for contributions in history:
        for c in contributions:
            sums[c.feature] = sums.get(c.feature, 0.0) + abs(c.contribution)
            counts[c.feature] = counts.get(c.feature, 0) + 1

    means = sorted(
        ((feature, sums[feature] / counts[feature]) for feature in sums),
        key=lambda item: item[1],
        reverse=True,
    )
    return [
        GlobalImportance(feature=feature, mean_absolute_contribution=round(mean, 6), rank=i + 1)
        for i, (feature, mean) in enumerate(means)
    ]


@dataclass(frozen=True)
class FeatureTimePoint:
    as_of: datetime
    contribution: float


def feature_importance_over_time(
    history: list[tuple[datetime, list[FeatureContributionPoint]]], feature_name: str
) -> list[FeatureTimePoint]:
    """The chosen feature's SHAP contribution across past predictions, in
    chronological order — does this feature's influence grow, shrink, or
    flip sign over time?"""
    points = []
    for as_of, contributions in history:
        match = next((c for c in contributions if c.feature == feature_name), None)
        if match is not None:
            points.append(FeatureTimePoint(as_of=as_of, contribution=match.contribution))
    return sorted(points, key=lambda p: p.as_of)


@dataclass(frozen=True)
class ExplanationDelta:
    feature: str
    contribution_a: float
    contribution_b: float
    delta: float


@dataclass(frozen=True)
class ComparisonResult:
    deltas: list[ExplanationDelta]
    similarity: float | None
    explanation: str


def compare_explanations(
    a: list[FeatureContributionPoint], b: list[FeatureContributionPoint]
) -> ComparisonResult:
    """Compares two predictions' SHAP attributions feature by feature via
    the cosine similarity of their contribution vectors: 1 = the model
    reasoned identically, 0 = unrelated reasoning, negative = opposite
    reasoning (the same feature pushed the decision the other way)."""
    a_map = {c.feature: c.contribution for c in a}
    b_map = {c.feature: c.contribution for c in b}
    features = sorted(set(a_map) | set(b_map))

    deltas = sorted(
        (
            ExplanationDelta(
                feature=f,
                contribution_a=a_map.get(f, 0.0),
                contribution_b=b_map.get(f, 0.0),
                delta=b_map.get(f, 0.0) - a_map.get(f, 0.0),
            )
            for f in features
        ),
        key=lambda d: abs(d.delta),
        reverse=True,
    )

    dot = sum(a_map.get(f, 0.0) * b_map.get(f, 0.0) for f in features)
    norm_a = math.sqrt(sum(v**2 for v in a_map.values()))
    norm_b = math.sqrt(sum(v**2 for v in b_map.values()))
    similarity = dot / (norm_a * norm_b) if norm_a > 0 and norm_b > 0 else None

    if similarity is None:
        tone = "indéterminée (historique insuffisant)"
    elif similarity > 0.7:
        tone = "très proche — raisonnement quasi identique"
    elif similarity < 0.3:
        tone = "sensiblement différente"
    else:
        tone = "partiellement différente"

    return ComparisonResult(
        deltas=deltas,
        similarity=round(similarity, 4) if similarity is not None else None,
        explanation=(
            "Similarité cosinus des deux explications SHAP : "
            + (f"{similarity:+.2f} — {tone}." if similarity is not None else f"{tone}.")
        ),
    )
