from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class RevenueSegment:
    """사업부문별 매출 비중 — 파이 차트 시각화용.

    DART 사업보고서 '매출 구성' 또는 LLM 일반 지식 기반으로 추출.
    합계는 100% 근사 (기타/조정 항목으로 100 미만일 수 있음).
    """

    name: str        # 사업 부문명 (예: "치과용임플란트", "메모리 반도체")
    percent: float   # 0 < percent <= 100


@dataclass(frozen=True)
class BusinessOverview:
    summary: str
    revenue_sources: list[str] = field(default_factory=list)
    revenue_segments: list[RevenueSegment] = field(default_factory=list)
    source: str = "llm_only"  # "rag_summary" | "llm_only" | "asset_llm_only"
    founding_story: Optional[str] = None
    business_model: Optional[str] = None
