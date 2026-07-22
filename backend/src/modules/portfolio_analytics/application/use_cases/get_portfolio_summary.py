from pydantic import BaseModel

from src.modules.market_data.domain.repositories import InstrumentRepository
from src.modules.paper_trading.application.dto import SessionSummary
from src.modules.paper_trading.application.use_cases.manage_sessions import (
    ManageSessionsUseCase,
)


class InstrumentAllocation(BaseModel):
    instrument_id: int
    symbol: str
    asset_class: str
    equity: float
    weight_pct: float


class PortfolioSummary(BaseModel):
    total_equity: float
    total_initial_capital: float
    total_pnl: float
    total_return_pct: float
    total_fees: float
    running_sessions: int
    stopped_sessions: int
    allocation: list[InstrumentAllocation]
    sessions: list[SessionSummary]
    explanation: str


class GetPortfolioSummaryUseCase:
    """Real aggregate view across every paper trading session (running or
    stopped) — the Portfolio Analytics module (docs/05), built by composing
    the already-tested per-session analytics rather than duplicating them."""

    def __init__(
        self,
        manage_sessions: ManageSessionsUseCase,
        instruments: InstrumentRepository,
    ) -> None:
        self._manage_sessions = manage_sessions
        self._instruments = instruments

    def execute(self) -> PortfolioSummary:
        sessions = self._manage_sessions.list_sessions().sessions

        total_equity = 0.0
        total_initial_capital = 0.0
        total_fees = 0.0
        running = 0
        stopped = 0
        equity_by_instrument: dict[int, float] = {}

        for session in sessions:
            if session.status == "running":
                running += 1
            else:
                stopped += 1

            detail = self._manage_sessions.detail(session.id)
            total_equity += detail.analytics.equity
            total_initial_capital += session.initial_capital
            total_fees += detail.analytics.fees_paid
            equity_by_instrument[session.instrument_id] = (
                equity_by_instrument.get(session.instrument_id, 0.0)
                + detail.analytics.equity
            )

        allocation: list[InstrumentAllocation] = []
        for instrument_id, equity in equity_by_instrument.items():
            instrument = self._instruments.get(instrument_id)
            allocation.append(
                InstrumentAllocation(
                    instrument_id=instrument_id,
                    symbol=instrument.symbol if instrument else f"#{instrument_id}",
                    asset_class=instrument.asset_class if instrument else "?",
                    equity=equity,
                    weight_pct=(equity / total_equity * 100.0) if total_equity > 0 else 0.0,
                )
            )
        allocation.sort(key=lambda a: a.equity, reverse=True)

        total_pnl = total_equity - total_initial_capital
        total_return_pct = (
            total_pnl / total_initial_capital if total_initial_capital > 0 else 0.0
        )

        return PortfolioSummary(
            total_equity=round(total_equity, 2),
            total_initial_capital=round(total_initial_capital, 2),
            total_pnl=round(total_pnl, 2),
            total_return_pct=round(total_return_pct, 4),
            total_fees=round(total_fees, 2),
            running_sessions=running,
            stopped_sessions=stopped,
            allocation=allocation,
            sessions=sessions,
            explanation=(
                f"Portefeuille agrégé sur {len(sessions)} session(s) de paper "
                f"trading ({running} en cours, {stopped} arrêtée(s)) : capital "
                f"initial cumulé {total_initial_capital:.2f}, valeur actuelle "
                f"{total_equity:.2f}, soit un rendement de {total_return_pct * 100:.2f} %. "
                "Simulation sans argent réel — voir la page Paper trading pour "
                "le détail par session."
            ),
        )
