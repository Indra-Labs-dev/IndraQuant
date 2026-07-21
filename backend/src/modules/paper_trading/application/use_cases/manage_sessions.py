import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.modules.backtesting.application.dto import StrategySpec
from src.modules.paper_trading.application.dto import (
    CreateSessionRequest,
    PaperTradeDto,
    SessionDetail,
    SessionsResponse,
    SessionSummary,
)
from src.modules.paper_trading.infrastructure.sqlalchemy_repository import (
    PaperSessionModel,
    SqlAlchemyPaperTradingRepository,
)
from src.modules.portfolio_analytics.application.service import (
    TradeRecord,
    compute_analytics,
)
from src.modules.risk_management.application.service import compute_risk
from src.modules.technical_analysis.application.ports import OhlcvProvider
from src.shared.kernel.errors import AppError, NotFoundError

_SECONDS_PER_YEAR = 365 * 86_400

_TIMEFRAME_SECONDS = {
    "1s": 1, "5s": 5, "30s": 30, "1m": 60, "5m": 300,
    "15m": 900, "1h": 3_600, "4h": 14_400, "1d": 86_400,
}


def _summary(model: PaperSessionModel) -> SessionSummary:
    return SessionSummary(
        id=model.id,
        instrument_id=model.instrument_id,
        timeframe=model.timeframe,
        strategy=StrategySpec(**json.loads(model.strategy_json)),
        initial_capital=float(model.initial_capital),
        status=model.status,
        started_at=model.started_at,
        stopped_at=model.stopped_at,
    )


class ManageSessionsUseCase:
    def __init__(
        self, repository: SqlAlchemyPaperTradingRepository, ohlcv: OhlcvProvider
    ) -> None:
        self._repository = repository
        self._ohlcv = ohlcv

    def create(self, request: CreateSessionRequest) -> SessionSummary:
        from src.modules.backtesting.application.service import validate_strategy

        validate_strategy(request.strategy)
        model = self._repository.add_session(
            PaperSessionModel(
                instrument_id=request.instrument_id,
                timeframe=request.timeframe,
                strategy_json=request.strategy.model_dump_json(),
                initial_capital=Decimal(str(request.initial_capital)),
                cash=Decimal(str(request.initial_capital)),
                position_qty=Decimal(0),
                status="running",
            )
        )
        return _summary(model)

    def stop(self, session_id: int) -> SessionSummary:
        model = self._repository.get(session_id)
        if model is None:
            raise NotFoundError("session_not_found", f"Session {session_id} inconnue.")
        if model.status == "running":
            model.status = "stopped"
            model.stopped_at = datetime.now(timezone.utc).replace(tzinfo=None)
        return _summary(model)

    def list_sessions(self) -> SessionsResponse:
        return SessionsResponse(
            sessions=[_summary(m) for m in self._repository.list_sessions()]
        )

    def detail(self, session_id: int) -> SessionDetail:
        model = self._repository.get(session_id)
        if model is None:
            raise NotFoundError("session_not_found", f"Session {session_id} inconnue.")

        trades = self._repository.trades_for(session_id)
        trade_records = [
            TradeRecord(
                side=t.side,
                quantity=float(t.quantity),
                price=float(t.price),
                fee=float(t.fee),
                executed_at=t.executed_at,
                reason=t.reason,
            )
            for t in trades
        ]

        seconds = _TIMEFRAME_SECONDS.get(model.timeframe, 60)
        end = datetime.now(timezone.utc)
        start = min(
            model.started_at.replace(tzinfo=timezone.utc),
            end - timedelta(seconds=seconds * 2),
        )
        response = self._ohlcv.execute(
            model.instrument_id, model.timeframe, start, end, 5000
        )
        last_price = response.candles[-1].close if response.candles else 0.0

        analytics = compute_analytics(
            float(model.initial_capital),
            float(model.cash),
            float(model.position_qty),
            last_price,
            trade_records,
        )
        equity_curve = _replay_equity(
            float(model.initial_capital), trade_records, response.candles
        )
        risk = compute_risk(equity_curve, _SECONDS_PER_YEAR / seconds)

        summary = _summary(model)
        return SessionDetail(
            **summary.model_dump(),
            trades=[PaperTradeDto(**t.model_dump()) for t in trade_records],
            analytics=analytics,
            risk=risk,
        )


def _replay_equity(initial_capital, trade_records, candles) -> list[float]:
    cash = initial_capital
    quantity = 0.0
    pending = list(trade_records)
    equity = []
    for candle in candles:
        while pending and pending[0].executed_at.replace(
            tzinfo=timezone.utc
        ) <= candle.open_time.replace(tzinfo=timezone.utc):
            trade = pending.pop(0)
            if trade.side == "buy":
                cash = 0.0
                quantity = trade.quantity
            else:
                cash = trade.quantity * trade.price - trade.fee
                quantity = 0.0
        equity.append(cash + quantity * candle.close)
    return equity
