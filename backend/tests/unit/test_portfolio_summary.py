from datetime import datetime

from src.modules.backtesting.application.dto import StrategySpec
from src.modules.paper_trading.application.dto import SessionDetail, SessionSummary
from src.modules.portfolio_analytics.application.service import PortfolioAnalytics
from src.modules.portfolio_analytics.application.use_cases.get_portfolio_summary import (
    GetPortfolioSummaryUseCase,
)
from src.modules.risk_management.application.service import RiskReport


class FakeInstrument:
    def __init__(self, id: int, symbol: str, asset_class: str = "crypto") -> None:
        self.id = id
        self.symbol = symbol
        self.asset_class = asset_class


class FakeInstrumentRepository:
    def __init__(self, instruments: list[FakeInstrument]) -> None:
        self._instruments = instruments

    def get(self, instrument_id: int):
        return next((i for i in self._instruments if i.id == instrument_id), None)


def _session(id: int, instrument_id: int, status: str, initial_capital: float) -> SessionSummary:
    return SessionSummary(
        id=id,
        instrument_id=instrument_id,
        timeframe="1m",
        strategy=StrategySpec(),
        initial_capital=initial_capital,
        status=status,
        started_at=datetime(2026, 1, 1),
        stopped_at=None,
    )


def _detail(session: SessionSummary, equity: float, fees: float) -> SessionDetail:
    return SessionDetail(
        **session.model_dump(),
        trades=[],
        analytics=PortfolioAnalytics(
            equity=equity,
            cash=equity,
            position_quantity=0.0,
            position_value=0.0,
            pnl=equity - session.initial_capital,
            return_pct=(equity - session.initial_capital) / session.initial_capital,
            fees_paid=fees,
            trade_count=0,
        ),
        risk=RiskReport(var_95=None, max_drawdown=0.0, annualized_volatility=None, explanation=""),
    )


class FakeManageSessionsUseCase:
    def __init__(self, sessions: list[SessionSummary], details: dict[int, SessionDetail]) -> None:
        self._sessions = sessions
        self._details = details

    def list_sessions(self):
        class Response:
            sessions = self._sessions

        return Response()

    def detail(self, session_id: int) -> SessionDetail:
        return self._details[session_id]


def test_allocation_is_grouped_by_instrument_not_by_session():
    sessions = [
        _session(1, instrument_id=1, status="running", initial_capital=10_000.0),
        _session(2, instrument_id=1, status="stopped", initial_capital=10_000.0),
        _session(3, instrument_id=2, status="stopped", initial_capital=5_000.0),
    ]
    details = {
        1: _detail(sessions[0], equity=11_000.0, fees=10.0),
        2: _detail(sessions[1], equity=9_000.0, fees=5.0),
        3: _detail(sessions[2], equity=5_000.0, fees=2.0),
    }
    use_case = GetPortfolioSummaryUseCase(
        FakeManageSessionsUseCase(sessions, details),
        FakeInstrumentRepository(
            [FakeInstrument(1, "BTC/USDT"), FakeInstrument(2, "ETH/USDT")]
        ),
    )

    summary = use_case.execute()

    assert len(summary.allocation) == 2
    btc = next(a for a in summary.allocation if a.instrument_id == 1)
    assert btc.equity == 20_000.0
    assert summary.total_equity == 25_000.0
    assert summary.running_sessions == 1
    assert summary.stopped_sessions == 2


def test_weights_sum_to_roughly_one_hundred_percent():
    sessions = [
        _session(1, instrument_id=1, status="stopped", initial_capital=10_000.0),
        _session(2, instrument_id=2, status="stopped", initial_capital=10_000.0),
    ]
    details = {
        1: _detail(sessions[0], equity=6_000.0, fees=0.0),
        2: _detail(sessions[1], equity=4_000.0, fees=0.0),
    }
    use_case = GetPortfolioSummaryUseCase(
        FakeManageSessionsUseCase(sessions, details),
        FakeInstrumentRepository(
            [FakeInstrument(1, "BTC/USDT"), FakeInstrument(2, "ETH/USDT")]
        ),
    )

    summary = use_case.execute()

    assert round(sum(a.weight_pct for a in summary.allocation), 6) == 100.0
    assert summary.allocation[0].symbol == "BTC/USDT"
