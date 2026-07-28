import asyncio
from typing import Awaitable, Callable

_MIN_POLL_SECONDS = 2
_MAX_POLL_SECONDS = 30

_TIMEFRAME_SECONDS = {
    "1s": 1, "5s": 5, "30s": 30, "1m": 60, "5m": 300,
    "15m": 900, "1h": 3_600, "4h": 14_400, "1d": 86_400,
}


class PaperTradingRunner:
    """Keeps one polling coroutine per running paper session on the main
    event loop. Callers (route handlers, lifespan startup) all run directly
    on the event loop now that the whole stack is async, so sessions are
    scheduled with plain asyncio.create_task — no cross-thread indirection
    needed."""

    def __init__(self, process_tick: Callable[[int], Awaitable[None]]) -> None:
        self._process_tick = process_tick
        self._tasks: dict[int, asyncio.Task] = {}

    def start(self, session_id: int, timeframe: str) -> None:
        existing = self._tasks.get(session_id)
        if existing is not None and not existing.done():
            return
        poll = min(
            max(_TIMEFRAME_SECONDS.get(timeframe, 60), _MIN_POLL_SECONDS),
            _MAX_POLL_SECONDS,
        )
        self._tasks[session_id] = asyncio.create_task(
            self._session_loop(session_id, poll)
        )

    def stop(self, session_id: int) -> None:
        task = self._tasks.pop(session_id, None)
        if task is not None:
            task.cancel()

    def stop_all(self) -> None:
        for session_id in list(self._tasks):
            self.stop(session_id)

    async def _session_loop(self, session_id: int, poll_seconds: int) -> None:
        try:
            while True:
                try:
                    await self._process_tick(session_id)
                except Exception:
                    # Transient failure (exchange/db): retry on next tick.
                    pass
                await asyncio.sleep(poll_seconds)
        except asyncio.CancelledError:
            pass
