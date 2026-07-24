"""Bounded in-memory log of recent domain events (docs/roadmap #9) — a
real subscriber proving the event bus actually delivers events end to end,
and giving visibility into cross-module activity without coupling those
modules to each other."""

from collections import deque
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone


def _jsonable(payload: dict) -> dict:
    return {
        key: (value.isoformat() if isinstance(value, datetime) else value)
        for key, value in payload.items()
    }


class EventLogService:
    def __init__(self, capacity: int = 200) -> None:
        self._capacity = capacity
        self._events: deque[tuple[str, datetime, dict]] = deque(maxlen=capacity)

    def record(self, event: object) -> None:
        payload = asdict(event) if is_dataclass(event) else {}
        self._events.append(
            (type(event).__name__, datetime.now(timezone.utc), payload)
        )

    def recent(self, limit: int = 50) -> list[dict]:
        ordered = list(self._events)[-limit:]
        return [
            {
                "type": name,
                "recorded_at": recorded_at.isoformat(),
                "payload": _jsonable(payload),
            }
            for name, recorded_at, payload in reversed(ordered)
        ]
