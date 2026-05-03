from dataclasses import dataclass
from typing import Optional


@dataclass
class LeadingIndustry:
    """주도 업종(평균 수익률·EScore 기반 상위 업종) 행."""

    industry: str
    avg_return: Optional[float] = None
    avg_escore: Optional[float] = None
    member_count: Optional[int] = None
    rank: Optional[int] = None
