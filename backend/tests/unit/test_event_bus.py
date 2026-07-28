import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.modules.alert_center.application.use_cases.manage_alerts import (
    CheckAlertsUseCase,
)
from src.modules.alert_center.infrastructure.sqlalchemy_repository import AlertModel
from src.modules.market_data.application.dto import CandleDto, OhlcvResponse
from src.modules.paper_trading.application.use_cases.process_tick import (
    ProcessTickUseCase,
)
from src.modules.paper_trading.infrastructure.sqlalchemy_repository import (
    PaperSessionModel,
)
from src.shared.events.event_bus import (
    ALL_EVENT_TYPES,
    AlertTriggered,
    EventBus,
    MarketDataIngested,
    PortfolioUpdated,
)
from src.shared.events.event_log import EventLogService


class FakeOhlcvProvider:
    def __init__(self, closes: list[float]) -> None:
        self._closes = closes

    async def execute(self, instrument_id, timeframe, start, end, limit) -> OhlcvResponse:
        candles = [
            CandleDto(
                open_time=datetime(2026, 1, 1) + timedelta(hours=i),
                open=c,
                high=c,
                low=c,
                close=c,
                volume=100.0,
            )
            for i, c in enumerate(self._closes)
        ]
        return OhlcvResponse(instrument_id=instrument_id, timeframe=timeframe, candles=candles)


class FakeAlertRepository:
    def __init__(self, alerts: list[AlertModel]) -> None:
        self._alerts = alerts

    async def list_active(self) -> list[AlertModel]:
        return self._alerts


class FakePaperTradingRepository:
    def __init__(self, session: PaperSessionModel) -> None:
        self._session = session
        self.trades = []

    async def get(self, session_id: int) -> PaperSessionModel:
        return self._session

    async def add_trade(self, trade) -> None:
        self.trades.append(trade)


def test_event_bus_delivers_to_subscribed_handler():
    bus = EventBus()
    received = []
    bus.subscribe(MarketDataIngested, received.append)
    event = MarketDataIngested(
        instrument_id=1, timeframe="1h", candle_count=10, ingested_at=datetime.now()
    )
    bus.publish(event)
    assert received == [event]


def test_event_bus_does_not_deliver_to_other_event_types():
    bus = EventBus()
    received = []
    bus.subscribe(MarketDataIngested, received.append)
    bus.publish(
        AlertTriggered(alert_id=1, instrument_id=1, message="x", triggered_at=datetime.now())
    )
    assert received == []


def test_subscribe_all_registers_handler_for_every_event_type():
    bus = EventBus()
    log = EventLogService()
    bus.subscribe_all(ALL_EVENT_TYPES, log.record)
    bus.publish(
        PortfolioUpdated(
            session_id=1, instrument_id=1, equity=100.0, updated_at=datetime.now()
        )
    )
    assert len(log.recent()) == 1
    assert log.recent()[0]["type"] == "PortfolioUpdated"


def test_event_log_bounds_capacity_and_orders_most_recent_first():
    log = EventLogService(capacity=3)
    for i in range(5):
        log.record(
            MarketDataIngested(
                instrument_id=i, timeframe="1h", candle_count=1, ingested_at=datetime.now()
            )
        )
    recent = log.recent()
    assert len(recent) == 3
    assert [e["payload"]["instrument_id"] for e in recent] == [4, 3, 2]


def test_event_log_serializes_datetime_payload_fields():
    log = EventLogService()
    log.record(
        MarketDataIngested(
            instrument_id=1,
            timeframe="1h",
            candle_count=1,
            ingested_at=datetime(2026, 1, 1, 12, 0),
        )
    )
    payload = log.recent()[0]["payload"]
    assert payload["ingested_at"] == "2026-01-01T12:00:00"


async def test_check_alerts_publishes_alert_triggered_on_hit():
    alert = AlertModel(
        id=1,
        instrument_id=1,
        timeframe="1h",
        condition_type="price_above",
        threshold=Decimal("50"),
        is_active=True,
    )
    bus = EventBus()
    received = []
    bus.subscribe(AlertTriggered, received.append)

    use_case = CheckAlertsUseCase(
        FakeAlertRepository([alert]), FakeOhlcvProvider([40.0, 45.0, 60.0]), bus
    )
    triggered = await use_case.execute()

    assert triggered == 1
    assert alert.is_active is False
    assert len(received) == 1
    assert received[0].alert_id == 1
    assert received[0].instrument_id == 1


async def test_check_alerts_publishes_nothing_without_event_bus():
    alert = AlertModel(
        id=1,
        instrument_id=1,
        timeframe="1h",
        condition_type="price_above",
        threshold=Decimal("50"),
        is_active=True,
    )
    use_case = CheckAlertsUseCase(FakeAlertRepository([alert]), FakeOhlcvProvider([60.0] * 5))
    # Must not raise even though no event bus was provided.
    assert await use_case.execute() == 1


async def test_process_tick_publishes_portfolio_updated_on_buy():
    session = PaperSessionModel(
        id=7,
        instrument_id=1,
        timeframe="1h",
        strategy_json=json.dumps({"type": "sma_crossover", "fast": 2, "slow": 3}),
        initial_capital=Decimal("1000"),
        cash=Decimal("1000"),
        position_qty=Decimal("0"),
        status="running",
    )
    bus = EventBus()
    received = []
    bus.subscribe(PortfolioUpdated, received.append)

    closes = [float(100 + i) for i in range(10)]  # strong uptrend -> long signal
    use_case = ProcessTickUseCase(
        FakePaperTradingRepository(session), FakeOhlcvProvider(closes), bus
    )
    await use_case.execute(7)

    assert len(received) == 1
    assert received[0].session_id == 7
    assert received[0].equity > 0
