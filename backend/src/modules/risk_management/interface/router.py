from fastapi import APIRouter, Depends, Query

from src.composition_root import (
    get_current_user,
    get_exposure_report_use_case,
    get_risk_budget_use_case,
    get_risk_profile_use_case,
)
from src.modules.auth.application.dto import UserProfile
from src.modules.risk_management.application.dto import (
    ExposureReportResponse,
    RiskBudgetResponse,
    RiskProfileResponse,
)
from src.modules.risk_management.application.use_cases.get_exposure_report import (
    GetExposureReportUseCase,
)
from src.modules.risk_management.application.use_cases.get_risk_budget import (
    GetRiskBudgetUseCase,
)
from src.modules.risk_management.application.use_cases.get_risk_profile import (
    GetRiskProfileUseCase,
)

router = APIRouter(tags=["risk-management"])


@router.get("/instruments/{instrument_id}/risk-profile")
async def get_risk_profile(
    instrument_id: int,
    timeframe: str = Query(default="1h"),
    capital: float = Query(default=10_000.0, gt=0),
    risk_per_trade_pct: float = Query(default=0.01, gt=0, le=1.0),
    stop_distance_pct: float = Query(default=0.02, gt=0, le=1.0),
    _: UserProfile = Depends(get_current_user),
    use_case: GetRiskProfileUseCase = Depends(get_risk_profile_use_case),
) -> RiskProfileResponse:
    return await use_case.execute(
        instrument_id, timeframe, capital, risk_per_trade_pct, stop_distance_pct
    )


@router.get("/portfolio/exposure")
async def get_exposure_report(
    max_single_pct: float = Query(default=25.0, gt=0, le=100.0),
    max_total_pct: float = Query(default=100.0, gt=0, le=1000.0),
    _: UserProfile = Depends(get_current_user),
    use_case: GetExposureReportUseCase = Depends(get_exposure_report_use_case),
) -> ExposureReportResponse:
    return await use_case.execute(max_single_pct, max_total_pct)


@router.get("/portfolio/risk-budget")
async def get_risk_budget(
    _: UserProfile = Depends(get_current_user),
    use_case: GetRiskBudgetUseCase = Depends(get_risk_budget_use_case),
) -> RiskBudgetResponse:
    return await use_case.execute()
