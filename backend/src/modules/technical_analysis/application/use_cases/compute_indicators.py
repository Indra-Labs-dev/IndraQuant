from datetime import datetime

from src.modules.technical_analysis.application.dto import (
    IndicatorPoint,
    IndicatorsResponse,
)
from src.modules.technical_analysis.application.ports import OhlcvProvider
from src.modules.technical_analysis.domain import indicators
from src.shared.kernel.errors import AppError

_DEFAULT_PERIODS = {"sma": 20, "ema": 12, "rsi": 14, "bollinger": 20}


class ComputeIndicatorsUseCase:
    def __init__(self, ohlcv: OhlcvProvider) -> None:
        self._ohlcv = ohlcv

    def execute(
        self,
        instrument_id: int,
        timeframe: str,
        start: datetime,
        end: datetime,
        limit: int,
        indicator_specs: list[str],
    ) -> IndicatorsResponse:
        response = self._ohlcv.execute(instrument_id, timeframe, start, end, limit)
        closes = [c.close for c in response.candles]
        times = [c.open_time for c in response.candles]

        series: dict[str, list[IndicatorPoint]] = {}
        for spec in indicator_specs:
            name, _, raw_period = spec.partition(":")
            name = name.strip().lower()
            try:
                period = int(raw_period) if raw_period else _DEFAULT_PERIODS.get(name, 14)
            except ValueError:
                raise AppError(
                    "invalid_indicator", f"Période invalide : {spec}", 422
                )

            if name == "sma":
                series[f"sma_{period}"] = _points(times, indicators.sma(closes, period))
            elif name == "ema":
                series[f"ema_{period}"] = _points(times, indicators.ema(closes, period))
            elif name == "rsi":
                series[f"rsi_{period}"] = _points(times, indicators.rsi(closes, period))
            elif name == "macd":
                for key, values in indicators.macd(closes).items():
                    series[f"macd_{key}"] = _points(times, values)
            elif name == "bollinger":
                for key, values in indicators.bollinger(closes, period).items():
                    series[f"bollinger_{key}_{period}"] = _points(times, values)
            else:
                raise AppError(
                    "invalid_indicator", f"Indicateur inconnu : {name}", 422
                )

        return IndicatorsResponse(
            instrument_id=instrument_id, timeframe=response.timeframe, series=series
        )


def _points(
    times: list[datetime], values: list[float | None]
) -> list[IndicatorPoint]:
    return [
        IndicatorPoint(time=t, value=v)
        for t, v in zip(times, values)
        if v is not None
    ]
