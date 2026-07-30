from src.modules.market_data.application.dto import InstrumentDto
from src.modules.market_data.application.use_cases.list_instruments import (
    ListInstrumentsUseCase,
)

_COMMON_QUOTE_ASSETS = ("USDT", "USD")


async def resolve_instrument(
    symbol: str, instruments: ListInstrumentsUseCase
) -> InstrumentDto | None:
    """The model sometimes writes a sloppy symbol ("BTC" instead of
    "BTC/USDT") when it invents tool arguments — falls back from an exact
    match to a base-asset guess before giving up, so a chat tool call never
    fails on a symbol a human would obviously recognize."""
    catalog = (await instruments.execute()).instruments
    normalized = symbol.strip().upper()

    for instrument in catalog:
        if instrument.symbol.upper() == normalized:
            return instrument

    if "/" not in normalized:
        for quote in _COMMON_QUOTE_ASSETS:
            guess = f"{normalized}/{quote}"
            for instrument in catalog:
                if instrument.symbol.upper() == guess:
                    return instrument

    base = normalized.split("/")[0]
    for instrument in catalog:
        if instrument.symbol.upper().split("/")[0] == base:
            return instrument

    return None
