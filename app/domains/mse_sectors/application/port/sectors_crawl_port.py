from abc import ABC, abstractmethod

from app.domains.mse_sectors.domain.entity.sectors_snapshot import SectorsSnapshot


class SectorsCrawlPort(ABC):
    """외부 산업군 분석 페이지를 크롤링하여 SectorsSnapshot 으로 반환한다."""

    @abstractmethod
    async def crawl(self) -> SectorsSnapshot:
        pass
