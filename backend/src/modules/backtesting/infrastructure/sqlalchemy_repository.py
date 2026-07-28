import json
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.backtesting.application.dto import (
    BacktestReport,
    BacktestSummary,
    StrategySpec,
)
from src.shared.infrastructure.database import Base


class BacktestRunModel(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id"), nullable=False
    )
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    strategy_json: Mapped[str] = mapped_column(Text, nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    final_equity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    total_return: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    max_drawdown: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    trade_count: Mapped[int] = mapped_column(Integer, nullable=False)
    report_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )


class SqlAlchemyBacktestRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, report: BacktestReport) -> int:
        model = BacktestRunModel(
            instrument_id=report.instrument_id,
            timeframe=report.timeframe,
            strategy_json=report.strategy.model_dump_json(),
            initial_capital=Decimal(str(report.initial_capital)),
            final_equity=Decimal(str(report.final_equity)),
            total_return=Decimal(str(round(report.total_return, 6))),
            max_drawdown=Decimal(str(round(report.max_drawdown, 6))),
            trade_count=report.trade_count,
            report_json=report.model_dump_json(exclude={"equity_curve"}),
        )
        self._session.add(model)
        await self._session.flush()
        return model.id

    async def list_runs(self, limit: int = 50) -> list[BacktestSummary]:
        models = await self._session.scalars(
            select(BacktestRunModel)
            .order_by(BacktestRunModel.created_at.desc())
            .limit(limit)
        )
        return [
            BacktestSummary(
                id=m.id,
                instrument_id=m.instrument_id,
                timeframe=m.timeframe,
                strategy=StrategySpec(**json.loads(m.strategy_json)),
                initial_capital=float(m.initial_capital),
                final_equity=float(m.final_equity),
                total_return=float(m.total_return),
                max_drawdown=float(m.max_drawdown),
                trade_count=m.trade_count,
                created_at=m.created_at,
            )
            for m in models
        ]
