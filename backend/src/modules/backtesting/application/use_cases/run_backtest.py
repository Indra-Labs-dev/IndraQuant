from src.modules.backtesting.application.dto import (
    BacktestReport,
    EquityPoint,
    RunBacktestRequest,
    TradeDto,
)
from src.modules.backtesting.application.service import (
    describe,
    min_history,
    positions_for,
    trade_reasons,
    validate_strategy,
)
from src.modules.backtesting.domain.engine import BacktestCandle, run_backtest
from src.modules.backtesting.application.ports import BacktestRunRepository
from src.modules.technical_analysis.application.ports import OhlcvProvider
from src.shared.kernel.errors import AppError

_SECONDS_PER_YEAR = 365 * 86_400

_TIMEFRAME_SECONDS = {
    "1s": 1, "5s": 5, "30s": 30, "1m": 60, "5m": 300,
    "15m": 900, "1h": 3_600, "4h": 14_400, "1d": 86_400,
}


class RunBacktestUseCase:
    def __init__(
        self, ohlcv: OhlcvProvider, runs: BacktestRunRepository | None = None
    ) -> None:
        self._ohlcv = ohlcv
        self._runs = runs

    async def execute(self, request: RunBacktestRequest, persist: bool = True) -> BacktestReport:
        validate_strategy(request.strategy)

        response = await self._ohlcv.execute(
            request.instrument_id,
            request.timeframe,
            request.from_,
            request.to,
            5000,
        )
        if len(response.candles) < min_history(request.strategy):
            raise AppError(
                "not_enough_data",
                "Pas assez de bougies sur la période pour cette stratégie.",
                422,
            )

        candles = [
            BacktestCandle(open_time=c.open_time, close=c.close)
            for c in response.candles
        ]
        closes = [c.close for c in candles]
        positions = positions_for(request.strategy, closes)
        seconds = _TIMEFRAME_SECONDS.get(request.timeframe, 3_600)
        buy_reason, sell_reason = trade_reasons(request.strategy)
        result = run_backtest(
            candles,
            positions,
            request.initial_capital,
            periods_per_year=_SECONDS_PER_YEAR / seconds,
            buy_reason=buy_reason,
            sell_reason=sell_reason,
        )

        metrics = result.metrics
        report = BacktestReport(
            instrument_id=request.instrument_id,
            timeframe=response.timeframe,
            strategy=request.strategy,
            initial_capital=request.initial_capital,
            final_equity=round(metrics["final_equity"], 2),
            total_return=metrics["total_return"],
            max_drawdown=metrics["max_drawdown"],
            sharpe=metrics["sharpe"],
            win_rate=metrics["win_rate"],
            trade_count=metrics["trade_count"],
            trades=[
                TradeDto(
                    side=t.side,
                    time=t.time,
                    price=t.price,
                    quantity=t.quantity,
                    fee=t.fee,
                    reason=t.reason,
                )
                for t in result.trades
            ],
            equity_curve=[
                EquityPoint(time=time, equity=equity)
                for time, equity in result.equity_curve
            ],
            explanation=(
                f"{describe(request.strategy)} "
                f"sur {len(candles)} bougies {response.timeframe} : "
                f"{metrics['trade_count']} ordres simulés (frais 0,1 %), "
                f"rendement total {metrics['total_return'] * 100:.2f} %, "
                f"drawdown maximal {metrics['max_drawdown'] * 100:.2f} %. "
                "Résultat historique — aucune garantie sur le futur."
            ),
        )
        if persist and self._runs is not None:
            report.id = await self._runs.save(report)
        return report
