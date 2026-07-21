from datetime import date, datetime, timedelta

from pydantic import BaseModel

from src.modules.economic_calendar.infrastructure.static_source import (
    generate_events,
)


class CalendarEvent(BaseModel):
    date: date
    name: str
    importance: str
    note: str


class CalendarResponse(BaseModel):
    events: list[CalendarEvent]
    source_note: str


class ListEventsUseCase:
    def execute(self, start: datetime, end: datetime) -> CalendarResponse:
        events = [
            CalendarEvent(**event)
            for event in generate_events(start.date(), end.date())
        ]
        events.sort(key=lambda e: e.date)
        return CalendarResponse(
            events=events,
            source_note=(
                "Source statique (ADR-018) : dates FOMC officielles 2026, "
                "CPI et NFP générés par règle récurrente — les dates CPI/NFP "
                "sont approximatives (±1 jour)."
            ),
        )


def default_range() -> tuple[datetime, datetime]:
    today = datetime.now()
    return today, today + timedelta(days=45)
