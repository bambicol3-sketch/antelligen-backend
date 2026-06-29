from pydantic import BaseModel, Field

from app.domains.hermes.domain.value_object.entry_type import HermesEntryType


class UpdateHermesEntryRequest(BaseModel):
    """부분 수정 — None 인 필드는 기존 값을 유지한다."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    type: HermesEntryType | None = None
    content: str | None = Field(default=None, min_length=1)
    tags: list[str] | None = None
    project: str | None = None
