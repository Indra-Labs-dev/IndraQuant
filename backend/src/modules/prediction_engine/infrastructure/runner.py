import asyncio
from typing import Awaitable, Callable

_CHECK_INTERVAL_SECONDS = 30


class PredictionResolverRunner:
    """Periodic in-process resolver (same pattern as AlertRunner) — checks
    pending predictions and records real outcomes, feeding the calibration
    loop described in ADR-020."""

    def __init__(self, resolve: Callable[[], Awaitable[int]]) -> None:
        self._resolve = resolve
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
                    await self._resolve()
                except Exception:
                    pass
                await asyncio.sleep(_CHECK_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            pass
