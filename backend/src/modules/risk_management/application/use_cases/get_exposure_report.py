from src.modules.portfolio_analytics.application.use_cases.get_portfolio_summary import (
    GetPortfolioSummaryUseCase,
)
from src.modules.risk_management.application.dto import (
    ExposureReportResponse,
    ExposureWarningDto,
)
from src.modules.risk_management.domain.advanced import check_exposure

_DEFAULT_MAX_SINGLE_PCT = 25.0
_DEFAULT_MAX_TOTAL_PCT = 100.0


class GetExposureReportUseCase:
    """Exposure Control (docs/roadmap #10): flags concentration risk across
    the real paper-trading portfolio — reuses `GetPortfolioSummaryUseCase`
    (Portfolio Analytics) rather than recomputing allocations."""

    def __init__(self, portfolio_summary: GetPortfolioSummaryUseCase) -> None:
        self._portfolio_summary = portfolio_summary

    async def execute(
        self,
        max_single_pct: float = _DEFAULT_MAX_SINGLE_PCT,
        max_total_pct: float = _DEFAULT_MAX_TOTAL_PCT,
    ) -> ExposureReportResponse:
        summary = await self._portfolio_summary.execute()
        allocations = [(a.symbol, a.weight_pct) for a in summary.allocation]
        warnings, total = check_exposure(allocations, max_single_pct, max_total_pct)

        return ExposureReportResponse(
            warnings=[
                ExposureWarningDto(
                    instrument=w.instrument,
                    weight_pct=w.weight_pct,
                    limit_pct=w.limit_pct,
                    message=w.message,
                )
                for w in warnings
            ],
            total_exposure_pct=total,
            max_single_pct=max_single_pct,
            max_total_pct=max_total_pct,
            explanation=(
                f"{len(warnings)} avertissement(s) d'exposition sur "
                f"{len(allocations)} position(s), exposition totale {total:.1f} %."
                if warnings
                else f"Aucune concentration excessive sur {len(allocations)} "
                f"position(s), exposition totale {total:.1f} %."
            ),
        )
