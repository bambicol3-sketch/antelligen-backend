from dataclasses import asdict

from app.domains.mse_sectors.domain.entity.dashboard_section import DashboardSection
from app.domains.mse_sectors.domain.entity.leading_industry import LeadingIndustry
from app.domains.mse_sectors.domain.entity.sectors_snapshot import SectorsSnapshot
from app.domains.mse_sectors.domain.entity.stock_metric import StockMetric
from app.domains.mse_sectors.domain.value_object.crawl_status import CrawlStatus
from app.domains.mse_sectors.infrastructure.orm.sectors_snapshot_orm import SectorsSnapshotOrm


class SectorsSnapshotMapper:

    @staticmethod
    def to_entity(orm: SectorsSnapshotOrm) -> SectorsSnapshot:
        return SectorsSnapshot(
            id=orm.id,
            source_url=orm.source_url,
            collected_at=orm.collected_at,
            status=CrawlStatus(orm.status),
            error_reason=orm.error_reason,
            stock_metrics=[StockMetric(**row) for row in (orm.stock_metrics or [])],
            leading_industries=[
                LeadingIndustry(**row) for row in (orm.leading_industries or [])
            ],
            sections=[DashboardSection(**row) for row in (orm.sections or [])],
        )

    @staticmethod
    def to_orm(entity: SectorsSnapshot) -> SectorsSnapshotOrm:
        return SectorsSnapshotOrm(
            source_url=entity.source_url,
            collected_at=entity.collected_at,
            status=entity.status.value,
            error_reason=entity.error_reason,
            stock_metrics=[asdict(m) for m in entity.stock_metrics],
            leading_industries=[asdict(i) for i in entity.leading_industries],
            sections=[asdict(s) for s in entity.sections],
        )
