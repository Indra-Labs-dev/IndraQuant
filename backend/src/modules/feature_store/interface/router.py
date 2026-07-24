from fastapi import APIRouter, Depends, Query

from src.composition_root import get_current_user, get_feature_vector_use_case
from src.modules.auth.application.dto import UserProfile
from src.modules.feature_store.application.dto import FeatureVectorResponse
from src.modules.feature_store.application.use_cases.get_features import (
    GetFeatureVectorUseCase,
)

router = APIRouter(tags=["feature-store"])


@router.get("/instruments/{instrument_id}/features")
def get_features(
    instrument_id: int,
    timeframe: str = Query(default="1h"),
    _: UserProfile = Depends(get_current_user),
    use_case: GetFeatureVectorUseCase = Depends(get_feature_vector_use_case),
) -> FeatureVectorResponse:
    return use_case.execute(instrument_id, timeframe)
