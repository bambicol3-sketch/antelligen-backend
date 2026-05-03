from abc import ABC, abstractmethod

from app.domains.mse_credit.domain.entity.credit_snapshot import CreditSnapshot


class CreditCrawlPort(ABC):
    """외부 신용 스프레드 분석 페이지를 크롤링하여 CreditSnapshot 으로 반환한다."""

    @abstractmethod
    async def crawl(self) -> CreditSnapshot:
        pass
