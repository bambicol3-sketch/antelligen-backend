from datetime import date
from typing import Optional

from pydantic import BaseModel


class ConcentratedBuyingItem(BaseModel):
    stock_code: str
    stock_name: str
    foreign_net_buy: int
    institution_net_buy: int
    total_net_buy: int
    concentration_score: float


class ConcentratedBuyingResponse(BaseModel):
    since_date: Optional[date]
    days: int
    total: int
    items: list[ConcentratedBuyingItem]
