from datetime import datetime

from src.modules.technical_analysis.application.dto import (
    VolumeProfileBucketDto,
    VolumeProfileResponse,
)
from src.modules.technical_analysis.application.ports import OhlcvProvider
from src.modules.technical_analysis.domain import indicators
from src.shared.kernel.errors import AppError


class GetVolumeProfileUseCase:
    """Volume Profile (docs/roadmap #11): a histogram of traded volume by
    price level over the window, plus the Point of Control (the most-
    traded price) — a different shape from the per-candle time series the
    other indicators produce, so it gets its own endpoint."""

    def __init__(self, ohlcv: OhlcvProvider) -> None:
        self._ohlcv = ohlcv

    async def execute(
        self,
        instrument_id: int,
        timeframe: str,
        start: datetime,
        end: datetime,
        limit: int,
        bins: int = 10,
    ) -> VolumeProfileResponse:
        response = await self._ohlcv.execute(instrument_id, timeframe, start, end, limit)
        if not response.candles:
            raise AppError("not_enough_data", "Aucune bougie sur la période.", 422)

        highs = [c.high for c in response.candles]
        lows = [c.low for c in response.candles]
        closes = [c.close for c in response.candles]
        volumes = [c.volume for c in response.candles]

        profile = indicators.volume_profile(highs, lows, closes, volumes, bins)
        poc = indicators.point_of_control(profile)

        return VolumeProfileResponse(
            instrument_id=instrument_id,
            timeframe=response.timeframe,
            buckets=[
                VolumeProfileBucketDto(
                    price_low=b.price_low, price_high=b.price_high, volume=b.volume
                )
                for b in profile
            ],
            point_of_control=(
                VolumeProfileBucketDto(
                    price_low=poc.price_low, price_high=poc.price_high, volume=poc.volume
                )
                if poc is not None
                else None
            ),
            explanation=(
                f"Profil de volume sur {len(response.candles)} bougies "
                f"{response.timeframe}, {bins} tranches de prix. "
                + (
                    f"Point de contrôle (prix le plus échangé) : "
                    f"{poc.price_low:.2f} – {poc.price_high:.2f}."
                    if poc is not None
                    else "Aucune donnée exploitable."
                )
            ),
        )
