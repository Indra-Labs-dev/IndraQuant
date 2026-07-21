from typing import Protocol

from src.modules.backtesting.application.dto import BacktestReport, BacktestSummary


class BacktestRunRepository(Protocol):
    def save(self, report: BacktestReport) -> int: ...

    def list_runs(self, limit: int = 50) -> list[BacktestSummary]: ...
