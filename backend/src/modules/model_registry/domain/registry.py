"""MLOps (docs/roadmap #8): Model Registry, Champion/Challenger and A/B
Testing — adapted honestly to how IndraQuant actually trains models.

There is no persisted model *binary* to version: the Prediction Engine
retrains on the fly whenever a new candle closes (ADR-026's cache-key-on-
as_of discipline), by design, so every prediction is always trained on the
freshest data. What genuinely can be — and is — versioned here is each
retrain *event*'s metadata (both models' test accuracy, the ensemble's
accuracy, the baseline, the training-set size) each time it actually
happens. "Champion/Challenger" therefore means: which of the two model
types (XGBoost vs logistic regression) is currently the more accurate one
for this instrument/timeframe, tracked across retrains. "Rollback" means
reinstating a prior version's model type as champion for reporting and
monitoring purposes — it cannot restore an old parameter set, since none
is kept, and this module says so rather than pretending otherwise."""

from dataclasses import dataclass

from src.modules.validation.domain.resampling import bootstrap_confidence_interval


@dataclass(frozen=True)
class ChampionDecision:
    model_type: str
    promoted: bool
    explanation: str


def decide_champion(
    xgboost_accuracy: float,
    logistic_regression_accuracy: float,
    prior_champion_accuracy: float | None,
) -> ChampionDecision:
    model_type = (
        "xgboost" if xgboost_accuracy >= logistic_regression_accuracy else "logistic_regression"
    )
    best_accuracy = max(xgboost_accuracy, logistic_regression_accuracy)

    if prior_champion_accuracy is None:
        return ChampionDecision(
            model_type,
            True,
            f"Premier modèle enregistré pour cet instrument/unité de temps — "
            f"{model_type} devient champion (précision {best_accuracy * 100:.1f} %).",
        )

    promoted = best_accuracy >= prior_champion_accuracy
    return ChampionDecision(
        model_type,
        promoted,
        f"{model_type} (précision {best_accuracy * 100:.1f} %) "
        + ("devient champion" if promoted else "reste challenger")
        + f" face au champion actuel (précision {prior_champion_accuracy * 100:.1f} %).",
    )


@dataclass(frozen=True)
class AbTestResult:
    winner: str
    xgboost_edge: tuple[float, float, float]
    logistic_regression_edge: tuple[float, float, float]
    explanation: str


def compare_model_types(
    xgboost_edges: list[float], logistic_regression_edges: list[float]
) -> AbTestResult:
    """Compares the two model types' historical edge over the naive
    baseline (accuracy - baseline_accuracy) across every registered
    retrain, via bootstrap confidence intervals (docs/roadmap #6 — reused,
    not duplicated) rather than a single-point accuracy comparison."""
    xgb = bootstrap_confidence_interval(xgboost_edges)
    lr = bootstrap_confidence_interval(logistic_regression_edges)

    if xgb.mean > lr.mean:
        winner = "xgboost"
    elif lr.mean > xgb.mean:
        winner = "logistic_regression"
    else:
        winner = "égalité"

    explanation = (
        f"Comparaison A/B sur {len(xgboost_edges)} version(s) enregistrée(s) "
        "(intervalles de confiance bootstrap sur l'avantage par rapport à la "
        f"référence naïve) : XGBoost {xgb.mean * 100:+.2f} % "
        f"[{xgb.ci_low * 100:+.2f} %, {xgb.ci_high * 100:+.2f} %] vs régression "
        f"logistique {lr.mean * 100:+.2f} % [{lr.ci_low * 100:+.2f} %, "
        f"{lr.ci_high * 100:+.2f} %]. Gagnant : {winner}."
    )
    return AbTestResult(
        winner,
        (xgb.mean, xgb.ci_low, xgb.ci_high),
        (lr.mean, lr.ci_low, lr.ci_high),
        explanation,
    )
