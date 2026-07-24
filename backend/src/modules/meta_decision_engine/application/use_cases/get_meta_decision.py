from datetime import datetime, timedelta, timezone

from src.modules.economic_calendar.application.use_cases.list_events import (
    CalendarResponse,
    ListEventsUseCase,
)
from src.modules.feature_store.application.service import FeatureStoreService
from src.modules.market_regime.application.use_cases.get_market_regime import (
    GetMarketRegimeUseCase,
)
from src.modules.market_regime.domain.detector import MarketRegime
from src.modules.meta_decision_engine.application.dto import (
    EngineSignalDto,
    MetaDecisionResponse,
    RegimeSummary,
)
from src.modules.meta_decision_engine.domain.engines import (
    DEFAULT_WEIGHTS,
    EngineSignal,
    fuse,
    liquidity_engine,
    mean_reversion_engine,
    trend_engine,
    volatility_engine,
)
from src.modules.machine_learning.application.dto import DirectionPrediction
from src.modules.prediction_engine.application.use_cases.predict_direction import (
    PredictDirectionUseCase,
)
from src.modules.sentiment_analysis.application.use_cases.analyze_news import (
    AnalyzeNewsSentimentUseCase,
    SentimentResponse,
)
from src.modules.smart_money.application.use_cases.detect_smc import DetectSmcUseCase
from src.modules.technical_analysis.application.ports import OhlcvProvider
from src.shared.kernel.errors import AppError

# How much the Market Regime Detector (docs/roadmap #2) reweights the
# fusion: a trending regime leans on the Trend engine, a range regime leans
# on Mean Reversion, and a panic regime distrusts the ML engine (trained on
# data that may no longer describe the current, abnormal conditions) and
# further dampens the whole decision's confidence.
_TREND_REGIME_BOOST = 1.5
_COUNTER_REGIME_DAMPEN = 0.6
_PANIC_ML_DAMPEN = 0.5
_PANIC_CONFIDENCE_DAMPEN = 0.6

_TIMEFRAME_SECONDS = {
    "1s": 1, "5s": 5, "30s": 30, "1m": 60, "5m": 300,
    "15m": 900, "1h": 3_600, "4h": 14_400, "1d": 86_400,
}
_CANDLE_WINDOW = 300
_MIN_ROWS = 60
_SMC_SIGNAL_COUNT = 10


class GetMetaDecisionUseCase:
    """Meta Decision Engine (docs/roadmap #1): fuses independent specialized
    engines — trend, mean reversion, volatility, liquidity (SMC), ML,
    news, macro — into one explainable decision. Composes existing,
    already-tested use cases (`PredictDirectionUseCase`, `DetectSmcUseCase`,
    `AnalyzeNewsSentimentUseCase`, `ListEventsUseCase`) rather than
    duplicating their logic; none of them are modified by this module."""

    def __init__(
        self,
        ohlcv: OhlcvProvider,
        smc: DetectSmcUseCase,
        ml: PredictDirectionUseCase,
        news: AnalyzeNewsSentimentUseCase | None = None,
        calendar: ListEventsUseCase | None = None,
        regime: GetMarketRegimeUseCase | None = None,
        feature_store: FeatureStoreService | None = None,
    ) -> None:
        self._ohlcv = ohlcv
        self._smc = smc
        self._ml = ml
        self._news = news
        self._calendar = calendar
        self._regime = regime
        self._feature_store = feature_store or FeatureStoreService()

    def execute(self, instrument_id: int, timeframe: str) -> MetaDecisionResponse:
        seconds = _TIMEFRAME_SECONDS.get(timeframe, 3_600)
        end = datetime.now(timezone.utc)
        start = end - timedelta(seconds=seconds * _CANDLE_WINDOW)
        response = self._ohlcv.execute(instrument_id, timeframe, start, end, 2000)

        closes = [c.close for c in response.candles]
        volumes = [c.volume for c in response.candles]
        if len(closes) < _MIN_ROWS:
            raise AppError(
                "not_enough_data",
                f"Pas assez d'historique pour le Meta Decision Engine "
                f"({len(closes)} bougies, minimum {_MIN_ROWS}).",
                422,
            )

        smc_signals = self._recent_smc_signals(instrument_id, timeframe, start, end)
        regime = self._detect_regime(instrument_id, timeframe)
        as_of = response.candles[-1].open_time
        features = self._feature_store.get_latest(
            instrument_id, response.timeframe, as_of, closes, volumes
        )

        signals = [
            trend_engine(features),
            mean_reversion_engine(features),
            volatility_engine(features),
            liquidity_engine(features, smc_signals),
            self._ml_signal(instrument_id, timeframe),
            self._news_signal(),
            self._macro_signal(end),
        ]
        weights = self._regime_adjusted_weights(regime)
        decision = fuse(signals, weights)

        confidence = decision.confidence
        explanation = decision.explanation
        if regime is not None and regime.is_panic:
            confidence = round(confidence * _PANIC_CONFIDENCE_DAMPEN, 4)
            explanation += (
                " Régime de panique détecté (Market Regime Detector) : "
                "confiance supplémentairement réduite, le modèle ML est "
                "moins fiable dans des conditions aussi anormales."
            )

        return MetaDecisionResponse(
            instrument_id=instrument_id,
            timeframe=response.timeframe,
            direction=decision.direction,
            score=decision.score,
            confidence=confidence,
            engines=[
                EngineSignalDto(
                    engine=s.engine,
                    direction=s.direction,
                    score=s.score,
                    confidence=s.confidence,
                    explanation=s.explanation,
                )
                for s in decision.engines
            ],
            regime=(
                RegimeSummary(
                    trend=regime.trend,
                    volatility=regime.volatility,
                    is_trending=regime.is_trending,
                    is_panic=regime.is_panic,
                    label=regime.label,
                )
                if regime is not None
                else None
            ),
            explanation=explanation,
        )

    def _detect_regime(
        self, instrument_id: int, timeframe: str
    ) -> MarketRegime | None:
        if self._regime is None:
            return None
        try:
            return self._regime.detect(instrument_id, timeframe)
        except Exception:
            return None

    def _regime_adjusted_weights(
        self, regime: MarketRegime | None
    ) -> dict[str, float]:
        weights = dict(DEFAULT_WEIGHTS)
        if regime is None:
            return weights

        if regime.is_trending and regime.trend in ("bull", "bear"):
            weights["trend"] *= _TREND_REGIME_BOOST
            weights["mean_reversion"] *= _COUNTER_REGIME_DAMPEN
        elif regime.trend == "range":
            weights["mean_reversion"] *= _TREND_REGIME_BOOST
            weights["trend"] *= _COUNTER_REGIME_DAMPEN

        if regime.is_panic:
            weights["ml"] *= _PANIC_ML_DAMPEN

        return weights

    def _recent_smc_signals(
        self, instrument_id: int, timeframe: str, start: datetime, end: datetime
    ) -> list[tuple[str, float]]:
        try:
            detections = self._smc.execute(
                instrument_id, timeframe, start, end, 2000
            ).detections
        except Exception:
            return []
        return [
            (d.direction, d.confidence) for d in detections[-_SMC_SIGNAL_COUNT:]
        ]

    def _ml_signal(self, instrument_id: int, timeframe: str) -> EngineSignal:
        try:
            prediction: DirectionPrediction = self._ml.execute(instrument_id, timeframe)
        except AppError as error:
            return EngineSignal(
                "ml", "neutral", 0.0, 0.0,
                f"Modèle ML indisponible : {error.message}",
            )
        except Exception:
            return EngineSignal(
                "ml", "neutral", 0.0, 0.0,
                "Modèle ML indisponible pour le moment.",
            )

        score = max(min(2 * prediction.prob_up - 1, 1.0), -1.0)
        edge = prediction.test_accuracy - prediction.baseline_accuracy
        raw_confidence = max(prediction.prob_up, prediction.prob_down)
        confidence = max(min((raw_confidence - 0.5) * 2, 1.0), 0.0)
        if edge <= 0:
            confidence *= 0.5
        direction = "bullish" if score > 0.02 else "bearish" if score < -0.02 else "neutral"
        return EngineSignal(
            "ml",
            direction,
            round(score, 4),
            round(confidence, 4),
            f"Modèle ML (XGBoost + régression logistique, calibré) : "
            f"probabilité haussière {prediction.prob_up * 100:.1f} %"
            + (
                ""
                if edge > 0
                else " — ne bat pas la référence naïve sur cette période, confiance réduite en conséquence."
            ),
        )

    def _news_signal(self) -> EngineSignal:
        if self._news is None:
            return EngineSignal(
                "news", "neutral", 0.0, 0.0, "Moteur d'actualités non configuré."
            )
        try:
            sentiment: SentimentResponse = self._news.execute(limit=8)
        except Exception:
            return EngineSignal(
                "news",
                "neutral",
                0.0,
                0.0,
                "Analyse de sentiment des actualités indisponible pour le moment.",
            )

        score = max(min(sentiment.average_score, 1.0), -1.0)
        confidence = min(abs(score) * 0.6 + 0.15, 0.6)
        direction = "bullish" if score > 0.15 else "bearish" if score < -0.15 else "neutral"
        return EngineSignal(
            "news",
            direction,
            round(score, 4),
            round(confidence, 4),
            "Sentiment des actualités générales du marché (pas spécifique à "
            f"l'instrument) : score moyen {score:+.2f} sur "
            f"{len(sentiment.items)} titre(s) récent(s).",
        )

    def _macro_signal(self, as_of: datetime) -> EngineSignal:
        if self._calendar is None:
            return EngineSignal(
                "macro", "neutral", 0.0, 0.0, "Calendrier économique non configuré."
            )
        try:
            calendar: CalendarResponse = self._calendar.execute(
                as_of, as_of + timedelta(days=1)
            )
        except Exception:
            return EngineSignal(
                "macro",
                "neutral",
                0.0,
                0.0,
                "Calendrier économique indisponible pour le moment.",
            )

        upcoming = [e for e in calendar.events if e.importance == "haute"]
        if not upcoming:
            return EngineSignal(
                "macro",
                "neutral",
                0.0,
                0.2,
                "Aucun événement macroéconomique à fort impact dans les 24 h.",
            )
        names = ", ".join(e.name for e in upcoming)
        return EngineSignal(
            "macro",
            "neutral",
            0.0,
            0.35,
            f"Événement(s) macroéconomique(s) à fort impact imminent(s) "
            f"({names}) — volatilité accrue attendue, prudence sur la "
            "fiabilité des autres signaux.",
        )
