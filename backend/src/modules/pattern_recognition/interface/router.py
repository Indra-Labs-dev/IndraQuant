from datetime import datetime

from fastapi import APIRouter, Depends, Query

from src.composition_root import get_current_user, get_detect_patterns_use_case
from src.modules.auth.application.dto import UserProfile
from src.modules.pattern_recognition.application.dto import PatternsResponse
from src.modules.pattern_recognition.application.use_cases.detect_patterns import (
    DetectPatternsUseCase,
)

router = APIRouter(prefix="/instruments", tags=["pattern-recognition"])


@router.get("/{instrument_id}/patterns")
async def get_patterns(
    instrument_id: int,
    timeframe: str = Query(),
    from_: datetime = Query(alias="from"),
    to: datetime = Query(),
    limit: int = Query(default=500, ge=1, le=5000),
    _: UserProfile = Depends(get_current_user),
    use_case: DetectPatternsUseCase = Depends(get_detect_patterns_use_case),
) -> PatternsResponse:
    return await use_case.execute(instrument_id, timeframe, from_, to, limit)
