import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.modules.machine_learning.application.dto import (
    DirectionPrediction,
    FeatureContribution,
    ModelScore,
    PredictionTrackRecord,
)
from src.modules.machine_learning.domain.calibration import (
    blend_calibration,
    confidence_bucket,
)
from src.modules.machine_learning.domain.features import FEATURE_NAMES, build_features
from src.modules.machine_learning.infrastructure.direction_model import DirectionModel
from src.modules.prediction_engine.infrastructure.sqlalchemy_repository import (
    PredictionModel,
    SqlAlchemyPredictionRepository,
)
from src.modules.technical_analysis.application.ports import OhlcvProvider
from src.shared.kernel.errors import AppError

_TIMEFRAME_SECONDS = {
    "1s": 1, "5s": 5, "30s": 30, "1m": 60, "5m": 300,
    "15m": 900, "1h": 3_600, "4h": 14_400, "1d": 86_400,
}
_TRAINING_CANDLES = 1500
_MIN_ROWS = 200
_CACHE_TTL_SECONDS = 60


def _naive(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


class PredictDirectionUseCase:
    """Prediction Engine: probabilistic, explained next-candle direction.
    Trains on the fly on recent history (mono-user local scale), persists
    every prediction, and recalibrates its confidence from real verified
    outcomes (ADR-020) — the model's self-correction loop."""

    def __init__(
        self,
        ohlcv: OhlcvProvider,
        model: DirectionModel,
        predictions: SqlAlchemyPredictionRepository | None = None,
        cache=None,
    ) -> None:
        self._ohlcv = ohlcv
        self._model = model
        self._predictions = predictions
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

        models = [
            ModelScore(
                name=name,
                prob_up=round(trained.model_probs[name], 4),
                test_accuracy=round(trained.model_accuracies[name], 4),
            )
            for name in trained.model_probs
        ]

        as_of = response.candles[-1].open_time
        target_time = as_of + timedelta(seconds=seconds)
        predicted_direction = "up" if trained.prob_up >= 0.5 else "down"
        raw_confidence = max(trained.prob_up, 1.0 - trained.prob_up)

        track_record = self._record_and_get_track_record(
            instrument_id,
            timeframe,
            as_of,
            target_time,
            predicted_direction,
            trained.prob_up,
            models,
        )

        calibrated_confidence = blend_calibration(
            raw_confidence, track_record.bucket_accuracy, track_record.bucket_resolved
        )
        calibrated_prob_up = (
            calibrated_confidence
            if predicted_direction == "up"
            else 1.0 - calibrated_confidence
        )

        direction = "haussière" if calibrated_prob_up >= 0.5 else "baissière"
        probability = max(calibrated_prob_up, 1.0 - calibrated_prob_up)
        edge = trained.test_accuracy - trained.baseline_accuracy
        reliability = (
            "le modèle ne fait pas mieux que le hasard sur la période de test — "
            "prudence maximale"
            if edge <= 0
            else f"le modèle bat la référence naïve de {edge * 100:.1f} points sur la période de test"
        )
        calibration_note = (
            f" Auto-apprentissage : sur {track_record.bucket_resolved} prédiction(s) "
            f"passée(s) à un niveau de confiance comparable, le modèle a eu raison "
            f"{track_record.bucket_accuracy * 100:.1f} % du temps — la confiance "
            f"affichée en tient compte (brute : {raw_confidence * 100:.1f} %)."
            if track_record.bucket_accuracy is not None
            else " Auto-apprentissage : pas encore assez de prédictions vérifiées "
            "pour recalibrer la confiance ; cela s'affinera automatiquement au "
            "fil des prochaines bougies résolues."
        )

        prediction = DirectionPrediction(
            instrument_id=instrument_id,
            timeframe=response.timeframe,
            as_of=as_of,
            horizon_candles=1,
            prob_up=round(calibrated_prob_up, 4),
            prob_down=round(1.0 - calibrated_prob_up, 4),
            raw_prob_up=round(trained.prob_up, 4),
            models=models,
            test_accuracy=round(trained.test_accuracy, 4),
            baseline_accuracy=round(trained.baseline_accuracy, 4),
            training_rows=trained.training_rows,
            top_features=contributions,
            track_record=track_record,
            explanation=(
                f"Tendance {direction} estimée à {probability * 100:.1f} % pour la "
                f"prochaine bougie {response.timeframe} (ensemble XGBoost + "
                f"régression logistique, {trained.training_rows} bougies "
                f"d'entraînement). Attribution SHAP : les facteurs listés sont "
                f"ceux qui pèsent le plus sur cette estimation. Fiabilité : "
                f"{reliability}.{calibration_note} Sortie probabiliste — jamais "
                "une certitude."
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

    def _record_and_get_track_record(
        self,
        instrument_id: int,
        timeframe: str,
        as_of: datetime,
        target_time: datetime,
        predicted_direction: str,
        raw_prob_up: float,
        models: list[ModelScore],
    ) -> PredictionTrackRecord:
        low, high = confidence_bucket(max(raw_prob_up, 1.0 - raw_prob_up))

        if self._predictions is None:
            return PredictionTrackRecord(
                bucket_low=low,
                bucket_high=high,
                bucket_resolved=0,
                bucket_accuracy=None,
                overall_resolved=0,
                overall_accuracy=None,
            )

        as_of_naive, target_naive = _naive(as_of), _naive(target_time)
        if self._predictions.get_by_as_of(instrument_id, timeframe, as_of_naive) is None:
            self._predictions.add(
                PredictionModel(
                    instrument_id=instrument_id,
                    timeframe=timeframe,
                    as_of=as_of_naive,
                    target_time=target_naive,
                    predicted_direction=predicted_direction,
                    raw_prob_up=Decimal(str(round(raw_prob_up, 4))),
                    model_json=json.dumps([m.model_dump() for m in models]),
                )
            )

        bucket_resolved, bucket_accuracy = self._predictions.calibration_stats(
            timeframe, low, high
        )
        overall_resolved, overall_accuracy = self._predictions.overall_accuracy(
            timeframe
        )
        return PredictionTrackRecord(
            bucket_low=low,
            bucket_high=high,
            bucket_resolved=bucket_resolved,
            bucket_accuracy=bucket_accuracy,
            overall_resolved=overall_resolved,
            overall_accuracy=overall_accuracy,
        )
