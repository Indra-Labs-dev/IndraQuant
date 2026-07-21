"""Minimal in-process event bus (see docs/04, section Event-Driven).

Phase 1 publishes MarketDataIngested; the first subscribers (indicator
recalculation) arrive in Phase 2.
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


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[type, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Callable) -> None:
        self._subscribers[event_type].append(handler)

    def publish(self, event: object) -> None:
        for handler in self._subscribers[type(event)]:
            handler(event)


event_bus = EventBus()
