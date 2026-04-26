from datetime import date
from typing import List, Optional

from pydantic import BaseModel

from app.domains.dashboard.domain.entity.announcement_event import AnnouncementEvent


class AnnouncementEventResponse(BaseModel):
    date: date
    type: str
    title: str
    source: str
    url: str
    items_str: Optional[str] = None  # SEC 8-K raw Item 코드. DART는 None.

    @classmethod
    def from_entity(cls, event: AnnouncementEvent) -> "AnnouncementEventResponse":
        return cls(
            date=event.date,
            type=event.type.value,
            title=event.title,
            source=event.source,
            url=event.url,
            items_str=event.items_str,
        )


class AnnouncementsResponse(BaseModel):
    ticker: str
    chart_interval: str
    count: int
    events: List[AnnouncementEventResponse]
