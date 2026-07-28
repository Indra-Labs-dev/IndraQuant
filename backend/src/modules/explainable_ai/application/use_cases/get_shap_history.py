from src.modules.explainable_ai.application.dto import (
    FeatureContributionDto,
    ShapHistoryResponse,
    ShapSnapshotDto,
)
from src.modules.explainable_ai.application.shap_serialization import parse_contributions
from src.modules.prediction_engine.infrastructure.sqlalchemy_repository import (
    SqlAlchemyPredictionRepository,
)
from src.shared.kernel.errors import AppError

_DEFAULT_LIMIT = 30
_CACHE_TTL_SECONDS = 3_600


class GetShapHistoryUseCase:
    """Historique SHAP (docs/roadmap #15): the persisted SHAP contributions
    (migration 006) for the most recent predictions on an instrument —
    predictions made before this feature shipped simply have no
    contributions to show (no retroactive backfill, same policy as
    ADR-029's non-retroactive columns).

    Cached keyed on the latest prediction id for the pair (ADR-026): a
    new prediction changes that id, so the cache can never serve a
    stale snapshot, while repeated dashboard polls between predictions
    skip the JSON-parsing pass over every record entirely."""

    def __init__(self, predictions: SqlAlchemyPredictionRepository, cache=None) -> None:
        self._predictions = predictions
        self._cache = cache

    async def execute(
        self, instrument_id: int, timeframe: str, limit: int = _DEFAULT_LIMIT
    ) -> ShapHistoryResponse:
        latest_id = await self._predictions.get_latest_id(instrument_id, timeframe)
        cache_key = f"shap-history:{instrument_id}:{timeframe}:{limit}:{latest_id}"
        if self._cache is not None:
            try:
                cached = await self._cache.get(cache_key)
                if cached:
                    return ShapHistoryResponse.model_validate_json(cached)
            except Exception:
                pass

        records = await self._predictions.list_recent(instrument_id, timeframe, limit)
        snapshots = []
        for record in records:
            contributions = parse_contributions(record.shap_json)
            if not contributions:
                continue
            snapshots.append(
                ShapSnapshotDto(
                    prediction_id=record.id,
                    as_of=record.as_of,
                    predicted_direction=record.predicted_direction,
                    contributions=[
                        FeatureContributionDto(
                            feature=c.feature, value=c.value, contribution=c.contribution
                        )
                        for c in contributions
                    ],
                )
            )

        if not snapshots and records:
            raise AppError(
                "no_shap_history",
                "Aucune prédiction avec SHAP persisté pour cet instrument — "
                "seules les prédictions faites après la mise à jour Explainable "
                "AI en disposent.",
                404,
            )

        response = ShapHistoryResponse(
            instrument_id=instrument_id,
            timeframe=timeframe,
            snapshots=snapshots,
            explanation=(
                f"{len(snapshots)} instantané(s) SHAP disponibles sur "
                f"{len(records)} prédiction(s) récente(s)."
            ),
        )
        if self._cache is not None:
            try:
                await self._cache.set(cache_key, response.model_dump_json(), ex=_CACHE_TTL_SECONDS)
            except Exception:
                pass
        return response
