from datetime import datetime
from typing import Protocol

from src.modules.market_data.application.dto import OhlcvResponse


class OhlcvProvider(Protocol):
    """Fulfilled by market_data's GetOhlcvUseCase (wired in the composition
    root) — technical_analysis never touches market_data internals."""

    def execute(
        self,
        instrument_id: int,
        timeframe_value: str,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> OhlcvResponse: ...
