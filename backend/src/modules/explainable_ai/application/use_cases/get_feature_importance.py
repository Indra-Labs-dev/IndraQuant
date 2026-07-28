from src.modules.explainable_ai.application.dto import (
    FeatureEvolutionResponse,
    FeatureTimePointDto,
    GlobalImportanceItemDto,
    GlobalImportanceResponse,
)
from src.modules.explainable_ai.application.shap_serialization import parse_contributions
from src.modules.explainable_ai.domain.analysis import (
    aggregate_feature_importance,
    feature_importance_over_time,
)
from src.modules.prediction_engine.infrastructure.sqlalchemy_repository import (
    SqlAlchemyPredictionRepository,
)
from src.shared.kernel.errors import AppError

_DEFAULT_LIMIT = 50
_CACHE_TTL_SECONDS = 3_600


class GetGlobalFeatureImportanceUseCase:
    """Importance globale (docs/roadmap #15): ranks features by their mean
    absolute SHAP contribution across many past predictions, instead of
    reading importance off a single prediction's explanation.

    Cached keyed on the latest prediction id (ADR-026 discipline) so a
    new prediction always invalidates it, never a blind TTL."""

    def __init__(self, predictions: SqlAlchemyPredictionRepository, cache=None) -> None:
        self._predictions = predictions
        self._cache = cache

    async def execute(
        self, instrument_id: int, timeframe: str, limit: int = _DEFAULT_LIMIT
    ) -> GlobalImportanceResponse:
        latest_id = await self._predictions.get_latest_id(instrument_id, timeframe)
        cache_key = f"feature-importance:{instrument_id}:{timeframe}:{limit}:{latest_id}"
        if self._cache is not None:
            try:
                cached = await self._cache.get(cache_key)
                if cached:
                    return GlobalImportanceResponse.model_validate_json(cached)
            except Exception:
                pass

        records = await self._predictions.list_recent(instrument_id, timeframe, limit)
        history = [
            contributions
            for record in records
            if (contributions := parse_contributions(record.shap_json))
        ]
        if not history:
            raise AppError(
                "no_shap_history",
                "Aucune prédiction avec SHAP persisté pour cet instrument.",
                404,
            )

        ranking = aggregate_feature_importance(history)
        response = GlobalImportanceResponse(
            instrument_id=instrument_id,
            timeframe=timeframe,
            sample_size=len(history),
            items=[
                GlobalImportanceItemDto(
                    feature=item.feature,
                    mean_absolute_contribution=item.mean_absolute_contribution,
                    rank=item.rank,
                )
                for item in ranking
            ],
            explanation=(
                f"Importance moyenne (valeur SHAP absolue) sur {len(history)} "
                f"prédiction(s) récente(s) — {ranking[0].feature if ranking else 'n/a'} "
                "est la feature la plus influente en moyenne, pas nécessairement "
                "sur la toute dernière prédiction."
            ),
        )
        if self._cache is not None:
            try:
                await self._cache.set(cache_key, response.model_dump_json(), ex=_CACHE_TTL_SECONDS)
            except Exception:
                pass
        return response


class GetFeatureEvolutionUseCase:
    """Évolution temporelle (docs/roadmap #15): comment la contribution
    SHAP d'une feature donnée évolue au fil des prédictions passées.

    Cached keyed on the latest prediction id (ADR-026 discipline)."""

    def __init__(self, predictions: SqlAlchemyPredictionRepository, cache=None) -> None:
        self._predictions = predictions
        self._cache = cache

    async def execute(
        self,
        instrument_id: int,
        timeframe: str,
        feature: str,
        limit: int = _DEFAULT_LIMIT,
    ) -> FeatureEvolutionResponse:
        latest_id = await self._predictions.get_latest_id(instrument_id, timeframe)
        cache_key = f"feature-evolution:{instrument_id}:{timeframe}:{feature}:{limit}:{latest_id}"
        if self._cache is not None:
            try:
                cached = await self._cache.get(cache_key)
                if cached:
                    return FeatureEvolutionResponse.model_validate_json(cached)
            except Exception:
                pass

        records = await self._predictions.list_recent(instrument_id, timeframe, limit)
        history = [
            (record.as_of, contributions)
            for record in records
            if (contributions := parse_contributions(record.shap_json))
        ]
        points = feature_importance_over_time(history, feature)
        if not points:
            raise AppError(
                "no_shap_history",
                f"Aucune contribution SHAP trouvée pour la feature « {feature} ».",
                404,
            )

        response = FeatureEvolutionResponse(
            instrument_id=instrument_id,
            timeframe=timeframe,
            feature=feature,
            points=[
                FeatureTimePointDto(as_of=p.as_of, contribution=p.contribution)
                for p in points
            ],
            explanation=(
                f"{len(points)} valeur(s) SHAP pour « {feature} » sur les "
                "prédictions récentes, dans l'ordre chronologique."
            ),
        )
        if self._cache is not None:
            try:
                await self._cache.set(cache_key, response.model_dump_json(), ex=_CACHE_TTL_SECONDS)
            except Exception:
                pass
        return response
