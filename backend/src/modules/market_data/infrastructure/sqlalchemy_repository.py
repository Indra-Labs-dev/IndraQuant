import time
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Mapped, Session, mapped_column

from src.modules.market_data.domain.entities import Candle, Instrument
from src.modules.market_data.domain.value_objects import Timeframe
from src.shared.infrastructure.database import Base


class ExchangeModel(Base):
    __tablename__ = "exchanges"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ccxt_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class InstrumentModel(Base):
    __tablename__ = "instruments"
    __table_args__ = (UniqueConstraint("exchange_id", "symbol"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exchange_id: Mapped[int] = mapped_column(
        ForeignKey("exchanges.id"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    base_asset: Mapped[str] = mapped_column(String(15), nullable=False)
    quote_asset: Mapped[str] = mapped_column(String(15), nullable=False)
    asset_class: Mapped[str] = mapped_column(
        Enum("crypto", "equity", "forex", name="asset_class"),
        nullable=False,
        default="crypto",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class OhlcvCandleModel(Base):
    __tablename__ = "ohlcv_candles"
    __table_args__ = (UniqueConstraint("instrument_id", "timeframe", "open_time"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id"), nullable=False
    )
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    open_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )


def _to_instrument(model: InstrumentModel, exchange: ExchangeModel) -> Instrument:
    return Instrument(
        id=model.id,
        exchange_ccxt_id=exchange.ccxt_id,
        exchange_display_name=exchange.display_name,
        symbol=model.symbol,
        base_asset=model.base_asset,
        quote_asset=model.quote_asset,
        asset_class=model.asset_class,
        is_active=model.is_active,
    )


class SqlAlchemyInstrumentRepository:
    """Instruments are seeded once at bootstrap and never mutated through
    the API (no create/update/delete endpoint exists) — a short process-wide
    cache is therefore both safe and free of invalidation concerns: a
    backend restart is the only event that could change this list, and that
    already clears the cache with it (docs/roadmap #11 — cache intelligent)."""

    _list_cache: dict[tuple[str | None, str | None], tuple[float, list[Instrument]]] = {}
    _get_cache: dict[int, tuple[float, Instrument | None]] = {}
    _TTL_SECONDS = 300

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_instruments(
        self, asset_class: str | None = None, exchange: str | None = None
    ) -> list[Instrument]:
        cache_key = (asset_class, exchange)
        cached = self._list_cache.get(cache_key)
        if cached is not None and time.monotonic() - cached[0] < self._TTL_SECONDS:
            return cached[1]

        query = (
            select(InstrumentModel, ExchangeModel)
            .join(ExchangeModel, InstrumentModel.exchange_id == ExchangeModel.id)
            .where(ExchangeModel.is_active.is_(True))
            .order_by(InstrumentModel.symbol)
        )
        if asset_class:
            query = query.where(InstrumentModel.asset_class == asset_class)
        if exchange:
            query = query.where(ExchangeModel.ccxt_id == exchange)
        instruments = [
            _to_instrument(instrument, exch)
            for instrument, exch in self._session.execute(query)
        ]
        self._list_cache[cache_key] = (time.monotonic(), instruments)
        return instruments

    def get(self, instrument_id: int) -> Instrument | None:
        cached = self._get_cache.get(instrument_id)
        if cached is not None and time.monotonic() - cached[0] < self._TTL_SECONDS:
            return cached[1]

        row = self._session.execute(
            select(InstrumentModel, ExchangeModel)
            .join(ExchangeModel, InstrumentModel.exchange_id == ExchangeModel.id)
            .where(InstrumentModel.id == instrument_id)
        ).first()
        instrument = _to_instrument(row[0], row[1]) if row else None
        self._get_cache[instrument_id] = (time.monotonic(), instrument)
        return instrument


class SqlAlchemyCandleStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_range(
        self,
        instrument_id: int,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> list[Candle]:
        models = self._session.scalars(
            select(OhlcvCandleModel)
            .where(
                OhlcvCandleModel.instrument_id == instrument_id,
                OhlcvCandleModel.timeframe == timeframe.value,
                OhlcvCandleModel.open_time >= start,
                OhlcvCandleModel.open_time <= end,
            )
            .order_by(OhlcvCandleModel.open_time)
            .limit(limit)
        )
        return [
            Candle(
                open_time=m.open_time,
                open=m.open,
                high=m.high,
                low=m.low,
                close=m.close,
                volume=m.volume,
            )
            for m in models
        ]

    def latest_open_time(
        self, instrument_id: int, timeframe: Timeframe
    ) -> datetime | None:
        return self._session.scalar(
            select(func.max(OhlcvCandleModel.open_time)).where(
                OhlcvCandleModel.instrument_id == instrument_id,
                OhlcvCandleModel.timeframe == timeframe.value,
            )
        )

    def earliest_open_time(
        self, instrument_id: int, timeframe: Timeframe
    ) -> datetime | None:
        return self._session.scalar(
            select(func.min(OhlcvCandleModel.open_time)).where(
                OhlcvCandleModel.instrument_id == instrument_id,
                OhlcvCandleModel.timeframe == timeframe.value,
            )
        )

    def upsert_many(
        self, instrument_id: int, timeframe: Timeframe, candles: list[Candle]
    ) -> int:
        if not candles:
            return 0
        statement = mysql_insert(OhlcvCandleModel).values(
            [
                {
                    "instrument_id": instrument_id,
                    "timeframe": timeframe.value,
                    "open_time": c.open_time,
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": c.volume,
                }
                for c in candles
            ]
        )
        statement = statement.on_duplicate_key_update(
            open=statement.inserted.open,
            high=statement.inserted.high,
            low=statement.inserted.low,
            close=statement.inserted.close,
            volume=statement.inserted.volume,
        )
        self._session.execute(statement)
        self._session.flush()
        return len(candles)
