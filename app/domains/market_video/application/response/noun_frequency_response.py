from pydantic import BaseModel


class NounFrequencyItem(BaseModel):
    noun: str
    count: int


class NounFrequencyResponse(BaseModel):
    total_unique_nouns: int
    selected_count: int
    items: list[NounFrequencyItem]
