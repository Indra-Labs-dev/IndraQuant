from datetime import datetime

from src.modules.technical_analysis.application.dto import (
    IndicatorPoint,
    IndicatorsResponse,
)
from src.modules.technical_analysis.application.ports import OhlcvProvider
from src.modules.technical_analysis.domain import indicators
from src.shared.kernel.errors import AppError

_DEFAULT_PERIODS = {
    "sma": 20, "ema": 12, "rsi": 14, "bollinger": 20,
    "vwap": 20, "atr": 14, "adx": 14, "donchian": 20, "keltner": 20,
    "mfi": 14, "cci": 20, "williams_r": 14, "cmf": 20, "ulcer": 14,
    "momentum": 10, "volatility_clustering": 30,
}


class ComputeIndicatorsUseCase:
    def __init__(self, ohlcv: OhlcvProvider) -> None:
        self._ohlcv = ohlcv

    async def execute(
        self,
        instrument_id: int,
        timeframe: str,
        start: datetime,
        end: datetime,
        limit: int,
        indicator_specs: list[str],
    ) -> IndicatorsResponse:
        response = await self._ohlcv.execute(instrument_id, timeframe, start, end, limit)
        closes = [c.close for c in response.candles]
        highs = [c.high for c in response.candles]
        lows = [c.low for c in response.candles]
        volumes = [c.volume for c in response.candles]
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
            elif name == "vwap":
                series[f"vwap_{period}"] = _points(
                    times, indicators.vwap(highs, lows, closes, volumes, period)
                )
            elif name == "atr":
                series[f"atr_{period}"] = _points(
                    times, indicators.atr(highs, lows, closes, period)
                )
            elif name == "adx":
                series[f"adx_{period}"] = _points(
                    times, indicators.adx(highs, lows, closes, period)
                )
            elif name == "donchian":
                for key, values in indicators.donchian(highs, lows, period).items():
                    series[f"donchian_{key}_{period}"] = _points(times, values)
            elif name == "keltner":
                for key, values in indicators.keltner(highs, lows, closes, period).items():
                    series[f"keltner_{key}_{period}"] = _points(times, values)
            elif name == "obv":
                series["obv"] = _points(times, indicators.obv(closes, volumes))
            elif name == "mfi":
                series[f"mfi_{period}"] = _points(
                    times, indicators.mfi(highs, lows, closes, volumes, period)
                )
            elif name == "cci":
                series[f"cci_{period}"] = _points(
                    times, indicators.cci(highs, lows, closes, period)
                )
            elif name == "williams_r":
                series[f"williams_r_{period}"] = _points(
                    times, indicators.williams_r(highs, lows, closes, period)
                )
            elif name == "cmf":
                series[f"cmf_{period}"] = _points(
                    times, indicators.chaikin_money_flow(highs, lows, closes, volumes, period)
                )
            elif name == "ulcer":
                series[f"ulcer_{period}"] = _points(
                    times, indicators.ulcer_index(closes, period)
                )
            elif name == "momentum":
                series[f"momentum_{period}"] = _points(
                    times, indicators.momentum(closes, period)
                )
            elif name == "order_flow":
                series["order_flow"] = _points(
                    times, indicators.order_flow_proxy(highs, lows, closes, volumes)
                )
            elif name == "volatility_clustering":
                series[f"volatility_clustering_{period}"] = _points(
                    times, indicators.volatility_clustering(closes, period)
                )
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
