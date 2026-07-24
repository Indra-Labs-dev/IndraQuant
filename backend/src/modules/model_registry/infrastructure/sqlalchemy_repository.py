from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    select,
    update,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from src.shared.infrastructure.database import Base


class ModelVersionModel(Base):
    __tablename__ = "model_versions"
    __table_args__ = (UniqueConstraint("instrument_id", "timeframe", "version"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    champion_model_type: Mapped[str] = mapped_column(String(30), nullable=False)
    xgboost_accuracy: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    logistic_regression_accuracy: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    ensemble_accuracy: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    baseline_accuracy: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    training_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    is_champion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rolled_back: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )


class SqlAlchemyModelVersionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def next_version(self, instrument_id: int, timeframe: str) -> int:
        current_max = self._session.scalar(
            select(func.max(ModelVersionModel.version)).where(
                ModelVersionModel.instrument_id == instrument_id,
                ModelVersionModel.timeframe == timeframe,
            )
        )
        return (current_max or 0) + 1

    def get_current_champion(
        self, instrument_id: int, timeframe: str
    ) -> ModelVersionModel | None:
        return self._session.scalar(
            select(ModelVersionModel)
            .where(
                ModelVersionModel.instrument_id == instrument_id,
                ModelVersionModel.timeframe == timeframe,
                ModelVersionModel.is_champion.is_(True),
            )
            .order_by(ModelVersionModel.version.desc())
            .limit(1)
        )

    def add(self, model: ModelVersionModel) -> ModelVersionModel:
        self._session.add(model)
        self._session.flush()
        return model

    def clear_champion(self, instrument_id: int, timeframe: str) -> None:
        self._session.execute(
            update(ModelVersionModel)
            .where(
                ModelVersionModel.instrument_id == instrument_id,
                ModelVersionModel.timeframe == timeframe,
            )
            .values(is_champion=False)
        )

    def list_versions(
        self, instrument_id: int, timeframe: str, limit: int = 50
    ) -> list[ModelVersionModel]:
        return list(
            self._session.scalars(
                select(ModelVersionModel)
                .where(
                    ModelVersionModel.instrument_id == instrument_id,
                    ModelVersionModel.timeframe == timeframe,
                )
                .order_by(ModelVersionModel.version.desc())
                .limit(limit)
            )
        )

    def get_by_version(
        self, instrument_id: int, timeframe: str, version: int
    ) -> ModelVersionModel | None:
        return self._session.scalar(
            select(ModelVersionModel).where(
                ModelVersionModel.instrument_id == instrument_id,
                ModelVersionModel.timeframe == timeframe,
                ModelVersionModel.version == version,
            )
        )

    def mark_rolled_back_after(self, instrument_id: int, timeframe: str, version: int) -> None:
        self._session.execute(
            update(ModelVersionModel)
            .where(
                ModelVersionModel.instrument_id == instrument_id,
                ModelVersionModel.timeframe == timeframe,
                ModelVersionModel.version > version,
            )
            .values(rolled_back=True, is_champion=False)
        )

    def set_champion(self, instrument_id: int, timeframe: str, version: int) -> None:
        self.clear_champion(instrument_id, timeframe)
        self._session.execute(
            update(ModelVersionModel)
            .where(
                ModelVersionModel.instrument_id == instrument_id,
                ModelVersionModel.timeframe == timeframe,
                ModelVersionModel.version == version,
            )
            .values(is_champion=True)
        )
