from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Instrument:
    id: int
    exchange_ccxt_id: str
    exchange_display_name: str
    symbol: str
    base_asset: str
    quote_asset: str
    asset_class: str
    is_active: bool


@dataclass(frozen=True)
class Candle:
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
