from datetime import datetime

from pydantic import BaseModel

from app.domains.hermes.domain.entity.hermes_entry import HermesEntry


class HermesEntryResponse(BaseModel):
    id: str
    title: str
    type: str
    content: str
    summary: str
    tags: list[str]
    project: str
    source: str
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_entity(cls, entry: HermesEntry) -> "HermesEntryResponse":
        return cls(
            id=entry.id,
            title=entry.title,
            type=entry.type.value,
            content=entry.content,
            summary=entry.summary(),
            tags=entry.tags,
            project=entry.project,
            source=entry.source,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )


class HermesEntryListResponse(BaseModel):
    entries: list[HermesEntryResponse]
    total: int
    type_counts: dict[str, int]
