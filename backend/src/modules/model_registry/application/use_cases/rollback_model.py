from src.modules.model_registry.application.dto import RollbackResponse
from src.modules.model_registry.infrastructure.sqlalchemy_repository import (
    SqlAlchemyModelVersionRepository,
)
from src.shared.kernel.errors import AppError


class RollbackModelUseCase:
    """Rollback (docs/roadmap #8), adapted to a train-on-the-fly engine:
    there is no serialized model artifact to restore, so this reinstates a
    prior *version*'s model type as champion for reporting/monitoring, and
    marks every version registered after it as rolled back — an audit
    trail, not a parameter restore. The next genuine retrain still trains
    fresh on current data, as it always does."""

    def __init__(self, versions: SqlAlchemyModelVersionRepository) -> None:
        self._versions = versions

    async def execute(self, instrument_id: int, timeframe: str, version: int) -> RollbackResponse:
        target = await self._versions.get_by_version(instrument_id, timeframe, version)
        if target is None:
            raise AppError(
                "model_version_not_found",
                f"Version {version} introuvable pour cet instrument/unité de temps.",
                404,
            )

        await self._versions.set_champion(instrument_id, timeframe, version)
        await self._versions.mark_rolled_back_after(instrument_id, timeframe, version)

        return RollbackResponse(
            instrument_id=instrument_id,
            timeframe=timeframe,
            champion_version=version,
            explanation=(
                f"Version {version} ({target.champion_model_type}) réinstaurée comme "
                "champion. Les versions enregistrées après elle sont marquées "
                "« rolled back » à titre d'audit — le prochain entraînement réel "
                "repartira toutefois des données actuelles, il n'y a pas de "
                "modèle sérialisé à restaurer."
            ),
        )
