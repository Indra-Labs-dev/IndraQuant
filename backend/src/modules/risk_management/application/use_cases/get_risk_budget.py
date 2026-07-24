from datetime import datetime, timedelta, timezone

from src.modules.portfolio_analytics.application.use_cases.get_portfolio_summary import (
    GetPortfolioSummaryUseCase,
)
from src.modules.risk_management.application.dto import (
    RiskBudgetItemDto,
    RiskBudgetResponse,
)
from src.modules.risk_management.domain import metrics
from src.modules.risk_management.domain.advanced import risk_budget_allocation
from src.modules.technical_analysis.application.ports import OhlcvProvider

_SECONDS_PER_YEAR = 365 * 86_400
_LOOKBACK_CANDLES = 200
_TIMEFRAME = "1h"
_TIMEFRAME_SECONDS = 3_600


class GetRiskBudgetUseCase:
    """Risk Budget (docs/roadmap #10): compares each currently-held
    position's actual capital weight (from the real paper-trading
    portfolio, `GetPortfolioSummaryUseCase`) against an inverse-volatility
    risk-parity target — positions much more volatile than their capital
    weight suggests are contributing disproportionate risk."""

    def __init__(
        self, portfolio_summary: GetPortfolioSummaryUseCase, ohlcv: OhlcvProvider
    ) -> None:
        self._portfolio_summary = portfolio_summary
        self._ohlcv = ohlcv

    def execute(self) -> RiskBudgetResponse:
        summary = self._portfolio_summary.execute()
        volatilities: dict[str, float] = {}
        volatility_by_instrument: dict[int, float | None] = {}

        end = datetime.now(timezone.utc)
        start = end - timedelta(seconds=_TIMEFRAME_SECONDS * _LOOKBACK_CANDLES)
        for allocation in summary.allocation:
            try:
                response = self._ohlcv.execute(
                    allocation.instrument_id, _TIMEFRAME, start, end, 2000
                )
                closes = [c.close for c in response.candles]
                returns = metrics.period_returns(closes)
                vol = metrics.annualized_volatility(
                    returns, _SECONDS_PER_YEAR / _TIMEFRAME_SECONDS
                )
            except Exception:
                vol = None
            volatility_by_instrument[allocation.instrument_id] = vol
            if vol is not None and vol > 0:
                volatilities[allocation.symbol] = vol

        targets = risk_budget_allocation(volatilities)

        items = [
            RiskBudgetItemDto(
                instrument_id=a.instrument_id,
                symbol=a.symbol,
                current_weight_pct=round(a.weight_pct, 2),
                target_weight_pct=targets.get(a.symbol, 0.0),
                annualized_volatility=volatility_by_instrument.get(a.instrument_id),
            )
            for a in summary.allocation
        ]

        return RiskBudgetResponse(
            items=items,
            explanation=(
                f"Budget de risque par parité de risque inverse-volatilité sur "
                f"{len(items)} position(s) : le poids cible est inversement "
                "proportionnel à la volatilité annualisée de chaque instrument, "
                "pour que chaque position contribue un risque comparable au "
                "portefeuille — un écart important entre poids actuel et poids "
                "cible signale une position sur- ou sous-pondérée par rapport à "
                "son risque réel."
            ),
        )
