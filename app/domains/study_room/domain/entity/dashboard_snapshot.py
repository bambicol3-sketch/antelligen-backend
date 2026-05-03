from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.domains.study_room.domain.entity.dashboard_section import DashboardSection
from app.domains.study_room.domain.entity.leading_industry import LeadingIndustry
from app.domains.study_room.domain.entity.stock_metric import StockMetric
from app.domains.study_room.domain.value_object.crawl_status import CrawlStatus


@dataclass
class DashboardSnapshot:
    """외부 대시보드 1회 크롤 결과의 표준 스냅샷.

    Aggregate Root. 정상 크롤 성공 시 정규화된 표 데이터를 보관하고
    실패/구조 변경 시에는 status/error_reason 만 갱신한다.
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
