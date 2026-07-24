"""Drift Detection (docs/roadmap #6): Data Drift (feature distributions
shift over time), Concept Drift (the Prediction Engine's real, verified
accuracy degrades — the relationship between features and outcome has
changed) and Label Drift (the base rate of the target itself shifts).

The system trains on the fly rather than persisting a model (ADR-017), so
drift here is measured by comparing two time windows (an older "reference"
half and a "recent" half) rather than a fixed training-time baseline.
Every verdict traces back to a named, standard statistic — no black box.
"""

import math
from dataclasses import dataclass

_PSI_MODERATE = 0.1
_PSI_SIGNIFICANT = 0.25
_LABEL_MODERATE = 0.07
_LABEL_SIGNIFICANT = 0.15
_ACCURACY_MODERATE = 0.07
_ACCURACY_SIGNIFICANT = 0.15


@dataclass(frozen=True)
class FeatureDrift:
    feature: str
    psi: float | None
    severity: str  # "stable" | "modérée" | "significative" | "indéterminé"
    explanation: str


@dataclass(frozen=True)
class LabelDrift:
    reference_up_rate: float | None
    recent_up_rate: float | None
    delta: float | None
    severity: str
    explanation: str


@dataclass(frozen=True)
class ConceptDrift:
    reference_accuracy: float | None
    recent_accuracy: float | None
    reference_n: int
    recent_n: int
    delta: float | None
    severity: str
    explanation: str


def population_stability_index(
    reference: list[float], recent: list[float], bins: int = 10
) -> float | None:
    """Standard PSI: bins the reference distribution into deciles, then
    measures how much the proportion of observations per bin shifted in
    the recent window — PSI = sum((recent% - ref%) * ln(recent% / ref%)).
    Industry-standard thresholds: < 0.1 stable, 0.1-0.25 moderate,
    > 0.25 significant."""
    if len(reference) < bins * 2 or len(recent) < bins:
        return None

    sorted_ref = sorted(reference)
    edges = [
        sorted_ref[int(round(i * (len(sorted_ref) - 1) / bins))]
        for i in range(1, bins)
    ]

    def bucket_counts(values: list[float]) -> list[int]:
        counts = [0] * bins
        for value in values:
            idx = 0
            while idx < len(edges) and value > edges[idx]:
                idx += 1
            counts[idx] += 1
        return counts

    ref_counts = bucket_counts(reference)
    recent_counts = bucket_counts(recent)
    psi = 0.0
    for ref_count, recent_count in zip(ref_counts, recent_counts):
        ref_pct = max(ref_count / len(reference), 1e-4)
        recent_pct = max(recent_count / len(recent), 1e-4)
        psi += (recent_pct - ref_pct) * math.log(recent_pct / ref_pct)
    return psi


def _psi_severity(psi: float) -> str:
    if psi >= _PSI_SIGNIFICANT:
        return "significative"
    if psi >= _PSI_MODERATE:
        return "modérée"
    return "stable"


def data_drift_report(
    reference_rows: list[list[float]],
    recent_rows: list[list[float]],
    feature_names: list[str],
) -> list[FeatureDrift]:
    reports: list[FeatureDrift] = []
    for i, name in enumerate(feature_names):
        reference_col = [row[i] for row in reference_rows]
        recent_col = [row[i] for row in recent_rows]
        psi = population_stability_index(reference_col, recent_col)
        if psi is None:
            reports.append(
                FeatureDrift(
                    name,
                    None,
                    "indéterminé",
                    "Historique insuffisant pour évaluer la dérive de cette feature.",
                )
            )
            continue
        severity = _psi_severity(psi)
        reports.append(
            FeatureDrift(
                name,
                round(psi, 4),
                severity,
                f"PSI = {psi:.3f} ({severity})"
                + (
                    " — distribution stable entre les deux périodes."
                    if severity == "stable"
                    else " — changement modéré de distribution, à surveiller."
                    if severity == "modérée"
                    else " — changement important de distribution, le modèle voit "
                    "des données significativement différentes de son historique."
                ),
            )
        )
    return reports


def label_drift(reference_labels: list[int], recent_labels: list[int]) -> LabelDrift:
    if not reference_labels or not recent_labels:
        return LabelDrift(
            None,
            None,
            None,
            "indéterminé",
            "Historique insuffisant pour évaluer la dérive de label.",
        )

    reference_rate = sum(reference_labels) / len(reference_labels)
    recent_rate = sum(recent_labels) / len(recent_labels)
    delta = recent_rate - reference_rate
    severity = (
        "significative"
        if abs(delta) >= _LABEL_SIGNIFICANT
        else "modérée"
        if abs(delta) >= _LABEL_MODERATE
        else "stable"
    )
    return LabelDrift(
        round(reference_rate, 4),
        round(recent_rate, 4),
        round(delta, 4),
        severity,
        f"Taux de bougies haussières : {reference_rate * 100:.1f} % (référence) → "
        f"{recent_rate * 100:.1f} % (récent), écart {delta * 100:+.1f} points — {severity}."
        + (
            " Le marché a probablement changé de régime directionnel."
            if severity != "stable"
            else ""
        ),
    )


def concept_drift(
    reference_accuracy: float | None,
    recent_accuracy: float | None,
    reference_n: int,
    recent_n: int,
    min_samples: int = 10,
) -> ConceptDrift:
    if (
        reference_accuracy is None
        or recent_accuracy is None
        or reference_n < min_samples
        or recent_n < min_samples
    ):
        return ConceptDrift(
            reference_accuracy,
            recent_accuracy,
            reference_n,
            recent_n,
            None,
            "indéterminé",
            f"Pas assez de prédictions vérifiées pour évaluer la dérive de concept "
            f"(minimum {min_samples} par période, {reference_n} en référence et "
            f"{recent_n} récentes disponibles).",
        )

    delta = recent_accuracy - reference_accuracy
    severity = (
        "significative"
        if delta <= -_ACCURACY_SIGNIFICANT
        else "modérée"
        if delta <= -_ACCURACY_MODERATE
        else "stable"
    )
    return ConceptDrift(
        round(reference_accuracy, 4),
        round(recent_accuracy, 4),
        reference_n,
        recent_n,
        round(delta, 4),
        severity,
        f"Précision réellement vérifiée : {reference_accuracy * 100:.1f} % (sur "
        f"{reference_n} prédictions anciennes) → {recent_accuracy * 100:.1f} % "
        f"(sur {recent_n} prédictions récentes), écart {delta * 100:+.1f} points — {severity}."
        + (
            " La relation entre les features et le résultat semble s'être "
            "dégradée — envisager un réentraînement plus fréquent ou une revue "
            "des features."
            if severity != "stable"
            else ""
        ),
    )


def overall_severity(severities: list[str]) -> str:
    """The worst verdict wins ("significative" > "modérée" > "stable"),
    with "indéterminé" only when every input is itself indéterminé."""
    if not severities:
        return "indéterminé"
    if "significative" in severities:
        return "significative"
    if "modérée" in severities:
        return "modérée"
    if "stable" in severities:
        return "stable"
    return "indéterminé"
