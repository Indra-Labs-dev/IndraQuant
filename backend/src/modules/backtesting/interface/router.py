from fastapi import APIRouter, Depends

from src.composition_root import (
    get_backtest_repository,
    get_current_user,
    get_run_backtest_use_case,
    get_walk_forward_use_case,
)
from src.modules.auth.application.dto import UserProfile
from src.modules.backtesting.application.dto import (
    BacktestListResponse,
    BacktestReport,
    RunBacktestRequest,
    WalkForwardReport,
    WalkForwardRequest,
)
from src.modules.backtesting.application.ports import BacktestRunRepository
from src.modules.backtesting.application.use_cases.run_backtest import (
    RunBacktestUseCase,
)
from src.modules.backtesting.application.use_cases.walk_forward import (
    WalkForwardUseCase,
)

router = APIRouter(prefix="/backtests", tags=["backtesting"])


@router.post("")
async def run_backtest(
    request: RunBacktestRequest,
    _: UserProfile = Depends(get_current_user),
    use_case: RunBacktestUseCase = Depends(get_run_backtest_use_case),
) -> BacktestReport:
    return await use_case.execute(request)


@router.get("")
async def list_backtests(
    _: UserProfile = Depends(get_current_user),
    repository: BacktestRunRepository = Depends(get_backtest_repository),
) -> BacktestListResponse:
    return BacktestListResponse(backtests=await repository.list_runs())


@router.post("/walk-forward")
async def walk_forward(
    request: WalkForwardRequest,
    _: UserProfile = Depends(get_current_user),
    use_case: WalkForwardUseCase = Depends(get_walk_forward_use_case),
) -> WalkForwardReport:
    return await use_case.execute(request)
