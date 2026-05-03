import logging

from app.domains.study_room.application.port.dashboard_crawl_port import DashboardCrawlPort
from app.domains.study_room.application.port.dashboard_snapshot_repository import (
    DashboardSnapshotRepositoryPort,
)
from app.domains.study_room.domain.entity.dashboard_snapshot import DashboardSnapshot

logger = logging.getLogger(__name__)


class CrawlStudyRoomDashboardUseCase:
    """외부 주식 대시보드를 크롤링하여 스냅샷으로 저장한다.

    실패/구조 변경 스냅샷도 동일하게 저장하여
    오류 상태와 마지막 성공 시각을 추적할 수 있게 한다.
    """

    def __init__(
        self,
        crawler: DashboardCrawlPort,
        repository: DashboardSnapshotRepositoryPort,
    ):
        self._crawler = crawler
        self._repository = repository

    async def execute(self) -> DashboardSnapshot:
        snapshot = await self._crawler.crawl()
        saved = await self._repository.save(snapshot)
        if saved.is_successful():
            logger.info(
                "study_room dashboard crawl ok: stocks=%d industries=%d sections=%d",
                len(saved.stock_metrics),
                len(saved.leading_industries),
                len(saved.sections),
            )
        else:
            logger.warning(
                "study_room dashboard crawl status=%s reason=%s",
                saved.status.value,
                saved.error_reason,
            )
        return saved
