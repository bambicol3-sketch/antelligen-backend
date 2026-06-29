from pydantic import BaseModel, Field

from app.domains.hermes.domain.value_object.entry_type import HermesEntryType


class CreateHermesEntryRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    type: HermesEntryType = HermesEntryType.TIP
    content: str = Field(min_length=1)
    tags: list[str] = []
    project: str = "global"
