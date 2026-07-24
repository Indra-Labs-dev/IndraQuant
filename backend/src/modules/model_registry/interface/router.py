from fastapi import APIRouter, Depends, Query

from src.composition_root import (
    get_current_user,
    get_model_registry_use_case,
    get_rollback_model_use_case,
    get_run_ab_test_use_case,
)
from src.modules.auth.application.dto import UserProfile
from src.modules.model_registry.application.dto import (
    AbTestResponse,
    ModelRegistryResponse,
    RollbackResponse,
)
from src.modules.model_registry.application.use_cases.get_model_registry import (
    GetModelRegistryUseCase,
)
from src.modules.model_registry.application.use_cases.rollback_model import (
    RollbackModelUseCase,
)
from src.modules.model_registry.application.use_cases.run_ab_test import RunAbTestUseCase

router = APIRouter(tags=["model-registry"])


@router.get("/instruments/{instrument_id}/model-registry")
def get_model_registry(
    instrument_id: int,
    timeframe: str = Query(default="1h"),
    limit: int = Query(default=50, ge=1, le=200),
    _: UserProfile = Depends(get_current_user),
    use_case: GetModelRegistryUseCase = Depends(get_model_registry_use_case),
) -> ModelRegistryResponse:
    return use_case.execute(instrument_id, timeframe, limit)


@router.post("/instruments/{instrument_id}/model-registry/rollback")
def rollback_model(
    instrument_id: int,
    version: int = Query(),
    timeframe: str = Query(default="1h"),
    _: UserProfile = Depends(get_current_user),
    use_case: RollbackModelUseCase = Depends(get_rollback_model_use_case),
) -> RollbackResponse:
    return use_case.execute(instrument_id, timeframe, version)


@router.get("/instruments/{instrument_id}/model-registry/ab-test")
def run_ab_test(
    instrument_id: int,
    timeframe: str = Query(default="1h"),
    _: UserProfile = Depends(get_current_user),
    use_case: RunAbTestUseCase = Depends(get_run_ab_test_use_case),
) -> AbTestResponse:
    return use_case.execute(instrument_id, timeframe)
