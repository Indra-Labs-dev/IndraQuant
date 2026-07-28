from src.modules.model_registry.application.dto import AbTestResponse
from src.modules.model_registry.domain.registry import compare_model_types
from src.modules.model_registry.infrastructure.sqlalchemy_repository import (
    SqlAlchemyModelVersionRepository,
)
from src.shared.kernel.errors import AppError

_DEFAULT_LIMIT = 200
_MIN_RELIABLE_SAMPLES = 20


class RunAbTestUseCase:
    """A/B Testing (docs/roadmap #8): compares XGBoost against logistic
    regression's historical edge over the naive baseline, across every
    registered retrain, using bootstrap confidence intervals (docs/roadmap
    #6) rather than a single-point accuracy comparison."""

    def __init__(self, versions: SqlAlchemyModelVersionRepository) -> None:
        self._versions = versions

    async def execute(
        self, instrument_id: int, timeframe: str, limit: int = _DEFAULT_LIMIT
    ) -> AbTestResponse:
        records = await self._versions.list_versions(instrument_id, timeframe, limit)
        if not records:
            raise AppError(
                "no_model_versions",
                "Aucun modèle encore enregistré pour cet instrument/unité de temps.",
                404,
            )

        xgboost_edges = [
            float(r.xgboost_accuracy) - float(r.baseline_accuracy) for r in records
        ]
        logistic_regression_edges = [
            float(r.logistic_regression_accuracy) - float(r.baseline_accuracy) for r in records
        ]

        result = compare_model_types(xgboost_edges, logistic_regression_edges)
        explanation = result.explanation
        if len(records) < _MIN_RELIABLE_SAMPLES:
            explanation += (
                f" Attention : seulement {len(records)} version(s) enregistrée(s) "
                f"(minimum {_MIN_RELIABLE_SAMPLES} recommandé pour un intervalle "
                "bootstrap fiable) — ce résultat n'est encore qu'indicatif."
            )

        return AbTestResponse(
            instrument_id=instrument_id,
            timeframe=timeframe,
            winner=result.winner,
            xgboost_edge_mean=result.xgboost_edge[0],
            xgboost_edge_ci_low=result.xgboost_edge[1],
            xgboost_edge_ci_high=result.xgboost_edge[2],
            logistic_regression_edge_mean=result.logistic_regression_edge[0],
            logistic_regression_edge_ci_low=result.logistic_regression_edge[1],
            logistic_regression_edge_ci_high=result.logistic_regression_edge[2],
            sample_size=len(records),
            explanation=explanation,
        )
