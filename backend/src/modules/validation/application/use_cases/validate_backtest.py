from src.modules.backtesting.application.dto import RunBacktestRequest, StrategySpec
from src.modules.backtesting.application.service import (
    min_history,
    positions_for,
    validate_strategy,
)
from src.modules.backtesting.domain.engine import BacktestCandle, run_backtest
from src.modules.feature_engineering.application import service as fe
from src.modules.risk_management.domain.metrics import period_returns
from src.modules.technical_analysis.application.ports import OhlcvProvider
from src.modules.validation.application.dto import (
    BacktestValidationResponse,
    BootstrapDto,
    MonteCarloDto,
    WhiteRealityCheckDto,
)
from src.modules.validation.domain.resampling import (
    bootstrap_confidence_interval,
    monte_carlo_permutation_test,
    white_reality_check,
)
from src.shared.kernel.errors import AppError

_SECONDS_PER_YEAR = 365 * 86_400
_TIMEFRAME_SECONDS = {
    "1s": 1, "5s": 5, "30s": 30, "1m": 60, "5m": 300,
    "15m": 900, "1h": 3_600, "4h": 14_400, "1d": 86_400,
}

# Small, strategy-type-specific parameter grids used only to build the
# "many candidates tried" universe White's Reality Check needs — the same
# spirit as the walk-forward grid, generalized across all four strategy
# types so the Reality Check isn't limited to sma_crossover.
_VARIANT_GRIDS: dict[str, list[dict]] = {
    "sma_crossover": [
        {"fast": 10, "slow": 30}, {"fast": 10, "slow": 50}, {"fast": 20, "slow": 50},
        {"fast": 20, "slow": 100}, {"fast": 30, "slow": 100},
    ],
    "macd_crossover": [
        {"fast": 8, "slow": 17, "signal": 9}, {"fast": 12, "slow": 26, "signal": 9},
        {"fast": 12, "slow": 26, "signal": 5}, {"fast": 19, "slow": 39, "signal": 9},
        {"fast": 6, "slow": 13, "signal": 5},
    ],
    "bollinger_breakout": [
        {"period": 10, "num_std": 1.5}, {"period": 20, "num_std": 2.0},
        {"period": 20, "num_std": 2.5}, {"period": 30, "num_std": 2.0},
        {"period": 15, "num_std": 2.0},
    ],
    "rsi_reversion": [
        {"period": 7, "low": 25.0, "high": 75.0}, {"period": 14, "low": 30.0, "high": 70.0},
        {"period": 14, "low": 20.0, "high": 80.0}, {"period": 21, "low": 30.0, "high": 70.0},
        {"period": 10, "low": 25.0, "high": 75.0},
    ],
}


class ValidateBacktestUseCase:
    """Scientific validation of a backtest result (docs/roadmap #7):
    Bootstrap confidence interval on the realized return, a Monte Carlo
    permutation test on the strategy's position timing (vs random timing
    on the same market), and White's Reality Check across a small grid of
    parameter variants of the same strategy type — testing whether the
    reported edge survives the correction for having tried several
    variants (data-snooping bias)."""

    def __init__(self, ohlcv: OhlcvProvider) -> None:
        self._ohlcv = ohlcv

    async def execute(self, request: RunBacktestRequest) -> BacktestValidationResponse:
        validate_strategy(request.strategy)
        response = await self._ohlcv.execute(
            request.instrument_id, request.timeframe, request.from_, request.to, 5000
        )
        if len(response.candles) < min_history(request.strategy):
            raise AppError(
                "not_enough_data",
                "Pas assez de bougies sur la période pour valider cette stratégie.",
                422,
            )

        candles = [
            BacktestCandle(open_time=c.open_time, close=c.close) for c in response.candles
        ]
        closes = [c.close for c in candles]
        seconds = _TIMEFRAME_SECONDS.get(request.timeframe, 3_600)

        positions = positions_for(request.strategy, closes)
        result = run_backtest(
            candles,
            positions,
            request.initial_capital,
            periods_per_year=_SECONDS_PER_YEAR / seconds,
        )
        equity = [e for _, e in result.equity_curve]
        strategy_returns = period_returns(equity)
        market_returns = [r for r in fe.returns(closes) if r is not None]

        bootstrap = bootstrap_confidence_interval(strategy_returns)
        monte_carlo = monte_carlo_permutation_test(market_returns, positions)
        reality_check = self._reality_check(
            request.strategy, candles, request.initial_capital, seconds
        )

        explanation = (
            "Validation statistique du backtest : "
            + bootstrap.explanation
            + " "
            + monte_carlo.explanation
            + " "
            + reality_check.explanation
        )

        return BacktestValidationResponse(
            instrument_id=request.instrument_id,
            timeframe=response.timeframe,
            bootstrap=BootstrapDto(
                mean=bootstrap.mean,
                ci_low=bootstrap.ci_low,
                ci_high=bootstrap.ci_high,
                confidence=bootstrap.confidence,
                explanation=bootstrap.explanation,
            ),
            monte_carlo=MonteCarloDto(
                observed_return=monte_carlo.observed_return,
                p_value=monte_carlo.p_value,
                null_mean=monte_carlo.null_mean,
                null_std=monte_carlo.null_std,
                explanation=monte_carlo.explanation,
            ),
            reality_check=WhiteRealityCheckDto(
                best_candidate_index=reality_check.best_candidate_index,
                best_mean_return=reality_check.best_mean_return,
                p_value=reality_check.p_value,
                n_candidates=reality_check.n_candidates,
                explanation=reality_check.explanation,
            ),
            explanation=explanation,
        )

    def _reality_check(
        self,
        strategy: StrategySpec,
        candles: list[BacktestCandle],
        capital: float,
        seconds: int,
    ):
        grid = _VARIANT_GRIDS.get(strategy.type, [])
        closes = [c.close for c in candles]
        candidate_returns: list[list[float]] = []
        for params in grid:
            variant = strategy.model_copy(update=params)
            try:
                validate_strategy(variant)
            except AppError:
                continue
            variant_positions = positions_for(variant, closes)
            variant_result = run_backtest(
                candles,
                variant_positions,
                capital,
                periods_per_year=_SECONDS_PER_YEAR / seconds,
            )
            variant_equity = [e for _, e in variant_result.equity_curve]
            candidate_returns.append(period_returns(variant_equity))

        return white_reality_check(candidate_returns)
