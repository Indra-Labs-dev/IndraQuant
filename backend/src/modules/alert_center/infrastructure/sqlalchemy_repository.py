from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from src.shared.infrastructure.database import Base


class AlertModel(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id"), nullable=False
    )
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    condition_type: Mapped[str] = mapped_column(
        Enum(
            "price_above",
            "price_below",
            "rsi_above",
            "rsi_below",
            name="alert_condition_type",
        ),
        nullable=False,
    )
    threshold: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    message: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SqlAlchemyAlertRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, model: AlertModel) -> AlertModel:
        self._session.add(model)
        self._session.flush()
        return model

    def get(self, alert_id: int) -> AlertModel | None:
        return self._session.get(AlertModel, alert_id)

    def list_all(self) -> list[AlertModel]:
        return list(
            self._session.scalars(
                select(AlertModel).order_by(AlertModel.id.desc())
            )
        )

    def list_active(self) -> list[AlertModel]:
        return list(
            self._session.scalars(
                select(AlertModel).where(AlertModel.is_active.is_(True))
            )
        )

    def delete(self, model: AlertModel) -> None:
        self._session.delete(model)
        self._session.flush()
