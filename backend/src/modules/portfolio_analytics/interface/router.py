from fastapi import APIRouter, Depends

from src.composition_root import get_current_user, get_portfolio_summary_use_case
from src.modules.auth.application.dto import UserProfile
from src.modules.portfolio_analytics.application.use_cases.get_portfolio_summary import (
    GetPortfolioSummaryUseCase,
    PortfolioSummary,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio-analytics"])


@router.get("/summary")
async def get_portfolio_summary(
    _: UserProfile = Depends(get_current_user),
    use_case: GetPortfolioSummaryUseCase = Depends(get_portfolio_summary_use_case),
) -> PortfolioSummary:
    return await use_case.execute()
