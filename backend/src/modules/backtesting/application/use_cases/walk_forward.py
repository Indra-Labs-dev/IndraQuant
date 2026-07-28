from src.modules.backtesting.application.dto import (
    WalkForwardFold,
    WalkForwardReport,
    WalkForwardRequest,
)
from src.modules.backtesting.domain.engine import (
    BacktestCandle,
    run_backtest,
    sma_crossover_positions,
)
from src.modules.technical_analysis.application.ports import OhlcvProvider
from src.shared.kernel.errors import AppError

_PARAM_GRID = [(10, 30), (10, 50), (20, 50), (20, 100), (30, 100)]


class WalkForwardUseCase:
    """Rolling-window validation: optimize the strategy on window i, evaluate
    on window i+1 — guards against overfitting a single lucky period."""

    def __init__(self, ohlcv: OhlcvProvider) -> None:
        self._ohlcv = ohlcv

    async def execute(self, request: WalkForwardRequest) -> WalkForwardReport:
        response = await self._ohlcv.execute(
            request.instrument_id, request.timeframe, request.from_, request.to, 5000
        )
        candles = [
            BacktestCandle(open_time=c.open_time, close=c.close)
            for c in response.candles
        ]
        segment_size = len(candles) // (request.folds + 1)
        if segment_size < 120:
            raise AppError(
                "not_enough_data",
                "Pas assez de bougies pour une validation walk-forward "
                f"en {request.folds} plis (minimum {(request.folds + 1) * 120}).",
                422,
            )

        folds: list[WalkForwardFold] = []
        for fold in range(request.folds):
            train = candles[fold * segment_size : (fold + 1) * segment_size]
            test = candles[(fold + 1) * segment_size : (fold + 2) * segment_size]

            best_params, best_return = None, None
            for fast, slow in _PARAM_GRID:
                if len(train) < slow + 2:
                    continue
                result = self._run(train, fast, slow, request.initial_capital)
                if best_return is None or result > best_return:
                    best_params, best_return = (fast, slow), result
            if best_params is None:
                raise AppError(
                    "not_enough_data", "Fenêtre d'entraînement trop courte.", 422
                )

            test_return = self._run(
                test, best_params[0], best_params[1], request.initial_capital
            )
            folds.append(
                WalkForwardFold(
                    fold=fold + 1,
                    best_fast=best_params[0],
                    best_slow=best_params[1],
                    train_return=best_return,
                    test_return=test_return,
                )
            )

        mean_test = sum(f.test_return for f in folds) / len(folds)
        positive = sum(1 for f in folds if f.test_return > 0)
        return WalkForwardReport(
            instrument_id=request.instrument_id,
            timeframe=response.timeframe,
            folds=folds,
            mean_test_return=mean_test,
            positive_test_folds=positive,
            total_folds=len(folds),
            explanation=(
                f"Validation en {len(folds)} plis glissants : les paramètres "
                "optimisés sur chaque fenêtre d'entraînement sont évalués sur la "
                f"fenêtre suivante, jamais vue. Rendement test moyen "
                f"{mean_test * 100:.2f} %, {positive}/{len(folds)} plis positifs. "
                "Un écart important entre rendement d'entraînement et de test "
                "signale du surapprentissage."
            ),
        )

    def _run(
        self,
        candles: list[BacktestCandle],
        fast: int,
        slow: int,
        capital: float,
    ) -> float:
        closes = [c.close for c in candles]
        positions = sma_crossover_positions(closes, fast, slow)
        result = run_backtest(candles, positions, capital)
        return result.metrics["total_return"]
