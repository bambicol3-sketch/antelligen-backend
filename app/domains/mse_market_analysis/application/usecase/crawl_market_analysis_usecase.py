import logging

from app.domains.mse_market_analysis.application.port.market_analysis_crawl_port import (
    MarketAnalysisCrawlPort,
)
from app.domains.mse_market_analysis.application.port.market_analysis_snapshot_repository import (
    MarketAnalysisSnapshotRepositoryPort,
)
from app.domains.mse_market_analysis.domain.entity.market_analysis_snapshot import (
    MarketAnalysisSnapshot,
)

logger = logging.getLogger(__name__)


class CrawlMarketAnalysisUseCase:
    """외부 시장분석 페이지를 크롤링하여 스냅샷으로 저장한다."""

    def __init__(
        self,
        crawler: MarketAnalysisCrawlPort,
        repository: MarketAnalysisSnapshotRepositoryPort,
    ):
        self._crawler = crawler
        self._repository = repository

    async def execute(self) -> MarketAnalysisSnapshot:
        snapshot = await self._crawler.crawl()
        saved = await self._repository.save(snapshot)
        if saved.is_successful():
            logger.info(
                "mse_market_analysis crawl ok: stocks=%d industries=%d sections=%d",
                len(saved.stock_metrics),
                len(saved.leading_industries),
                len(saved.sections),
            )
        else:
            logger.warning(
                "mse_market_analysis crawl status=%s reason=%s",
                saved.status.value,
                saved.error_reason,
            )
        return saved
