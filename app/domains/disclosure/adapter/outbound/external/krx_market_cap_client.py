import logging
import math

import httpx

from app.domains.disclosure.application.port.krx_market_cap_port import (
    KrxMarketCapPort,
    KrxMarketCapInfo,
)

logger = logging.getLogger(__name__)

NAVER_MARKET_VALUE_URL = "https://m.stock.naver.com/api/stocks/marketValue/{market}?page={page}&pageSize={page_size}"
NAVER_PAGE_SIZE = 100
MARKETS = ["KOSPI", "KOSDAQ"]


class KrxMarketCapClient(KrxMarketCapPort):
    """네이버 금융 API를 사용한 시가총액 상위 기업 조회 어댑터.

    KRX 직접 크롤링이 컨테이너 환경에서 차단되므로,
    네이버 금융의 시가총액 순위 API를 대안으로 사용한다.
    """

    async def fetch_top_by_market_cap(self, count: int = 300) -> list[KrxMarketCapInfo]:
        all_stocks: list[dict] = []

        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15.0,
        ) as client:
            for market in MARKETS:
                pages_needed = math.ceil(count / NAVER_PAGE_SIZE)
                for page in range(1, pages_needed + 1):
                    url = NAVER_MARKET_VALUE_URL.format(
                        market=market, page=page, page_size=NAVER_PAGE_SIZE,
                    )
                    try:
                        resp = await client.get(url)
                        if resp.status_code != 200:
                            logger.warning("네이버 시총 조회 실패: market=%s, page=%d, status=%d", market, page, resp.status_code)
                            break
                        data = resp.json()
                        stocks = data.get("stocks", [])
                        if not stocks:
                            break
                        all_stocks.extend(
                            {"stock_code": s["itemCode"], "corp_name": s["stockName"], "market_cap": self._parse_market_value(s.get("marketValue", "0")), "market": market}
                            for s in stocks
                            if s.get("stockEndType") == "stock"  # 우선주 등 제외
                        )
                    except Exception as e:
                        logger.error("네이버 시총 조회 에러: market=%s, page=%d, %s", market, page, e)
                        break

        # 시가총액 기준 정렬 후 상위 count개 선택
        all_stocks.sort(key=lambda x: x["market_cap"], reverse=True)
        top_stocks = all_stocks[:count]

        result: list[KrxMarketCapInfo] = []
        for rank, stock in enumerate(top_stocks, start=1):
            result.append(
                KrxMarketCapInfo(
                    stock_code=stock["stock_code"],
                    corp_name=stock["corp_name"],
                    market_cap=stock["market_cap"],
                    rank=rank,
                )
            )

        logger.info("시가총액 상위 %d개 기업 수집 완료 (KOSPI+KOSDAQ, 네이버 금융)", len(result))
        return result

    @staticmethod
    def _parse_market_value(value: str) -> int:
        """'10,637,589' 같은 문자열을 정수로 변환한다."""
        try:
            return int(value.replace(",", ""))
        except (ValueError, AttributeError):
            return 0
