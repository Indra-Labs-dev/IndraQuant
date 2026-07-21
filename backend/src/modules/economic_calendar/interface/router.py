from datetime import datetime

from fastapi import APIRouter, Depends, Query

from src.composition_root import get_current_user
from src.modules.auth.application.dto import UserProfile
from src.modules.economic_calendar.application.use_cases.list_events import (
    CalendarResponse,
    ListEventsUseCase,
    default_range,
)

router = APIRouter(prefix="/calendar", tags=["economic-calendar"])


@router.get("/events")
def list_events(
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    _: UserProfile = Depends(get_current_user),
) -> CalendarResponse:
    start, end = default_range()
    return ListEventsUseCase().execute(from_ or start, to or end)
