import json
from datetime import datetime, timedelta, timezone

from src.modules.machine_learning.application.dto import (
    DirectionPrediction,
    FeatureContribution,
    ModelScore,
)
from src.modules.machine_learning.domain.features import FEATURE_NAMES, build_features
from src.modules.machine_learning.infrastructure.direction_model import DirectionModel
from src.modules.technical_analysis.application.ports import OhlcvProvider
from src.shared.kernel.errors import AppError

_TIMEFRAME_SECONDS = {
    "1s": 1, "5s": 5, "30s": 30, "1m": 60, "5m": 300,
    "15m": 900, "1h": 3_600, "4h": 14_400, "1d": 86_400,
}
_TRAINING_CANDLES = 1500
_MIN_ROWS = 200
_CACHE_TTL_SECONDS = 60


class PredictDirectionUseCase:
    """Prediction Engine: probabilistic, explained next-candle direction.
    Trains on the fly on recent history (mono-user local scale) and caches
    the result briefly in Redis."""

    def __init__(
        self, ohlcv: OhlcvProvider, model: DirectionModel, cache=None
    ) -> None:
        self._ohlcv = ohlcv
        self._model = model
        self._cache = cache

    def execute(self, instrument_id: int, timeframe: str) -> DirectionPrediction:
        cache_key = f"prediction:{instrument_id}:{timeframe}"
        if self._cache is not None:
            try:
                cached = self._cache.get(cache_key)
                if cached:
                    return DirectionPrediction(**json.loads(cached))
            except Exception:
                pass

        seconds = _TIMEFRAME_SECONDS.get(timeframe, 3_600)
        end = datetime.now(timezone.utc)
        start = end - timedelta(seconds=seconds * _TRAINING_CANDLES)
        response = self._ohlcv.execute(instrument_id, timeframe, start, end, 5000)

        closes = [c.close for c in response.candles]
        volumes = [c.volume for c in response.candles]
        rows, labels, latest = build_features(closes, volumes)
        if len(rows) < _MIN_ROWS or latest is None:
            raise AppError(
                "not_enough_data",
                f"Pas assez d'historique pour entraîner un modèle fiable "
                f"({len(rows)} lignes, minimum {_MIN_ROWS}).",
                422,
            )

        trained = self._model.train_predict(rows, labels, latest)

        contributions = sorted(
            (
                FeatureContribution(
                    feature=name, value=value, contribution=contribution
                )
                for name, value, contribution in zip(
                    FEATURE_NAMES, latest, trained.shap_contributions
                )
            ),
            key=lambda c: abs(c.contribution),
            reverse=True,
        )[:5]

        direction = "haussière" if trained.prob_up >= 0.5 else "baissière"
        probability = max(trained.prob_up, 1.0 - trained.prob_up)
        edge = trained.test_accuracy - trained.baseline_accuracy
        reliability = (
            "le modèle ne fait pas mieux que le hasard sur la période de test — "
            "prudence maximale"
            if edge <= 0
            else f"le modèle bat la référence naïve de {edge * 100:.1f} points sur la période de test"
        )

        prediction = DirectionPrediction(
            instrument_id=instrument_id,
            timeframe=response.timeframe,
            as_of=response.candles[-1].open_time,
            horizon_candles=1,
            prob_up=round(trained.prob_up, 4),
            prob_down=round(1.0 - trained.prob_up, 4),
            models=[
                ModelScore(
                    name=name,
                    prob_up=round(trained.model_probs[name], 4),
                    test_accuracy=round(trained.model_accuracies[name], 4),
                )
                for name in trained.model_probs
            ],
            test_accuracy=round(trained.test_accuracy, 4),
            baseline_accuracy=round(trained.baseline_accuracy, 4),
            training_rows=trained.training_rows,
            top_features=contributions,
            explanation=(
                f"Tendance {direction} estimée à {probability * 100:.1f} % pour la "
                f"prochaine bougie {response.timeframe} (ensemble XGBoost + "
                f"régression logistique, {trained.training_rows} bougies "
                f"d'entraînement). Attribution SHAP : les facteurs listés sont "
                f"ceux qui pèsent le plus sur cette estimation. Fiabilité : "
                f"{reliability}. Sortie probabiliste — jamais une certitude."
            ),
        )

        if self._cache is not None:
            try:
                self._cache.set(
                    cache_key,
                    prediction.model_dump_json(),
                    ex=_CACHE_TTL_SECONDS,
                )
            except Exception:
                pass
        return prediction
