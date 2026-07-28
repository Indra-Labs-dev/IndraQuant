import asyncio
from typing import Awaitable, Callable

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
    that *was* generated remains fully persisted (ADR-020). All callers now
    run directly on the event loop (async route handlers, async lifespan),
    so sessions are scheduled with plain asyncio.create_task."""

    def __init__(self, predict: Callable[[int, str], Awaitable[None]]) -> None:
        self._predict = predict
        self._tasks: dict[tuple[int, str], asyncio.Task] = {}

    def is_running(self, instrument_id: int, timeframe: str) -> bool:
        task = self._tasks.get((instrument_id, timeframe))
        return task is not None and not task.done()

    def active_sessions(self) -> list[tuple[int, str]]:
        return [key for key, task in self._tasks.items() if not task.done()]

    def start(self, instrument_id: int, timeframe: str) -> None:
        if self.is_running(instrument_id, timeframe):
            return
        interval = min(
            max(_TIMEFRAME_SECONDS.get(timeframe, 3_600), _MIN_INTERVAL_SECONDS),
            _MAX_INTERVAL_SECONDS,
        )
        key = (instrument_id, timeframe)
        self._tasks[key] = asyncio.create_task(
            self._loop_body(instrument_id, timeframe, interval)
        )

    def stop(self, instrument_id: int, timeframe: str) -> None:
        task = self._tasks.pop((instrument_id, timeframe), None)
        if task is not None:
            task.cancel()

    def stop_all(self) -> None:
        for instrument_id, timeframe in list(self._tasks):
            self.stop(instrument_id, timeframe)

    async def _loop_body(
        self, instrument_id: int, timeframe: str, interval: int
    ) -> None:
        try:
            while True:
                try:
                    await self._predict(instrument_id, timeframe)
                except Exception:
                    pass
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            pass
