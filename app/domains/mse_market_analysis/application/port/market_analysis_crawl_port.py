from abc import ABC, abstractmethod

from app.domains.mse_market_analysis.domain.entity.market_analysis_snapshot import (
    MarketAnalysisSnapshot,
)


class MarketAnalysisCrawlPort(ABC):
    """외부 시장분석 페이지를 크롤링하여 MarketAnalysisSnapshot 으로 반환한다."""

    @abstractmethod
    async def crawl(self) -> MarketAnalysisSnapshot:
        pass
