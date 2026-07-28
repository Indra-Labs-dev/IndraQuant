from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class PaperSessionModel(Base):
    __tablename__ = "paper_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id"), nullable=False
    )
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    strategy_json: Mapped[str] = mapped_column(Text, nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    cash: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    position_qty: Mapped[Decimal] = mapped_column(
        Numeric(24, 8), nullable=False, default=Decimal(0)
    )
    status: Mapped[str] = mapped_column(
        Enum("running", "stopped", name="paper_session_status"),
        nullable=False,
        default="running",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PaperTradeModel(Base):
    __tablename__ = "paper_trades"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("paper_sessions.id"), nullable=False
    )
    side: Mapped[str] = mapped_column(
        Enum("buy", "sell", name="paper_trade_side"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    reason: Mapped[str] = mapped_column(String(200), nullable=False)


class SqlAlchemyPaperTradingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, session_id: int) -> PaperSessionModel | None:
        return await self._session.get(PaperSessionModel, session_id)

    async def list_sessions(self) -> list[PaperSessionModel]:
        return list(
            await self._session.scalars(
                select(PaperSessionModel).order_by(PaperSessionModel.id.desc())
            )
        )

    async def list_running_ids(self) -> list[int]:
        return list(
            await self._session.scalars(
                select(PaperSessionModel.id).where(
                    PaperSessionModel.status == "running"
                )
            )
        )

    async def trades_for(self, session_id: int) -> list[PaperTradeModel]:
        return list(
            await self._session.scalars(
                select(PaperTradeModel)
                .where(PaperTradeModel.session_id == session_id)
                .order_by(PaperTradeModel.executed_at)
            )
        )

    async def add_session(self, model: PaperSessionModel) -> PaperSessionModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def add_trade(self, model: PaperTradeModel) -> None:
        self._session.add(model)
        await self._session.flush()
