from abc import ABC, abstractmethod

from app.domains.study_room.domain.entity.dashboard_snapshot import DashboardSnapshot


class DashboardCrawlPort(ABC):
    """외부 주식 대시보드 페이지를 크롤링하여 DashboardSnapshot 으로 반환한다.

    인증, HTTP 요청, HTML 파싱은 모두 어댑터 책임이며
    Application 은 이 Port 만을 통해 결과를 받는다.
    """

    @abstractmethod
    async def crawl(self) -> DashboardSnapshot:
        pass
