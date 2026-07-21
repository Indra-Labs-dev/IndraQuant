from datetime import datetime, timedelta, timezone
from decimal import Decimal

from pydantic import BaseModel, Field

from src.modules.alert_center.infrastructure.sqlalchemy_repository import (
    AlertModel,
    SqlAlchemyAlertRepository,
)
from src.modules.technical_analysis.application import service as ta
from src.modules.technical_analysis.application.ports import OhlcvProvider
from src.shared.kernel.errors import NotFoundError

_TIMEFRAME_SECONDS = {
    "1s": 1, "5s": 5, "30s": 30, "1m": 60, "5m": 300,
    "15m": 900, "1h": 3_600, "4h": 14_400, "1d": 86_400,
}

_CONDITION_LABELS = {
    "price_above": "prix au-dessus de",
    "price_below": "prix en dessous de",
    "rsi_above": "RSI 14 au-dessus de",
    "rsi_below": "RSI 14 en dessous de",
}


class CreateAlertRequest(BaseModel):
    instrument_id: int
    timeframe: str = "1m"
    condition_type: str = Field(pattern="^(price_above|price_below|rsi_above|rsi_below)$")
    threshold: float


class AlertDto(BaseModel):
    id: int
    instrument_id: int
    timeframe: str
    condition_type: str
    threshold: float
    is_active: bool
    message: str | None
    created_at: datetime
    triggered_at: datetime | None


class AlertsResponse(BaseModel):
    alerts: list[AlertDto]


def _dto(model: AlertModel) -> AlertDto:
    return AlertDto(
        id=model.id,
        instrument_id=model.instrument_id,
        timeframe=model.timeframe,
        condition_type=model.condition_type,
        threshold=float(model.threshold),
        is_active=model.is_active,
        message=model.message,
        created_at=model.created_at,
        triggered_at=model.triggered_at,
    )


class ManageAlertsUseCase:
    def __init__(self, repository: SqlAlchemyAlertRepository) -> None:
        self._repository = repository

    def create(self, request: CreateAlertRequest) -> AlertDto:
        model = self._repository.add(
            AlertModel(
                instrument_id=request.instrument_id,
                timeframe=request.timeframe,
                condition_type=request.condition_type,
                threshold=Decimal(str(request.threshold)),
                is_active=True,
            )
        )
        return _dto(model)

    def list_alerts(self) -> AlertsResponse:
        return AlertsResponse(
            alerts=[_dto(m) for m in self._repository.list_all()]
        )

    def delete(self, alert_id: int) -> None:
        model = self._repository.get(alert_id)
        if model is None:
            raise NotFoundError("alert_not_found", f"Alerte {alert_id} inconnue.")
        self._repository.delete(model)


class CheckAlertsUseCase:
    """One evaluation pass over active alerts (called by the background
    runner). Triggered alerts become inactive (one-shot) with an explained
    message."""

    def __init__(
        self, repository: SqlAlchemyAlertRepository, ohlcv: OhlcvProvider
    ) -> None:
        self._repository = repository
        self._ohlcv = ohlcv

    def execute(self) -> int:
        triggered = 0
        for alert in self._repository.list_active():
            seconds = _TIMEFRAME_SECONDS.get(alert.timeframe, 60)
            end = datetime.now(timezone.utc)
            start = end - timedelta(seconds=seconds * 40)
            try:
                response = self._ohlcv.execute(
                    alert.instrument_id, alert.timeframe, start, end, 5000
                )
            except Exception:
                continue
            if not response.candles:
                continue

            closes = [c.close for c in response.candles]
            price = closes[-1]
            threshold = float(alert.threshold)
            observed: float | None = None

            if alert.condition_type in ("price_above", "price_below"):
                observed = price
                hit = (
                    price > threshold
                    if alert.condition_type == "price_above"
                    else price < threshold
                )
            else:
                rsi_values = ta.rsi(closes, 14)
                observed = rsi_values[-1]
                if observed is None:
                    continue
                hit = (
                    observed > threshold
                    if alert.condition_type == "rsi_above"
                    else observed < threshold
                )

            if hit:
                alert.is_active = False
                alert.triggered_at = datetime.now(timezone.utc).replace(tzinfo=None)
                alert.message = (
                    f"Alerte déclenchée : {_CONDITION_LABELS[alert.condition_type]} "
                    f"{threshold:g} — valeur observée {observed:.2f} "
                    f"({alert.timeframe})."
                )
                triggered += 1
        return triggered
