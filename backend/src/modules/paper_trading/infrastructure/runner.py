import asyncio
from concurrent.futures import Future
from typing import Callable

from starlette.concurrency import run_in_threadpool

_MIN_POLL_SECONDS = 2
_MAX_POLL_SECONDS = 30

_TIMEFRAME_SECONDS = {
    "1s": 1, "5s": 5, "30s": 30, "1m": 60, "5m": 300,
    "15m": 900, "1h": 3_600, "4h": 14_400, "1d": 86_400,
}


class PaperTradingRunner:
    """Keeps one polling coroutine per running paper session on the main
    event loop. start/stop are callable from worker threads (sync routes),
    hence the run_coroutine_threadsafe indirection."""

    def __init__(self, process_tick: Callable[[int], None]) -> None:
        self._process_tick = process_tick
        self._loop: asyncio.AbstractEventLoop | None = None
        self._futures: dict[int, Future] = {}

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def start(self, session_id: int, timeframe: str) -> None:
        if self._loop is None:
            return
        existing = self._futures.get(session_id)
        if existing is not None and not existing.done():
            return
        poll = min(
            max(_TIMEFRAME_SECONDS.get(timeframe, 60), _MIN_POLL_SECONDS),
            _MAX_POLL_SECONDS,
        )
        self._futures[session_id] = asyncio.run_coroutine_threadsafe(
            self._session_loop(session_id, poll), self._loop
        )

    def stop(self, session_id: int) -> None:
        future = self._futures.pop(session_id, None)
        if future is not None:
            future.cancel()

    def stop_all(self) -> None:
        for session_id in list(self._futures):
            self.stop(session_id)

    async def _session_loop(self, session_id: int, poll_seconds: int) -> None:
        try:
            while True:
                try:
                    await run_in_threadpool(self._process_tick, session_id)
                except Exception:
                    # Transient failure (exchange/db): retry on next tick.
                    pass
                await asyncio.sleep(poll_seconds)
        except asyncio.CancelledError:
            pass
