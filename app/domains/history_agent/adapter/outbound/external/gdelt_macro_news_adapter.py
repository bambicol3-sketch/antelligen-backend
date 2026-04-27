"""MacroNewsSearchPort 의 GDELT 어댑터.

`causality_agent` 의 `GdeltClient` 를 그대로 위임한다 — GDELT 의 키워드+날짜
검색이 매크로 이벤트(ticker 부재)에 가장 잘 맞아 별도 검색기 구현 없이 재사용.
도메인 결합은 어댑터 한 단으로 흡수해 application layer 가 GdeltClient 를
직접 import 하지 않도록 한다.
"""

from datetime import date
from typing import Any, Dict, List

from app.domains.causality_agent.adapter.outbound.external.gdelt_client import GdeltClient
from app.domains.history_agent.application.port.out.macro_news_search_port import (
    MacroNewsSearchPort,
)


class GdeltMacroNewsAdapter(MacroNewsSearchPort):
    def __init__(self, client: GdeltClient) -> None:
        self._client = client

    async def search(
        self,
        keyword: str,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        return await self._client.fetch_articles(
            keyword=keyword,
            start_date=start_date,
            end_date=end_date,
        )
