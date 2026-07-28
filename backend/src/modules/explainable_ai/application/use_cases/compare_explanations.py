from src.modules.explainable_ai.application.dto import (
    CompareExplanationsResponse,
    ExplanationDeltaDto,
)
from src.modules.explainable_ai.application.shap_serialization import parse_contributions
from src.modules.explainable_ai.domain.analysis import compare_explanations
from src.modules.prediction_engine.infrastructure.sqlalchemy_repository import (
    SqlAlchemyPredictionRepository,
)
from src.shared.kernel.errors import NotFoundError

# Past predictions never change once persisted, so a comparison between two
# fixed ids is safe to cache indefinitely — no invalidation logic needed.
_CACHE_TTL_SECONDS = 86_400


class CompareExplanationsUseCase:
    """Comparaison des explications (docs/roadmap #15): places two past
    predictions' SHAP attributions side by side and reports how similar
    the model's reasoning was, via cosine similarity of the contribution
    vectors."""

    def __init__(self, predictions: SqlAlchemyPredictionRepository, cache=None) -> None:
        self._predictions = predictions
        self._cache = cache

    async def execute(self, prediction_id_a: int, prediction_id_b: int) -> CompareExplanationsResponse:
        # Not normalized by min/max: a vs b and b vs a report deltas with
        # opposite signs, so swapping the request order must miss the cache.
        cache_key = f"compare-explanations:{prediction_id_a}:{prediction_id_b}"
        if self._cache is not None:
            try:
                cached = await self._cache.get(cache_key)
                if cached:
                    return CompareExplanationsResponse.model_validate_json(cached)
            except Exception:
                pass

        record_a = await self._predictions.get(prediction_id_a)
        record_b = await self._predictions.get(prediction_id_b)
        if record_a is None:
            raise NotFoundError("prediction_not_found", f"Prédiction {prediction_id_a} introuvable.")
        if record_b is None:
            raise NotFoundError("prediction_not_found", f"Prédiction {prediction_id_b} introuvable.")

        contributions_a = parse_contributions(record_a.shap_json)
        contributions_b = parse_contributions(record_b.shap_json)

        result = compare_explanations(contributions_a, contributions_b)

        response = CompareExplanationsResponse(
            prediction_id_a=prediction_id_a,
            prediction_id_b=prediction_id_b,
            similarity=result.similarity,
            deltas=[
                ExplanationDeltaDto(
                    feature=d.feature,
                    contribution_a=d.contribution_a,
                    contribution_b=d.contribution_b,
                    delta=d.delta,
                )
                for d in result.deltas
            ],
            explanation=result.explanation,
        )
        if self._cache is not None:
            try:
                await self._cache.set(cache_key, response.model_dump_json(), ex=_CACHE_TTL_SECONDS)
            except Exception:
                pass
        return response
