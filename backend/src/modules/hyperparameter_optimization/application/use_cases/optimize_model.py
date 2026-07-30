import json
from datetime import datetime, timedelta, timezone

from src.modules.hyperparameter_optimization.application.dispatch import run_search
from src.modules.hyperparameter_optimization.application.dto import (
    HpoResultDto,
    HpoTrialDto,
    OptimizeModelRequest,
)
from src.modules.hyperparameter_optimization.domain.search_space import ParamSpec
from src.modules.hyperparameter_optimization.infrastructure.model_objective import (
    cross_validated_accuracy,
)
from src.modules.machine_learning.domain.features import build_features
from src.modules.technical_analysis.application.ports import OhlcvProvider
from src.shared.kernel.errors import AppError

_TIMEFRAME_SECONDS = {
    "1s": 1, "5s": 5, "30s": 30, "1m": 60, "5m": 300,
    "15m": 900, "1h": 3_600, "4h": 14_400, "1d": 86_400,
}
_TRAINING_CANDLES = 1500
_MIN_ROWS = 200

_PARAM_SPECS = [
    ParamSpec("n_estimators", "int", 50, 400, step=10),
    ParamSpec("max_depth", "int", 2, 6),
    ParamSpec("learning_rate", "float", 0.01, 0.3),
]
# Same key format `PredictDirectionUseCase` reads from before constructing a
# `DirectionModel` (see prediction_engine/application/use_cases/
# predict_direction.py) — kept as a plain literal on both sides rather than a
# shared constant to avoid a hyperparameter_optimization -> prediction_engine
# import for a single string.
_HPO_CACHE_KEY = "hpo:best_params:{instrument_id}:{timeframe}"
_HPO_CACHE_TTL_SECONDS = 30 * 86_400


class OptimizeModelHyperparametersUseCase:
    """Hyperparameter Optimization applied to the Prediction Engine's
    XGBoost direction model (docs/roadmap #8): searches n_estimators/
    max_depth/learning_rate for the combination maximizing mean Time
    Series CV accuracy (docs/roadmap #7), via the requested engine. A
    successful search persists its best configuration (ADR-038) so the next
    `PredictDirectionUseCase` call for this exact instrument/timeframe picks
    it up — this used to be a read-only diagnostic with no effect on
    production, now it is the mechanism for actually tuning the model."""

    def __init__(self, ohlcv: OhlcvProvider, cache=None) -> None:
        self._ohlcv = ohlcv
        self._cache = cache

    async def execute(self, request: OptimizeModelRequest) -> HpoResultDto:
        seconds = _TIMEFRAME_SECONDS.get(request.timeframe, 3_600)
        end = datetime.now(timezone.utc)
        start = end - timedelta(seconds=seconds * _TRAINING_CANDLES)
        response = await self._ohlcv.execute(request.instrument_id, request.timeframe, start, end, 5000)

        closes = [c.close for c in response.candles]
        volumes = [c.volume for c in response.candles]
        rows, labels, _returns, _latest = build_features(closes, volumes)
        if len(rows) < _MIN_ROWS:
            raise AppError(
                "not_enough_data",
                f"Pas assez d'historique pour optimiser le modèle "
                f"({len(rows)} lignes, minimum {_MIN_ROWS}).",
                422,
            )

        def objective(params: dict) -> float:
            return cross_validated_accuracy(
                rows,
                labels,
                n_estimators=int(params["n_estimators"]),
                max_depth=int(params["max_depth"]),
                learning_rate=float(params["learning_rate"]),
            )

        result = run_search(request.method, _PARAM_SPECS, objective, request.n_trials)

        applied = False
        if result.best_params is not None and self._cache is not None:
            try:
                await self._cache.set(
                    _HPO_CACHE_KEY.format(
                        instrument_id=request.instrument_id, timeframe=request.timeframe
                    ),
                    json.dumps(result.best_params),
                    ex=_HPO_CACHE_TTL_SECONDS,
                )
                applied = True
            except Exception:
                pass

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
                f"Optimisation des hyperparamètres XGBoost via {result.method} sur "
                f"{len(result.trials)} essai(s) : meilleure configuration "
                f"{result.best_params}, précision moyenne en Time Series CV "
                f"{(result.best_value or 0) * 100:.1f} %. "
                + (
                    "Cette configuration est désormais appliquée : le prochain appel "
                    "au Prediction Engine pour cet instrument/unité de temps "
                    "l'utilisera automatiquement (valable 30 jours)."
                    if applied
                    else "Configuration non persistée (cache indisponible) — le "
                    "Prediction Engine continue d'utiliser ses hyperparamètres "
                    "actuels."
                )
            ),
        )
