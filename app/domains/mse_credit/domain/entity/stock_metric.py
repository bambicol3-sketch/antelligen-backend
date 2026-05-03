from dataclasses import dataclass
from typing import Optional


@dataclass
class StockMetric:
    """신용 스프레드 분석 페이지에 노출되는 종목 단위 행의 표준 데이터 모델."""

    code: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None

    price: Optional[float] = None
    change_rate: Optional[float] = None

    wsma120: Optional[float] = None
    slope120: Optional[float] = None
    curv120: Optional[float] = None
    z180: Optional[float] = None

    align: Optional[float] = None
    momentum: Optional[float] = None
    escore: Optional[float] = None
