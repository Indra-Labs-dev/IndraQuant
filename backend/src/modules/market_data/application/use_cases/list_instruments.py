from src.modules.market_data.application.dto import InstrumentDto, InstrumentsResponse
from src.modules.market_data.domain.repositories import InstrumentRepository


class ListInstrumentsUseCase:
    def __init__(self, instruments: InstrumentRepository) -> None:
        self._instruments = instruments

    def execute(
        self, asset_class: str | None = None, exchange: str | None = None
    ) -> InstrumentsResponse:
        return InstrumentsResponse(
            instruments=[
                InstrumentDto(
                    id=i.id,
                    symbol=i.symbol,
                    exchange=i.exchange_ccxt_id,
                    asset_class=i.asset_class,
                )
                for i in self._instruments.list_instruments(asset_class, exchange)
                if i.is_active
            ]
        )
