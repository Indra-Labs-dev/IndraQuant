from datetime import datetime
from decimal import Decimal

from src.modules.model_registry.domain.registry import decide_champion
from src.modules.model_registry.infrastructure.sqlalchemy_repository import (
    ModelVersionModel,
    SqlAlchemyModelVersionRepository,
)


class RegisterModelVersionUseCase:
    """Called once per genuine retrain (docs/roadmap #8 — Model Registry,
    Versioning, Champion/Challenger). Never called on a cache hit in
    `PredictDirectionUseCase`, since a cache hit means no new model was
    actually trained."""

    def __init__(self, versions: SqlAlchemyModelVersionRepository) -> None:
        self._versions = versions

    def execute(
        self,
        instrument_id: int,
        timeframe: str,
        as_of: datetime,
        xgboost_accuracy: float,
        logistic_regression_accuracy: float,
        ensemble_accuracy: float,
        baseline_accuracy: float,
        training_rows: int,
    ) -> None:
        champion = self._versions.get_current_champion(instrument_id, timeframe)
        prior_accuracy = (
            max(float(champion.xgboost_accuracy), float(champion.logistic_regression_accuracy))
            if champion is not None
            else None
        )
        decision = decide_champion(xgboost_accuracy, logistic_regression_accuracy, prior_accuracy)

        version = self._versions.next_version(instrument_id, timeframe)
        if decision.promoted:
            self._versions.clear_champion(instrument_id, timeframe)

        self._versions.add(
            ModelVersionModel(
                instrument_id=instrument_id,
                timeframe=timeframe,
                version=version,
                as_of=as_of.replace(tzinfo=None) if as_of.tzinfo else as_of,
                champion_model_type=decision.model_type,
                xgboost_accuracy=Decimal(str(round(xgboost_accuracy, 4))),
                logistic_regression_accuracy=Decimal(
                    str(round(logistic_regression_accuracy, 4))
                ),
                ensemble_accuracy=Decimal(str(round(ensemble_accuracy, 4))),
                baseline_accuracy=Decimal(str(round(baseline_accuracy, 4))),
                training_rows=training_rows,
                is_champion=decision.promoted,
            )
        )
