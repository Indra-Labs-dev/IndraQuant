from datetime import datetime, timedelta, timezone
from itertools import combinations

from src.modules.correlation_engine.application.dto import (
    CorrelationMatrixResponse,
    PairCorrelation,
)
from src.modules.correlation_engine.domain.correlation import (
    describe_correlation,
    ewma_correlation,
    pearson,
    rolling_correlation,
    spearman,
)
from src.modules.feature_engineering.application import service as fe
from src.modules.market_data.domain.repositories import InstrumentRepository
from src.modules.technical_analysis.application.ports import OhlcvProvider
from src.shared.kernel.errors import AppError

_TIMEFRAME_SECONDS = {
    "1s": 1, "5s": 5, "30s": 30, "1m": 60, "5m": 300,
    "15m": 900, "1h": 3_600, "4h": 14_400, "1d": 86_400,
}
_CANDLE_WINDOW = 300
_MIN_PAIR_ROWS = 20


class GetCorrelationMatrixUseCase:
    """Correlation Engine (docs/roadmap #4): Pearson, Spearman, rolling and
    EWMA ("dynamic") correlation between every pair of the requested
    instruments, computed on aligned return series (never raw prices —
    correlating price levels would conflate shared long-term drift with
    actual co-movement)."""

    def __init__(self, ohlcv: OhlcvProvider, instruments: InstrumentRepository) -> None:
        self._ohlcv = ohlcv
        self._instruments = instruments

    async def execute(
        self, instrument_ids: list[int], timeframe: str, window: int = 20
    ) -> CorrelationMatrixResponse:
        unique_ids = list(dict.fromkeys(instrument_ids))
        if len(unique_ids) < 2:
            raise AppError(
                "invalid_request",
                "Il faut au moins deux instruments distincts pour calculer une corrélation.",
                422,
            )

        seconds = _TIMEFRAME_SECONDS.get(timeframe, 3_600)
        end = datetime.now(timezone.utc)
        start = end - timedelta(seconds=seconds * _CANDLE_WINDOW)

        closes_by_id: dict[int, dict[datetime, float]] = {}
        symbols: dict[int, str] = {}
        for instrument_id in unique_ids:
            instrument = await self._instruments.get(instrument_id)
            if instrument is None:
                raise AppError(
                    "instrument_not_found", f"Instrument {instrument_id} introuvable.", 404
                )
            symbols[instrument_id] = instrument.symbol
            response = await self._ohlcv.execute(instrument_id, timeframe, start, end, 2000)
            closes_by_id[instrument_id] = {c.open_time: c.close for c in response.candles}

        pairs = [
            self._pair_correlation(a, b, symbols, closes_by_id, window)
            for a, b in combinations(unique_ids, 2)
        ]

        return CorrelationMatrixResponse(
            timeframe=timeframe,
            window=window,
            instrument_ids=unique_ids,
            pairs=pairs,
            explanation=(
                f"Corrélations calculées sur les rendements (pas les prix bruts) de "
                f"{len(unique_ids)} instrument(s). Pearson mesure la relation "
                "linéaire, Spearman la relation monotone (robuste aux valeurs "
                "extrêmes) ; la corrélation glissante et la corrélation dynamique "
                "(EWMA) montrent l'évolution récente plutôt qu'une moyenne figée "
                "sur toute la période."
            ),
        )

    def _pair_correlation(
        self,
        a: int,
        b: int,
        symbols: dict[int, str],
        closes_by_id: dict[int, dict[datetime, float]],
        window: int,
    ) -> PairCorrelation:
        timestamps = sorted(set(closes_by_id[a]) & set(closes_by_id[b]))
        closes_a = [closes_by_id[a][t] for t in timestamps]
        closes_b = [closes_by_id[b][t] for t in timestamps]

        returns_a = [r for r in fe.returns(closes_a) if r is not None]
        returns_b = [r for r in fe.returns(closes_b) if r is not None]
        n = min(len(returns_a), len(returns_b))
        returns_a, returns_b = returns_a[-n:], returns_b[-n:]

        if n < _MIN_PAIR_ROWS:
            return PairCorrelation(
                instrument_a=a,
                symbol_a=symbols[a],
                instrument_b=b,
                symbol_b=symbols[b],
                pearson=None,
                spearman=None,
                rolling=None,
                dynamic=None,
                sample_size=n,
                explanation="Historique commun insuffisant pour calculer une corrélation fiable.",
            )

        p = pearson(returns_a, returns_b)
        s = spearman(returns_a, returns_b)
        rolling_series = rolling_correlation(returns_a, returns_b, min(window, n))
        last_rolling = next((v for v in reversed(rolling_series) if v is not None), None)
        dynamic_series = ewma_correlation(returns_a, returns_b, halflife=window)
        last_dynamic = next((v for v in reversed(dynamic_series) if v is not None), None)

        return PairCorrelation(
            instrument_a=a,
            symbol_a=symbols[a],
            instrument_b=b,
            symbol_b=symbols[b],
            pearson=round(p, 4) if p is not None else None,
            spearman=round(s, 4) if s is not None else None,
            rolling=round(last_rolling, 4) if last_rolling is not None else None,
            dynamic=round(last_dynamic, 4) if last_dynamic is not None else None,
            sample_size=n,
            explanation=describe_correlation(p),
        )
