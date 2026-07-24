import json
from dataclasses import asdict
from datetime import datetime

from src.modules.feature_engineering.application import service as fe
from src.modules.feature_store.domain.feature_vector import FeatureVector
from src.modules.technical_analysis.application import service as ta

_VOL_WINDOW = 20
_VOL_HISTORY = 90
# Cache hygiene only — correctness comes from the cache key including
# `as_of` (same discipline as the Prediction Engine cache, ADR-026): a
# newly-closed candle always changes the key and misses regardless of TTL.
_CACHE_TTL_SECONDS = 21_600


class FeatureStoreService:
    """Computes the shared technical `FeatureVector` for an instrument's
    latest candle exactly once per (instrument, timeframe, as_of), caching
    the result in Redis so every other consumer within the same candle's
    lifetime reads the cached vector instead of recomputing SMA/RSI/MACD/
    Bollinger/volatility from raw closes."""

    def __init__(self, cache=None) -> None:
        self._cache = cache

    def get_latest(
        self,
        instrument_id: int,
        timeframe: str,
        as_of: datetime,
        closes: list[float],
        volumes: list[float],
    ) -> FeatureVector:
        cache_key = f"feature_store:{instrument_id}:{timeframe}:{as_of.isoformat()}"
        if self._cache is not None:
            try:
                cached = self._cache.get(cache_key)
                if cached:
                    payload = json.loads(cached)
                    return FeatureVector(
                        instrument_id=instrument_id,
                        timeframe=timeframe,
                        as_of=as_of,
                        **payload,
                    )
            except Exception:
                pass

        vector = self._compute(instrument_id, timeframe, as_of, closes, volumes)

        if self._cache is not None:
            try:
                payload = asdict(vector)
                payload.pop("instrument_id")
                payload.pop("timeframe")
                payload.pop("as_of")
                self._cache.set(cache_key, json.dumps(payload), ex=_CACHE_TTL_SECONDS)
            except Exception:
                pass
        return vector

    def _compute(
        self,
        instrument_id: int,
        timeframe: str,
        as_of: datetime,
        closes: list[float],
        volumes: list[float],
    ) -> FeatureVector:
        sma20 = fe.rolling_mean(closes, 20)
        sma50 = fe.rolling_mean(closes, 50)
        rsi14 = ta.rsi(closes, 14)
        histogram = ta.macd(closes)["histogram"]
        bands = ta.bollinger(closes, 20, 2.0)
        returns = fe.returns(closes)
        vols = fe.rolling_std(
            [r if r is not None else 0.0 for r in returns], _VOL_WINDOW
        )
        vol_mean = fe.rolling_mean(volumes, _VOL_WINDOW)
        vol_std = fe.rolling_std(volumes, _VOL_WINDOW)

        valid_vols = [v for v in vols[-_VOL_HISTORY:] if v is not None]
        current_vol = vols[-1]
        volatility_z_score = None
        if current_vol is not None and len(valid_vols) >= 10:
            mean_v = sum(valid_vols) / len(valid_vols)
            std_v = (sum((v - mean_v) ** 2 for v in valid_vols) / len(valid_vols)) ** 0.5
            volatility_z_score = (current_vol - mean_v) / std_v if std_v > 0 else 0.0

        volume_z_score = None
        if vol_mean[-1] is not None and vol_std[-1] and vol_std[-1] > 0:
            volume_z_score = (volumes[-1] - vol_mean[-1]) / vol_std[-1]

        return FeatureVector(
            instrument_id=instrument_id,
            timeframe=timeframe,
            as_of=as_of,
            price=closes[-1],
            sma_20=sma20[-1],
            sma_50=sma50[-1],
            rsi_14=rsi14[-1],
            macd_histogram=histogram[-1],
            bollinger_upper=bands["upper"][-1],
            bollinger_lower=bands["lower"][-1],
            volatility_20=vols[-1],
            volatility_z_score=volatility_z_score,
            volume_z_score=volume_z_score,
            return_1=returns[-1],
        )
