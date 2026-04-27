"""매크로 사유 추정용 뉴스 검색 포트.

KR2-(3) — Type B 매크로 이벤트(VIX/유가/금/환율/지정학 등 ticker 없는 사건)의
사유 후보를 외부 뉴스 검색으로 보강한다. ticker-기반 어댑터(Finnhub/yfinance/Naver)
와 달리 키워드 free-text 가 가능한 소스(GDELT 등)만 이 포트의 어댑터가 된다.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Dict, List


class MacroNewsSearchPort(ABC):
    """키워드 + 날짜 윈도우 기반 뉴스 검색 포트.

    응답 항목 dict 스키마(어댑터들이 공통적으로 채우는 필드):
        - "title": str  — 기사 제목
        - "url":   str  — 기사 URL (라벨 fallback 용도로도 사용)
        - "date":  str  — "YYYYMMDD" (어댑터 fast-fail 시 빈 문자열 가능)
        - "source": str — 어댑터 식별자 (예: "gdelt")
    """

    @abstractmethod
    async def search(
        self,
        keyword: str,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        """키워드와 날짜 범위로 기사 목록을 조회한다. 실패는 빈 배열로 fast-fail."""
