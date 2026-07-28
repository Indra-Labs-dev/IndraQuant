import asyncio
from typing import Awaitable, Callable

_CHECK_INTERVAL_SECONDS = 30


class AlertRunner:
    """Periodic in-process checker (docs/04 Event-Driven — simple polling is
    enough at Phase 6 scale; no message queue needed)."""

    def __init__(self, check_alerts: Callable[[], Awaitable[int]]) -> None:
        self._check_alerts = check_alerts
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def _loop(self) -> None:
        try:
            while True:
                try:
                    await self._check_alerts()
                except Exception:
                    pass
                await asyncio.sleep(_CHECK_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            pass
