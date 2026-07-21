from fastapi import APIRouter, Depends

from src.composition_root import get_current_user
from src.modules.auth.application.dto import UserProfile
from src.modules.strategy_builder.application.use_cases.list_strategies import (
    ListStrategiesUseCase,
    StrategiesResponse,
)

router = APIRouter(prefix="/strategies", tags=["strategy-builder"])


@router.get("")
def list_strategies(
    _: UserProfile = Depends(get_current_user),
) -> StrategiesResponse:
    return ListStrategiesUseCase().execute()
