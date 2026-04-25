from datetime import date
from typing import Optional

from pydantic import BaseModel


class USConcentratedBuyingItem(BaseModel):
    ticker: str
    stock_name: str | None
    investor_count: int
    total_market_value: int  # USD 천 달러
    investors: list[str]
    reported_at: Optional[date]


class USConcentratedBuyingResponse(BaseModel):
    items: list[USConcentratedBuyingItem]
    total: int
