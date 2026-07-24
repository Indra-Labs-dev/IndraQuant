from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from src.composition_root import get_current_user, get_event_log_service
from src.modules.auth.application.dto import UserProfile
from src.shared.events.event_log import EventLogService

router = APIRouter(prefix="/events", tags=["events"])


class RecentEventsResponse(BaseModel):
    events: list[dict]


@router.get("/recent")
def get_recent_events(
    limit: int = Query(default=50, ge=1, le=200),
    _: UserProfile = Depends(get_current_user),
    log: EventLogService = Depends(get_event_log_service),
) -> RecentEventsResponse:
    return RecentEventsResponse(events=log.recent(limit))
