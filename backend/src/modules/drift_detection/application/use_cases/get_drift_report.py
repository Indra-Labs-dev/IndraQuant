from datetime import datetime, timedelta, timezone

from src.modules.drift_detection.application.dto import (
    ConceptDriftDto,
    DriftReportResponse,
    FeatureDriftDto,
    LabelDriftDto,
)
from src.modules.drift_detection.domain.drift import (
    ConceptDrift,
    concept_drift,
    data_drift_report,
    label_drift,
    overall_severity,
)
from src.modules.machine_learning.domain.features import FEATURE_NAMES, build_features
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
_MIN_RESOLVED_PER_WINDOW = 10


class GetDriftReportUseCase:
    """Drift Detection (docs/roadmap #6): Data Drift + Label Drift from the
    same feature matrix `PredictDirectionUseCase` trains on (split
    chronologically into an older reference half and a recent half), and
    Concept Drift from the real, verified accuracy already tracked by the
    auto-learning loop (ADR-020) — no model is duplicated or retrained
    here, only the existing feature-building and prediction-history code
    is reused."""

    def __init__(
        self, ohlcv: OhlcvProvider, predictions: SqlAlchemyPredictionRepository
    ) -> None:
        self._ohlcv = ohlcv
        self._predictions = predictions

    def execute(self, instrument_id: int, timeframe: str) -> DriftReportResponse:
        seconds = _TIMEFRAME_SECONDS.get(timeframe, 3_600)
        end = datetime.now(timezone.utc)
        start = end - timedelta(seconds=seconds * _TRAINING_CANDLES)
        response = self._ohlcv.execute(instrument_id, timeframe, start, end, 5000)

        closes = [c.close for c in response.candles]
        volumes = [c.volume for c in response.candles]
        rows, labels, _returns, _latest = build_features(closes, volumes)
        if len(rows) < _MIN_ROWS:
            raise AppError(
                "not_enough_data",
                f"Pas assez d'historique pour évaluer la dérive "
                f"({len(rows)} lignes, minimum {_MIN_ROWS}).",
                422,
            )

        midpoint = len(rows) // 2
        feature_drifts = data_drift_report(rows[:midpoint], rows[midpoint:], FEATURE_NAMES)
        label = label_drift(labels[:midpoint], labels[midpoint:])
        concept = self._concept_drift(instrument_id, response.timeframe)

        severity = overall_severity(
            [f.severity for f in feature_drifts] + [label.severity, concept.severity]
        )
        drifting_features = [f.feature for f in feature_drifts if f.severity == "significative"]

        explanation = (
            f"Évaluation de dérive : {severity}. "
            + (
                f"Feature(s) en dérive significative : {', '.join(drifting_features)}. "
                if drifting_features
                else "Aucune feature en dérive significative. "
            )
            + label.explanation
            + " "
            + concept.explanation
        )

        return DriftReportResponse(
            instrument_id=instrument_id,
            timeframe=response.timeframe,
            overall_severity=severity,
            feature_drifts=[
                FeatureDriftDto(
                    feature=f.feature, psi=f.psi, severity=f.severity, explanation=f.explanation
                )
                for f in feature_drifts
            ],
            label_drift=LabelDriftDto(
                reference_up_rate=label.reference_up_rate,
                recent_up_rate=label.recent_up_rate,
                delta=label.delta,
                severity=label.severity,
                explanation=label.explanation,
            ),
            concept_drift=ConceptDriftDto(
                reference_accuracy=concept.reference_accuracy,
                recent_accuracy=concept.recent_accuracy,
                reference_n=concept.reference_n,
                recent_n=concept.recent_n,
                delta=concept.delta,
                severity=concept.severity,
                explanation=concept.explanation,
            ),
            explanation=explanation,
        )

    def _concept_drift(self, instrument_id: int, timeframe: str) -> ConceptDrift:
        resolved: list[PredictionModel] = self._predictions.list_resolved_ordered(
            instrument_id, timeframe
        )
        n = len(resolved)
        midpoint = n // 2
        reference, recent = resolved[:midpoint], resolved[midpoint:]
        reference_accuracy = (
            sum(1 for p in reference if p.correct) / len(reference) if reference else None
        )
        recent_accuracy = (
            sum(1 for p in recent if p.correct) / len(recent) if recent else None
        )
        return concept_drift(
            reference_accuracy,
            recent_accuracy,
            len(reference),
            len(recent),
            _MIN_RESOLVED_PER_WINDOW,
        )
