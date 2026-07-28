import asyncio
from typing import Awaitable, Callable

_CYCLE_SECONDS = 300


class MarketDataRefreshRunner:
    """Periodic in-process refresher (same pattern as AlertRunner /
    PredictionResolverRunner) that proactively keeps the most-used
    timeframes warm in storage, rather than only ever fetching on-demand
    when a user happens to request them (ADR-030). Reuses the already-
    tested read-through ingestion in `GetOhlcvUseCase` — this runner is
    just a scheduler, no ingestion logic of its own."""

    def __init__(self, refresh_all: Callable[[], Awaitable[int]]) -> None:
        self._refresh_all = refresh_all
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
                    await self._refresh_all()
                except Exception:
                    pass
                await asyncio.sleep(_CYCLE_SECONDS)
        except asyncio.CancelledError:
            pass
