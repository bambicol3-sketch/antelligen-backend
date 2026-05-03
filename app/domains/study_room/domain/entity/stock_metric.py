from dataclasses import dataclass
from typing import Optional


@dataclass
class StockMetric:
    """원본 대시보드의 종목 단위 행을 표현하는 표준 데이터 모델.

    필드는 용어 설명에 정의된 기술 지표를 포함한다.
    값이 없을 수 있는 항목은 Optional 로 둔다.
    """

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
