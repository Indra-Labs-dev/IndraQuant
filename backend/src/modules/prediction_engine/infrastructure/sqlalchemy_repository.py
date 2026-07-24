from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    case,
    func,
    select,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from src.shared.infrastructure.database import Base


class PredictionModel(Base):
    __tablename__ = "predictions"
    __table_args__ = (UniqueConstraint("instrument_id", "timeframe", "as_of"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id"), nullable=False
    )
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    target_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    predicted_direction: Mapped[str] = mapped_column(
        Enum("up", "down", name="prediction_direction"), nullable=False
    )
    raw_prob_up: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    model_json: Mapped[str] = mapped_column(Text, nullable=False)
    actual_direction: Mapped[str | None] = mapped_column(
        Enum("up", "down", name="prediction_actual_direction"), nullable=True
    )
    correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    predicted_expected_return: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 8), nullable=True
    )
    predicted_low_return: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 8), nullable=True
    )
    predicted_high_return: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 8), nullable=True
    )
    actual_return: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    price_in_interval: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    shap_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )


class SqlAlchemyPredictionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_as_of(
        self, instrument_id: int, timeframe: str, as_of: datetime
    ) -> PredictionModel | None:
        return self._session.scalar(
            select(PredictionModel).where(
                PredictionModel.instrument_id == instrument_id,
                PredictionModel.timeframe == timeframe,
                PredictionModel.as_of == as_of,
            )
        )

    def add(self, model: PredictionModel) -> PredictionModel:
        self._session.add(model)
        self._session.flush()
        return model

    def get(self, prediction_id: int) -> PredictionModel | None:
        return self._session.get(PredictionModel, prediction_id)

    def list_unresolved_ready(
        self, now: datetime, limit: int = 200
    ) -> list[PredictionModel]:
        return list(
            self._session.scalars(
                select(PredictionModel)
                .where(
                    PredictionModel.resolved_at.is_(None),
                    PredictionModel.target_time <= now,
                )
                .order_by(PredictionModel.target_time)
                .limit(limit)
            )
        )

    def calibration_stats(
        self, timeframe: str, low: float, high: float
    ) -> tuple[int, float | None]:
        confidence = func.greatest(
            PredictionModel.raw_prob_up, 1 - PredictionModel.raw_prob_up
        )
        count, avg_correct = self._session.execute(
            select(
                func.count(),
                func.avg(case((PredictionModel.correct.is_(True), 1), else_=0)),
            ).where(
                PredictionModel.timeframe == timeframe,
                PredictionModel.resolved_at.is_not(None),
                confidence >= low,
                confidence < high,
            )
        ).one()
        return count or 0, float(avg_correct) if avg_correct is not None else None

    def price_calibration_stats(self, timeframe: str) -> tuple[int, float | None]:
        """Real, verified coverage of past price-interval estimates for this
        timeframe — how often the actual return actually fell inside the
        declared interval (ADR-029)."""
        count, avg_in = self._session.execute(
            select(
                func.count(),
                func.avg(case((PredictionModel.price_in_interval.is_(True), 1), else_=0)),
            ).where(
                PredictionModel.timeframe == timeframe,
                PredictionModel.price_in_interval.is_not(None),
            )
        ).one()
        return count or 0, float(avg_in) if avg_in is not None else None

    def overall_accuracy(self, timeframe: str) -> tuple[int, float | None]:
        count, avg_correct = self._session.execute(
            select(
                func.count(),
                func.avg(case((PredictionModel.correct.is_(True), 1), else_=0)),
            ).where(
                PredictionModel.timeframe == timeframe,
                PredictionModel.resolved_at.is_not(None),
            )
        ).one()
        return count or 0, float(avg_correct) if avg_correct is not None else None

    def summary_by_timeframe(self) -> list[dict]:
        rows = self._session.execute(
            select(
                PredictionModel.timeframe,
                func.sum(case((PredictionModel.resolved_at.is_not(None), 1), else_=0)),
                func.sum(case((PredictionModel.resolved_at.is_(None), 1), else_=0)),
                # No else_: unresolved rows (correct IS NULL) contribute NULL,
                # which AVG() ignores — only resolved rows count toward accuracy.
                func.avg(
                    case(
                        (PredictionModel.correct.is_(True), 1.0),
                        (PredictionModel.correct.is_(False), 0.0),
                    )
                ),
            ).group_by(PredictionModel.timeframe)
        ).all()
        return [
            {
                "timeframe": timeframe,
                "resolved": int(resolved or 0),
                "pending": int(pending or 0),
                "accuracy": float(accuracy) if accuracy is not None else None,
            }
            for timeframe, resolved, pending, accuracy in rows
        ]

    def list_recent(
        self,
        instrument_id: int | None,
        timeframe: str,
        limit: int = 100,
    ) -> list[PredictionModel]:
        query = (
            select(PredictionModel)
            .where(PredictionModel.timeframe == timeframe)
            .order_by(PredictionModel.created_at.desc())
            .limit(limit)
        )
        if instrument_id is not None:
            query = query.where(PredictionModel.instrument_id == instrument_id)
        return list(self._session.scalars(query))

    def get_latest_id(self, instrument_id: int, timeframe: str) -> int | None:
        """Cheapest possible query to detect whether new predictions landed
        since a cached read — used as a cache-invalidation key (ADR-026
        discipline) instead of the full `list_recent` fetch."""
        return self._session.scalar(
            select(func.max(PredictionModel.id)).where(
                PredictionModel.instrument_id == instrument_id,
                PredictionModel.timeframe == timeframe,
            )
        )

    def list_resolved_ordered(
        self, instrument_id: int | None, timeframe: str
    ) -> list[PredictionModel]:
        query = (
            select(PredictionModel)
            .where(
                PredictionModel.timeframe == timeframe,
                PredictionModel.resolved_at.is_not(None),
            )
            .order_by(PredictionModel.resolved_at)
        )
        if instrument_id is not None:
            query = query.where(PredictionModel.instrument_id == instrument_id)
        return list(self._session.scalars(query))
