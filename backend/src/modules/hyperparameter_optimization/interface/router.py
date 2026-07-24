from fastapi import APIRouter, Depends

from src.composition_root import (
    get_current_user,
    get_optimize_model_use_case,
    get_optimize_strategy_use_case,
)
from src.modules.auth.application.dto import UserProfile
from src.modules.hyperparameter_optimization.application.dto import (
    HpoResultDto,
    OptimizeModelRequest,
    OptimizeStrategyRequest,
)
from src.modules.hyperparameter_optimization.application.use_cases.optimize_model import (
    OptimizeModelHyperparametersUseCase,
)
from src.modules.hyperparameter_optimization.application.use_cases.optimize_strategy import (
    OptimizeStrategyUseCase,
)

router = APIRouter(prefix="/optimization", tags=["hyperparameter-optimization"])


@router.post("/strategy")
def optimize_strategy(
    request: OptimizeStrategyRequest,
    _: UserProfile = Depends(get_current_user),
    use_case: OptimizeStrategyUseCase = Depends(get_optimize_strategy_use_case),
) -> HpoResultDto:
    return use_case.execute(request)


@router.post("/model")
def optimize_model(
    request: OptimizeModelRequest,
    _: UserProfile = Depends(get_current_user),
    use_case: OptimizeModelHyperparametersUseCase = Depends(get_optimize_model_use_case),
) -> HpoResultDto:
    return use_case.execute(request)
