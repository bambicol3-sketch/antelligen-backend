import logging

from app.domains.mse_sectors.application.port.sectors_crawl_port import SectorsCrawlPort
from app.domains.mse_sectors.application.port.sectors_snapshot_repository import (
    SectorsSnapshotRepositoryPort,
)
from app.domains.mse_sectors.domain.entity.sectors_snapshot import SectorsSnapshot

logger = logging.getLogger(__name__)


class CrawlSectorsUseCase:
    """외부 산업군 분석 페이지를 크롤링하여 스냅샷으로 저장한다."""

    def __init__(
        self,
        crawler: SectorsCrawlPort,
        repository: SectorsSnapshotRepositoryPort,
    ):
        self._crawler = crawler
        self._repository = repository

    async def execute(self) -> SectorsSnapshot:
        snapshot = await self._crawler.crawl()
        saved = await self._repository.save(snapshot)
        if saved.is_successful():
            logger.info(
                "mse_sectors crawl ok: stocks=%d industries=%d sections=%d",
                len(saved.stock_metrics),
                len(saved.leading_industries),
                len(saved.sections),
            )
        else:
            logger.warning(
                "mse_sectors crawl status=%s reason=%s",
                saved.status.value,
                saved.error_reason,
            )
        return saved
