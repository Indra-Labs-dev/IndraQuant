from fastapi import APIRouter, Depends, Query

from src.composition_root import (
    get_compare_explanations_use_case,
    get_current_user,
    get_feature_evolution_use_case,
    get_global_feature_importance_use_case,
    get_shap_history_use_case,
)
from src.modules.auth.application.dto import UserProfile
from src.modules.explainable_ai.application.dto import (
    CompareExplanationsResponse,
    FeatureEvolutionResponse,
    GlobalImportanceResponse,
    ShapHistoryResponse,
)
from src.modules.explainable_ai.application.use_cases.compare_explanations import (
    CompareExplanationsUseCase,
)
from src.modules.explainable_ai.application.use_cases.get_feature_importance import (
    GetFeatureEvolutionUseCase,
    GetGlobalFeatureImportanceUseCase,
)
from src.modules.explainable_ai.application.use_cases.get_shap_history import (
    GetShapHistoryUseCase,
)

router = APIRouter(tags=["explainable-ai"])


@router.get("/instruments/{instrument_id}/shap-history")
def get_shap_history(
    instrument_id: int,
    timeframe: str = Query(default="1h"),
    limit: int = Query(default=30, ge=1, le=200),
    _: UserProfile = Depends(get_current_user),
    use_case: GetShapHistoryUseCase = Depends(get_shap_history_use_case),
) -> ShapHistoryResponse:
    return use_case.execute(instrument_id, timeframe, limit)


@router.get("/instruments/{instrument_id}/feature-importance")
def get_feature_importance(
    instrument_id: int,
    timeframe: str = Query(default="1h"),
    limit: int = Query(default=50, ge=1, le=200),
    _: UserProfile = Depends(get_current_user),
    use_case: GetGlobalFeatureImportanceUseCase = Depends(
        get_global_feature_importance_use_case
    ),
) -> GlobalImportanceResponse:
    return use_case.execute(instrument_id, timeframe, limit)


@router.get("/instruments/{instrument_id}/feature-evolution")
def get_feature_evolution(
    instrument_id: int,
    feature: str = Query(),
    timeframe: str = Query(default="1h"),
    limit: int = Query(default=50, ge=1, le=200),
    _: UserProfile = Depends(get_current_user),
    use_case: GetFeatureEvolutionUseCase = Depends(get_feature_evolution_use_case),
) -> FeatureEvolutionResponse:
    return use_case.execute(instrument_id, timeframe, feature, limit)


@router.get("/predictions/{prediction_id_a}/compare/{prediction_id_b}")
def compare_explanations(
    prediction_id_a: int,
    prediction_id_b: int,
    _: UserProfile = Depends(get_current_user),
    use_case: CompareExplanationsUseCase = Depends(get_compare_explanations_use_case),
) -> CompareExplanationsResponse:
    return use_case.execute(prediction_id_a, prediction_id_b)
