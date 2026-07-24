from src.modules.model_registry.application.dto import ModelRegistryResponse, ModelVersionDto
from src.modules.model_registry.infrastructure.sqlalchemy_repository import (
    SqlAlchemyModelVersionRepository,
)
from src.shared.kernel.errors import AppError

_DEFAULT_LIMIT = 50


class GetModelRegistryUseCase:
    """Monitoring (docs/roadmap #8): the version history and accuracy trend
    for an instrument/timeframe pair — which model type has been winning
    the champion/challenger comparison across retrains, and whether
    accuracy is drifting."""

    def __init__(self, versions: SqlAlchemyModelVersionRepository) -> None:
        self._versions = versions

    def execute(
        self, instrument_id: int, timeframe: str, limit: int = _DEFAULT_LIMIT
    ) -> ModelRegistryResponse:
        records = self._versions.list_versions(instrument_id, timeframe, limit)
        if not records:
            raise AppError(
                "no_model_versions",
                "Aucun modèle encore enregistré pour cet instrument/unité de temps "
                "— au moins une prédiction doit avoir entraîné un modèle.",
                404,
            )

        champion = next((r for r in records if r.is_champion), records[0])
        return ModelRegistryResponse(
            instrument_id=instrument_id,
            timeframe=timeframe,
            versions=[
                ModelVersionDto(
                    version=r.version,
                    as_of=r.as_of,
                    champion_model_type=r.champion_model_type,
                    xgboost_accuracy=float(r.xgboost_accuracy),
                    logistic_regression_accuracy=float(r.logistic_regression_accuracy),
                    ensemble_accuracy=float(r.ensemble_accuracy),
                    baseline_accuracy=float(r.baseline_accuracy),
                    training_rows=r.training_rows,
                    is_champion=r.is_champion,
                    rolled_back=r.rolled_back,
                )
                for r in records
            ],
            explanation=(
                f"{len(records)} version(s) enregistrée(s) sur les {limit} plus "
                f"récentes. Champion actuel : version {champion.version} "
                f"({champion.champion_model_type}, précision "
                f"{max(float(champion.xgboost_accuracy), float(champion.logistic_regression_accuracy)) * 100:.1f} %)."
            ),
        )
