import asyncio
from concurrent.futures import Future
from typing import Callable

from starlette.concurrency import run_in_threadpool

_TIMEFRAME_SECONDS = {
    "1s": 1, "5s": 5, "30s": 30, "1m": 60, "5m": 300,
    "15m": 900, "1h": 3_600, "4h": 14_400, "1d": 86_400,
}
_MIN_INTERVAL_SECONDS = 30
_MAX_INTERVAL_SECONDS = 300


class TrainingRunner:
    """Continuous training loop (ADR-024): periodically re-runs the
    Prediction Engine for a given (instrument, timeframe) so its track
    record keeps accumulating without the user manually clicking "Analyser"
    each time. Session state is in-memory only, not persisted — a backend
    restart simply stops all sessions (the user restarts them), which is an
    acceptable trade-off at this project's scale since every prediction
    that *was* generated remains fully persisted (ADR-020). Cross-thread
    scheduling mirrors PaperTradingRunner: sync route handlers run in
    FastAPI's threadpool, so tasks must be scheduled onto the main event
    loop via run_coroutine_threadsafe rather than asyncio.create_task."""

    def __init__(self, predict: Callable[[int, str], None]) -> None:
        self._predict = predict
        self._loop: asyncio.AbstractEventLoop | None = None
        self._futures: dict[tuple[int, str], Future] = {}

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def is_running(self, instrument_id: int, timeframe: str) -> bool:
        future = self._futures.get((instrument_id, timeframe))
        return future is not None and not future.done()

    def active_sessions(self) -> list[tuple[int, str]]:
        return [key for key, future in self._futures.items() if not future.done()]

    def start(self, instrument_id: int, timeframe: str) -> None:
        if self._loop is None or self.is_running(instrument_id, timeframe):
            return
        interval = min(
            max(_TIMEFRAME_SECONDS.get(timeframe, 3_600), _MIN_INTERVAL_SECONDS),
            _MAX_INTERVAL_SECONDS,
        )
        key = (instrument_id, timeframe)
        self._futures[key] = asyncio.run_coroutine_threadsafe(
            self._loop_body(instrument_id, timeframe, interval), self._loop
        )

    def stop(self, instrument_id: int, timeframe: str) -> None:
        future = self._futures.pop((instrument_id, timeframe), None)
        if future is not None:
            future.cancel()

    def stop_all(self) -> None:
        for instrument_id, timeframe in list(self._futures):
            self.stop(instrument_id, timeframe)

    async def _loop_body(
        self, instrument_id: int, timeframe: str, interval: int
    ) -> None:
        try:
            while True:
                try:
                    await run_in_threadpool(self._predict, instrument_id, timeframe)
                except Exception:
                    pass
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            pass
