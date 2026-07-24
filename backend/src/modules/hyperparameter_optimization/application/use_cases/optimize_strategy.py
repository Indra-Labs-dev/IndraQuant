from src.modules.backtesting.application.dto import StrategySpec
from src.modules.backtesting.application.service import (
    min_history,
    positions_for,
    validate_strategy,
)
from src.modules.backtesting.domain.engine import BacktestCandle, run_backtest
from src.modules.hyperparameter_optimization.application.dispatch import run_search
from src.modules.hyperparameter_optimization.application.dto import (
    HpoResultDto,
    HpoTrialDto,
    OptimizeStrategyRequest,
)
from src.modules.hyperparameter_optimization.domain.search_space import ParamSpec
from src.modules.technical_analysis.application.ports import OhlcvProvider
from src.shared.kernel.errors import AppError

_SECONDS_PER_YEAR = 365 * 86_400
_TIMEFRAME_SECONDS = {
    "1s": 1, "5s": 5, "30s": 30, "1m": 60, "5m": 300,
    "15m": 900, "1h": 3_600, "4h": 14_400, "1d": 86_400,
}

# Continuous/integer search ranges per strategy type — the objective
# function samples anywhere in these ranges, unlike the small fixed grids
# used elsewhere (walk-forward, Reality Check) for a fast, fixed universe.
_PARAM_SPECS: dict[str, list[ParamSpec]] = {
    "sma_crossover": [
        ParamSpec("fast", "int", 5, 50),
        ParamSpec("slow", "int", 20, 200),
    ],
    "macd_crossover": [
        ParamSpec("fast", "int", 5, 30),
        ParamSpec("slow", "int", 15, 60),
        ParamSpec("signal", "int", 3, 20),
    ],
    "bollinger_breakout": [
        ParamSpec("period", "int", 5, 50),
        ParamSpec("num_std", "float", 1.0, 3.5),
    ],
    "rsi_reversion": [
        ParamSpec("period", "int", 5, 30),
        ParamSpec("low", "float", 10.0, 40.0),
        ParamSpec("high", "float", 60.0, 90.0),
    ],
}


class OptimizeStrategyUseCase:
    """Hyperparameter Optimization applied to a Strategy Builder strategy
    (docs/roadmap #8): searches the strategy's own numeric parameters for
    the combination that maximizes total backtest return, via the
    requested engine (grid / random / Bayesian-Optuna / Bayesian-Hyperopt).
    Reuses the exact same `positions_for`/`run_backtest` pipeline as a
    normal backtest — no duplicated simulation logic."""

    def __init__(self, ohlcv: OhlcvProvider) -> None:
        self._ohlcv = ohlcv

    def execute(self, request: OptimizeStrategyRequest) -> HpoResultDto:
        param_specs = _PARAM_SPECS.get(request.strategy_type)
        if param_specs is None:
            raise AppError(
                "unknown_strategy",
                f"Type de stratégie inconnu pour l'optimisation : {request.strategy_type}.",
                422,
            )

        response = self._ohlcv.execute(
            request.instrument_id, request.timeframe, request.from_, request.to, 5000
        )
        min_needed = min(spec.low for spec in param_specs) + 10
        if len(response.candles) < min_needed:
            raise AppError(
                "not_enough_data",
                "Pas assez de bougies sur la période pour optimiser cette stratégie.",
                422,
            )

        candles = [
            BacktestCandle(open_time=c.open_time, close=c.close) for c in response.candles
        ]
        closes = [c.close for c in candles]
        seconds = _TIMEFRAME_SECONDS.get(request.timeframe, 3_600)

        def objective(params: dict) -> float:
            variant = StrategySpec(type=request.strategy_type, **params)
            try:
                validate_strategy(variant)
            except AppError:
                return -1.0
            if len(closes) < min_history(variant):
                return -1.0
            positions = positions_for(variant, closes)
            result = run_backtest(
                candles,
                positions,
                request.initial_capital,
                periods_per_year=_SECONDS_PER_YEAR / seconds,
            )
            return result.metrics["total_return"]

        result = run_search(request.method, param_specs, objective, request.n_trials)

        return HpoResultDto(
            method=result.method,
            best_params=result.best_params,
            best_value=result.best_value,
            n_trials=len(result.trials),
            trials=[
                HpoTrialDto(trial=t.trial, params=t.params, value=t.value)
                for t in result.trials
            ],
            explanation=(
                f"Optimisation de la stratégie « {request.strategy_type} » via "
                f"{result.method} sur {len(result.trials)} essai(s) : meilleurs "
                f"paramètres {result.best_params}, rendement total "
                f"{(result.best_value or 0) * 100:.2f} %. Résultat historique sur "
                "la période demandée — un ré-entraînement sur une autre période "
                "peut donner des paramètres différents (risque de surapprentissage "
                "si la période est courte ou peu représentative)."
            ),
        )
