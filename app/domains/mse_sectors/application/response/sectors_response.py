from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class StockMetricItem(BaseModel):
    code: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    price: Optional[float] = None
    change_rate: Optional[float] = None
    wsma120: Optional[float] = None
    slope120: Optional[float] = None
    curv120: Optional[float] = None
    z180: Optional[float] = None
    align: Optional[float] = None
    momentum: Optional[float] = None
    escore: Optional[float] = None


class LeadingIndustryItem(BaseModel):
    industry: str
    avg_return: Optional[float] = None
    avg_escore: Optional[float] = None
    member_count: Optional[int] = None
    rank: Optional[int] = None


class DashboardSectionItem(BaseModel):
    key: str
    title: str
    kind: str
    columns: list[str] = []
    rows: list[dict[str, Any]] = []
    extras: dict[str, Any] = {}


class SectorsResponse(BaseModel):
    source_url: str
    collected_at: datetime
    status: str
    error_reason: Optional[str] = None
    is_stale: bool
    stock_metrics: list[StockMetricItem]
    leading_industries: list[LeadingIndustryItem]
    sections: list[DashboardSectionItem]
