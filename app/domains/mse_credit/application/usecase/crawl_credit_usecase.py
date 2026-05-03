import logging

from app.domains.mse_credit.application.port.credit_crawl_port import CreditCrawlPort
from app.domains.mse_credit.application.port.credit_snapshot_repository import (
    CreditSnapshotRepositoryPort,
)
from app.domains.mse_credit.domain.entity.credit_snapshot import CreditSnapshot

logger = logging.getLogger(__name__)


class CrawlCreditUseCase:
    """외부 신용 스프레드 분석 페이지를 크롤링하여 스냅샷으로 저장한다."""

    def __init__(
        self,
        crawler: CreditCrawlPort,
        repository: CreditSnapshotRepositoryPort,
    ):
        self._crawler = crawler
        self._repository = repository

    async def execute(self) -> CreditSnapshot:
        snapshot = await self._crawler.crawl()
        saved = await self._repository.save(snapshot)
        if saved.is_successful():
            logger.info(
                "mse_credit crawl ok: stocks=%d industries=%d sections=%d",
                len(saved.stock_metrics),
                len(saved.leading_industries),
                len(saved.sections),
            )
        else:
            logger.warning(
                "mse_credit crawl status=%s reason=%s",
                saved.status.value,
                saved.error_reason,
            )
        return saved
