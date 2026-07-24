from src.modules.drift_detection.domain.drift import (
    concept_drift,
    data_drift_report,
    label_drift,
    overall_severity,
    population_stability_index,
)


def test_psi_none_with_insufficient_history():
    assert population_stability_index([1.0, 2.0], [1.0, 2.0], bins=10) is None


def test_psi_near_zero_for_identical_distributions():
    reference = [float(i % 10) for i in range(200)]
    recent = [float(i % 10) for i in range(200)]
    psi = population_stability_index(reference, recent, bins=10)
    assert psi is not None
    assert psi < 0.01


def test_psi_high_for_shifted_distribution():
    reference = [float(i % 10) for i in range(200)]
    recent = [float(50 + i % 10) for i in range(200)]
    psi = population_stability_index(reference, recent, bins=10)
    assert psi is not None
    assert psi > 0.25


def test_data_drift_report_flags_shifted_feature_only():
    stable_col = [float(i % 10) for i in range(200)]
    shifted_col = [float(i % 10) for i in range(200)]
    reference_rows = [[stable_col[i], shifted_col[i]] for i in range(200)]
    recent_rows = [[stable_col[i], shifted_col[i] + 50] for i in range(200)]

    reports = data_drift_report(reference_rows, recent_rows, ["stable_feat", "shifted_feat"])
    by_name = {r.feature: r for r in reports}
    assert by_name["stable_feat"].severity == "stable"
    assert by_name["shifted_feat"].severity == "significative"


def test_label_drift_stable_when_rates_match():
    reference = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
    recent = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
    drift = label_drift(reference, recent)
    assert drift.severity == "stable"
    assert drift.delta == 0.0


def test_label_drift_significant_on_large_shift():
    reference = [1] * 8 + [0] * 2  # 80% up
    recent = [1] * 2 + [0] * 8  # 20% up
    drift = label_drift(reference, recent)
    assert drift.severity == "significative"
    assert drift.delta is not None and drift.delta < 0


def test_label_drift_indeterminate_when_empty():
    drift = label_drift([], [1, 0])
    assert drift.severity == "indéterminé"


def test_concept_drift_indeterminate_with_too_few_samples():
    result = concept_drift(0.6, 0.4, 5, 5, min_samples=10)
    assert result.severity == "indéterminé"


def test_concept_drift_stable_when_accuracy_holds():
    result = concept_drift(0.62, 0.60, 50, 50, min_samples=10)
    assert result.severity == "stable"


def test_concept_drift_significant_on_large_accuracy_drop():
    result = concept_drift(0.65, 0.45, 50, 50, min_samples=10)
    assert result.severity == "significative"
    assert result.delta is not None and result.delta < 0


def test_overall_severity_picks_worst():
    assert overall_severity(["stable", "modérée", "stable"]) == "modérée"
    assert overall_severity(["stable", "significative", "modérée"]) == "significative"
    assert overall_severity(["stable", "stable"]) == "stable"
    assert overall_severity(["indéterminé", "indéterminé"]) == "indéterminé"
    assert overall_severity([]) == "indéterminé"
