from datetime import datetime, timedelta, timezone

from src.modules.market_regime.application.dto import MarketRegimeResponse
from src.modules.market_regime.domain.detector import MarketRegime, detect_regime
from src.modules.technical_analysis.application.ports import OhlcvProvider
from src.shared.kernel.errors import AppError

_TIMEFRAME_SECONDS = {
    "1s": 1, "5s": 5, "30s": 30, "1m": 60, "5m": 300,
    "15m": 900, "1h": 3_600, "4h": 14_400, "1d": 86_400,
}
_CANDLE_WINDOW = 200
_MIN_ROWS = 60


class GetMarketRegimeUseCase:
    """Market Regime Detector (docs/roadmap #2): classifies the current
    trend/volatility regime from price action alone. Consumed directly via
    its own endpoint, and by `GetMetaDecisionUseCase` to adapt fusion
    weights and confidence to the prevailing regime."""

    def __init__(self, ohlcv: OhlcvProvider) -> None:
        self._ohlcv = ohlcv

    def execute(self, instrument_id: int, timeframe: str) -> MarketRegimeResponse:
        regime = self.detect(instrument_id, timeframe)
        return MarketRegimeResponse(
            instrument_id=instrument_id,
            timeframe=timeframe,
            trend=regime.trend,
            volatility=regime.volatility,
            is_trending=regime.is_trending,
            is_panic=regime.is_panic,
            confidence=regime.confidence,
            label=regime.label,
            explanation=regime.explanation,
        )

    def detect(self, instrument_id: int, timeframe: str) -> MarketRegime:
        seconds = _TIMEFRAME_SECONDS.get(timeframe, 3_600)
        end = datetime.now(timezone.utc)
        start = end - timedelta(seconds=seconds * _CANDLE_WINDOW)
        response = self._ohlcv.execute(instrument_id, timeframe, start, end, 2000)
        closes = [c.close for c in response.candles]
        if len(closes) < _MIN_ROWS:
            raise AppError(
                "not_enough_data",
                f"Pas assez d'historique pour détecter le régime de marché "
                f"({len(closes)} bougies, minimum {_MIN_ROWS}).",
                422,
            )
        return detect_regime(closes)
