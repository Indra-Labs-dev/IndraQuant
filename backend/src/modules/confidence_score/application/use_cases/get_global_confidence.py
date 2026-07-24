from datetime import datetime, timedelta, timezone

from src.modules.confidence_score.application.dto import (
    ConfidenceFactorDto,
    GlobalConfidenceResponse,
)
from src.modules.confidence_score.domain.scoring import (
    aggregate_global_score,
    correlation_confirmation_factor,
    volatility_penalty_factor,
)
from src.modules.correlation_engine.application.use_cases.get_correlation_matrix import (
    GetCorrelationMatrixUseCase,
)
from src.modules.market_data.domain.repositories import InstrumentRepository
from src.modules.meta_decision_engine.application.use_cases.get_meta_decision import (
    GetMetaDecisionUseCase,
)
from src.modules.technical_analysis.application.ports import OhlcvProvider

_TIMEFRAME_SECONDS = {
    "1s": 1, "5s": 5, "30s": 30, "1m": 60, "5m": 300,
    "15m": 900, "1h": 3_600, "4h": 14_400, "1d": 86_400,
}
_MAX_PEERS = 4


class GetGlobalConfidenceScoreUseCase:
    """Score global de confiance (docs/roadmap #3): composes the already
    disagreement-aware Meta Decision Engine (IA + Analyse Technique + Smart
    Money Concepts + Sentiment + Régime) with two additional, explicit
    dimensions the roadmap asks for — Corrélations (do same-asset-class
    peers confirm this direction, or is it unconfirmed/idiosyncratic?) and
    Volatilité (an explicit, named penalty when the regime is abnormally
    volatile) — into one explained 0-100 trust meter."""

    def __init__(
        self,
        meta_decision: GetMetaDecisionUseCase,
        correlation: GetCorrelationMatrixUseCase,
        instruments: InstrumentRepository,
        ohlcv: OhlcvProvider,
    ) -> None:
        self._meta_decision = meta_decision
        self._correlation = correlation
        self._instruments = instruments
        self._ohlcv = ohlcv

    def execute(self, instrument_id: int, timeframe: str) -> GlobalConfidenceResponse:
        decision = self._meta_decision.execute(instrument_id, timeframe)

        correlation_factor = self._correlation_factor(
            instrument_id, timeframe, decision.direction
        )
        volatility_factor = volatility_penalty_factor(
            decision.regime.volatility if decision.regime is not None else None
        )

        result = aggregate_global_score(
            decision.confidence, [correlation_factor, volatility_factor]
        )

        return GlobalConfidenceResponse(
            instrument_id=instrument_id,
            timeframe=decision.timeframe,
            direction=decision.direction,
            score=result.score,
            level=result.level,
            base_confidence=result.base_confidence,
            factors=[
                ConfidenceFactorDto(
                    name=f.name, multiplier=f.multiplier, explanation=f.explanation
                )
                for f in result.factors
            ],
            explanation=result.explanation,
        )

    def _correlation_factor(self, instrument_id: int, timeframe: str, direction: str):
        try:
            target = self._instruments.get(instrument_id)
            if target is None:
                return correlation_confirmation_factor(direction, [])

            peer_ids = [
                peer.id
                for peer in self._instruments.list_instruments(asset_class=target.asset_class)
                if peer.id != instrument_id
            ][:_MAX_PEERS]
            if not peer_ids:
                return correlation_confirmation_factor(direction, [])

            matrix = self._correlation.execute([instrument_id, *peer_ids], timeframe)
            pearson_by_peer: dict[int, float | None] = {}
            for pair in matrix.pairs:
                other = (
                    pair.instrument_b if pair.instrument_a == instrument_id else pair.instrument_a
                )
                if pair.instrument_a == instrument_id or pair.instrument_b == instrument_id:
                    pearson_by_peer[other] = pair.pearson

            peers = [
                (pearson_by_peer.get(peer_id), self._peer_direction(peer_id, timeframe))
                for peer_id in peer_ids
            ]
            return correlation_confirmation_factor(direction, peers)
        except Exception:
            return correlation_confirmation_factor(direction, [])

    def _peer_direction(self, peer_id: int, timeframe: str) -> str:
        seconds = _TIMEFRAME_SECONDS.get(timeframe, 3_600)
        end = datetime.now(timezone.utc)
        start = end - timedelta(seconds=seconds * 5)
        try:
            response = self._ohlcv.execute(peer_id, timeframe, start, end, 5)
        except Exception:
            return "neutral"
        closes = [c.close for c in response.candles]
        if len(closes) < 2 or closes[-2] == 0:
            return "neutral"
        change = (closes[-1] - closes[-2]) / closes[-2]
        if change > 0.0005:
            return "bullish"
        if change < -0.0005:
            return "bearish"
        return "neutral"
