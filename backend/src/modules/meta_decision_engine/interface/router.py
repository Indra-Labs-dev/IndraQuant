from fastapi import APIRouter, Depends, Query

from src.composition_root import get_current_user, get_meta_decision_use_case
from src.modules.auth.application.dto import UserProfile
from src.modules.meta_decision_engine.application.dto import MetaDecisionResponse
from src.modules.meta_decision_engine.application.use_cases.get_meta_decision import (
    GetMetaDecisionUseCase,
)

router = APIRouter(tags=["meta-decision"])


@router.get("/instruments/{instrument_id}/meta-decision")
def get_meta_decision(
    instrument_id: int,
    timeframe: str = Query(default="1h"),
    _: UserProfile = Depends(get_current_user),
    use_case: GetMetaDecisionUseCase = Depends(get_meta_decision_use_case),
) -> MetaDecisionResponse:
    return use_case.execute(instrument_id, timeframe)
