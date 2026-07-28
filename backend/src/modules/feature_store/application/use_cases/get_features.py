from datetime import datetime, timedelta, timezone

from src.modules.feature_store.application.dto import FeatureVectorResponse
from src.modules.feature_store.application.service import FeatureStoreService
from src.modules.technical_analysis.application.ports import OhlcvProvider
from src.shared.kernel.errors import AppError

_TIMEFRAME_SECONDS = {
    "1s": 1, "5s": 5, "30s": 30, "1m": 60, "5m": 300,
    "15m": 900, "1h": 3_600, "4h": 14_400, "1d": 86_400,
}
_CANDLE_WINDOW = 200
_MIN_ROWS = 60


class GetFeatureVectorUseCase:
    """Direct, read-only inspection of the Feature Store's latest vector for
    an instrument — transparency endpoint (docs/01, explicable/traçable)
    consuming the exact same `FeatureStoreService` as the Meta Decision
    Engine's technical engines."""

    def __init__(self, ohlcv: OhlcvProvider, store: FeatureStoreService) -> None:
        self._ohlcv = ohlcv
        self._store = store

    async def execute(self, instrument_id: int, timeframe: str) -> FeatureVectorResponse:
        seconds = _TIMEFRAME_SECONDS.get(timeframe, 3_600)
        end = datetime.now(timezone.utc)
        start = end - timedelta(seconds=seconds * _CANDLE_WINDOW)
        response = await self._ohlcv.execute(instrument_id, timeframe, start, end, 2000)

        closes = [c.close for c in response.candles]
        volumes = [c.volume for c in response.candles]
        if len(closes) < _MIN_ROWS:
            raise AppError(
                "not_enough_data",
                f"Pas assez d'historique pour calculer les features "
                f"({len(closes)} bougies, minimum {_MIN_ROWS}).",
                422,
            )

        as_of = response.candles[-1].open_time
        vector = await self._store.get_latest(
            instrument_id, response.timeframe, as_of, closes, volumes
        )
        return FeatureVectorResponse(
            instrument_id=vector.instrument_id,
            timeframe=vector.timeframe,
            as_of=vector.as_of,
            price=vector.price,
            sma_20=vector.sma_20,
            sma_50=vector.sma_50,
            rsi_14=vector.rsi_14,
            macd_histogram=vector.macd_histogram,
            bollinger_upper=vector.bollinger_upper,
            bollinger_lower=vector.bollinger_lower,
            volatility_20=vector.volatility_20,
            volatility_z_score=vector.volatility_z_score,
            volume_z_score=vector.volume_z_score,
            return_1=vector.return_1,
        )
