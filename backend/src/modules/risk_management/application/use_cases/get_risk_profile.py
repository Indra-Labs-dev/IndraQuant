from datetime import datetime, timedelta, timezone

from src.modules.risk_management.application.dto import (
    KellyDto,
    PositionSizeDto,
    RiskProfileResponse,
    StressScenarioDto,
)
from src.modules.risk_management.domain import metrics
from src.modules.risk_management.domain.advanced import (
    expected_shortfall,
    kelly_criterion,
    position_sizing,
    risk_of_ruin,
    stress_test,
)
from src.modules.technical_analysis.application.ports import OhlcvProvider
from src.shared.kernel.errors import AppError

_TIMEFRAME_SECONDS = {
    "1s": 1, "5s": 5, "30s": 30, "1m": 60, "5m": 300,
    "15m": 900, "1h": 3_600, "4h": 14_400, "1d": 86_400,
}
_SECONDS_PER_YEAR = 365 * 86_400
_CANDLE_WINDOW = 500
_MIN_ROWS = 30
_DEFAULT_RISK_PER_TRADE_PCT = 0.01
_DEFAULT_STOP_DISTANCE_PCT = 0.02


class GetRiskProfileUseCase:
    """Advanced Risk Engine for a single instrument (docs/roadmap #10):
    extends the existing VaR/max-drawdown/volatility (`risk_management/
    domain/metrics.py`, already used by paper trading) with Expected
    Shortfall, Kelly Criterion, a Monte Carlo Risk of Ruin simulation,
    fixed-fractional Position Sizing, and Stress Testing — all derived
    from the instrument's own recent return distribution, no external
    trade log required."""

    def __init__(self, ohlcv: OhlcvProvider) -> None:
        self._ohlcv = ohlcv

    def execute(
        self,
        instrument_id: int,
        timeframe: str,
        capital: float = 10_000.0,
        risk_per_trade_pct: float = _DEFAULT_RISK_PER_TRADE_PCT,
        stop_distance_pct: float = _DEFAULT_STOP_DISTANCE_PCT,
    ) -> RiskProfileResponse:
        seconds = _TIMEFRAME_SECONDS.get(timeframe, 3_600)
        end = datetime.now(timezone.utc)
        start = end - timedelta(seconds=seconds * _CANDLE_WINDOW)
        response = self._ohlcv.execute(instrument_id, timeframe, start, end, 2000)

        closes = [c.close for c in response.candles]
        if len(closes) < _MIN_ROWS:
            raise AppError(
                "not_enough_data",
                f"Pas assez d'historique pour établir un profil de risque "
                f"({len(closes)} bougies, minimum {_MIN_ROWS}).",
                422,
            )

        returns = metrics.period_returns(closes)
        var = metrics.historical_var(returns)
        cvar = expected_shortfall(returns)
        drawdown = metrics.max_drawdown(closes)
        volatility = metrics.annualized_volatility(returns, _SECONDS_PER_YEAR / seconds)

        wins = [r for r in returns if r > 0]
        losses = [-r for r in returns if r < 0]
        win_rate = len(wins) / len(returns) if returns else 0.0
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0

        kelly = kelly_criterion(win_rate, avg_win, avg_loss)
        # Betting the instrument's own Kelly fraction (or the requested
        # risk-per-trade if there's no edge) ties the ruin simulation
        # directly to the sizing rule actually being evaluated.
        position_fraction = kelly.fraction if kelly.has_edge else risk_per_trade_pct
        ruin = risk_of_ruin(win_rate, avg_win, avg_loss, max(position_fraction, 0.001))

        current_price = closes[-1]
        stop_price = current_price * (1.0 - stop_distance_pct)
        sizing = position_sizing(capital, risk_per_trade_pct, current_price, stop_price)

        scenarios = stress_test(capital)

        explanation = (
            f"Profil de risque sur {len(closes)} bougies {response.timeframe} : "
            f"{kelly.explanation} Risque de ruine simulé (Monte Carlo, "
            f"fraction {position_fraction * 100:.1f} % par position) : "
            f"{ruin * 100:.1f} % de chance de tomber à 50 % du capital de "
            "départ. " + sizing.explanation
        )

        return RiskProfileResponse(
            instrument_id=instrument_id,
            timeframe=response.timeframe,
            var_95=var,
            expected_shortfall_95=cvar,
            max_drawdown=drawdown,
            annualized_volatility=volatility,
            kelly=KellyDto(
                fraction=kelly.fraction, has_edge=kelly.has_edge, explanation=kelly.explanation
            ),
            risk_of_ruin=round(ruin, 4),
            position_sizing=PositionSizeDto(
                quantity=sizing.quantity,
                risk_amount=sizing.risk_amount,
                position_value=sizing.position_value,
                capital_at_risk_pct=sizing.capital_at_risk_pct,
                explanation=sizing.explanation,
            ),
            stress_test=[
                StressScenarioDto(
                    shock_pct=s.shock_pct,
                    resulting_value=s.resulting_value,
                    loss_amount=s.loss_amount,
                )
                for s in scenarios
            ],
            explanation=explanation,
        )
