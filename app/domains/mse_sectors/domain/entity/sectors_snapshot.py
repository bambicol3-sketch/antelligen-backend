from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.domains.mse_sectors.domain.entity.dashboard_section import DashboardSection
from app.domains.mse_sectors.domain.entity.leading_industry import LeadingIndustry
from app.domains.mse_sectors.domain.entity.stock_metric import StockMetric
from app.domains.mse_sectors.domain.value_object.crawl_status import CrawlStatus


@dataclass
class SectorsSnapshot:
    """외부 산업군 분석 페이지 1회 크롤 결과의 표준 스냅샷.

    Aggregate Root.
    """

    id: Optional[int]
    source_url: str
    collected_at: datetime
    status: CrawlStatus
    error_reason: Optional[str] = None

    stock_metrics: list[StockMetric] = field(default_factory=list)
    leading_industries: list[LeadingIndustry] = field(default_factory=list)
    sections: list[DashboardSection] = field(default_factory=list)

    def is_successful(self) -> bool:
        return self.status == CrawlStatus.SUCCESS
