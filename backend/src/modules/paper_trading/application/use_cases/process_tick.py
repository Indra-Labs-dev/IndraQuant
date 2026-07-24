import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.modules.backtesting.application.dto import StrategySpec
from src.modules.backtesting.application.service import (
    latest_target_position,
    min_history,
    trade_reasons,
)
from src.modules.paper_trading.infrastructure.sqlalchemy_repository import (
    PaperTradeModel,
    SqlAlchemyPaperTradingRepository,
)
from src.modules.technical_analysis.application.ports import OhlcvProvider
from src.shared.events.event_bus import EventBus, PortfolioUpdated

_FEE_RATE = Decimal("0.001")

_TIMEFRAME_SECONDS = {
    "1s": 1, "5s": 5, "30s": 30, "1m": 60, "5m": 300,
    "15m": 900, "1h": 3_600, "4h": 14_400, "1d": 86_400,
}


class ProcessTickUseCase:
    """One evaluation step of a running paper session: fetch fresh candles,
    compute the strategy's target position, execute the simulated order if
    the position must change."""

    def __init__(
        self,
        repository: SqlAlchemyPaperTradingRepository,
        ohlcv: OhlcvProvider,
        event_bus: EventBus | None = None,
    ) -> None:
        self._repository = repository
        self._ohlcv = ohlcv
        self._event_bus = event_bus

    def execute(self, session_id: int) -> None:
        session = self._repository.get(session_id)
        if session is None or session.status != "running":
            return

        strategy = StrategySpec(**json.loads(session.strategy_json))
        seconds = _TIMEFRAME_SECONDS.get(session.timeframe, 60)
        end = datetime.now(timezone.utc)
        start = end - timedelta(seconds=seconds * (min_history(strategy) + 5))
        response = self._ohlcv.execute(
            session.instrument_id, session.timeframe, start, end, 5000
        )
        if not response.candles:
            return

        closes = [c.close for c in response.candles]
        target = latest_target_position(strategy, closes)
        buy_reason, sell_reason = trade_reasons(strategy)
        price = Decimal(str(closes[-1]))
        holding = session.position_qty > 0

        traded = False
        if target == 1 and not holding and session.cash > 0:
            fee = session.cash * _FEE_RATE
            quantity = (session.cash - fee) / price
            session.position_qty = quantity
            session.cash = Decimal(0)
            self._repository.add_trade(
                PaperTradeModel(
                    session_id=session.id,
                    side="buy",
                    quantity=quantity,
                    price=price,
                    fee=fee,
                    reason=buy_reason,
                )
            )
            traded = True
        elif target == 0 and holding:
            gross = session.position_qty * price
            fee = gross * _FEE_RATE
            session.cash = gross - fee
            quantity = session.position_qty
            session.position_qty = Decimal(0)
            self._repository.add_trade(
                PaperTradeModel(
                    session_id=session.id,
                    side="sell",
                    quantity=quantity,
                    price=price,
                    fee=fee,
                    reason=sell_reason,
                )
            )
            traded = True

        if traded and self._event_bus is not None:
            equity = float(session.cash + session.position_qty * price)
            self._event_bus.publish(
                PortfolioUpdated(
                    session_id=session.id,
                    instrument_id=session.instrument_id,
                    equity=equity,
                    updated_at=datetime.now(timezone.utc),
                )
            )
