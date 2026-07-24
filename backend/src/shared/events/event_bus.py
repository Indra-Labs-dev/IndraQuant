"""Minimal in-process event bus (see docs/04, section Event-Driven /
docs/roadmap #9). Phase 1 published only `MarketDataIngested`, with zero
subscribers; the events below are published from real use cases across
the platform (prediction_engine, prediction_engine's training runner,
paper_trading, alert_center, news_intelligence, market_data's refresh
runner) and consumed by at least one real subscriber, `EventLogService`
(see `event_log.py`).
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Callable


@dataclass(frozen=True)
class MarketDataIngested:
    instrument_id: int
    timeframe: str
    candle_count: int
    ingested_at: datetime


@dataclass(frozen=True)
class PredictionCreated:
    instrument_id: int
    timeframe: str
    predicted_direction: str
    prob_up: float
    as_of: datetime


@dataclass(frozen=True)
class TrainingFinished:
    instrument_id: int
    timeframe: str
    finished_at: datetime


@dataclass(frozen=True)
class PortfolioUpdated:
    session_id: int
    instrument_id: int
    equity: float
    updated_at: datetime


@dataclass(frozen=True)
class AlertTriggered:
    alert_id: int
    instrument_id: int
    message: str
    triggered_at: datetime


@dataclass(frozen=True)
class NewsReceived:
    count: int
    fetched_at: datetime


@dataclass(frozen=True)
class MarketClosed:
    instrument_id: int
    closed_at: datetime


ALL_EVENT_TYPES: tuple[type, ...] = (
    MarketDataIngested,
    PredictionCreated,
    TrainingFinished,
    PortfolioUpdated,
    AlertTriggered,
    NewsReceived,
    MarketClosed,
)


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[type, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Callable) -> None:
        self._subscribers[event_type].append(handler)

    def subscribe_all(self, event_types: tuple[type, ...], handler: Callable) -> None:
        for event_type in event_types:
            self.subscribe(event_type, handler)

    def publish(self, event: object) -> None:
        for handler in self._subscribers[type(event)]:
            handler(event)


event_bus = EventBus()
