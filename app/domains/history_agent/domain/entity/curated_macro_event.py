from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class CuratedMacroEvent:
    """seed JSON(`historic_macro_events.json`)의 큐레이션 매크로 이벤트.

    region 컨벤션 (CuratedMacroEventsAdapter.fetch 가 region 매칭 + GLOBAL 합집합 반환):
      - "US" / "KR" — 해당 리전 사용자 전용 이벤트 (예: TARP, 레고랜드 ABCP)
      - "GLOBAL"   — 전 리전 사용자에게 노출. 글로벌 commodities(원유/금/천연가스),
                     지정학 사건(전쟁/제재/주요국 정책), 글로벌 시장 충격(리먼/COVID 등)
                     은 GLOBAL 로 태깅해야 KR/US 사용자 모두 받음.

    신규 이벤트 추가 시 region 분류 기준:
      - 해당 국가 시장에만 영향 → "US" 또는 "KR"
      - 다국가 시장에 영향 (특히 KR-US 양쪽 차트에서 의미) → "GLOBAL"
    """

    date: date
    event_type: str
    region: str
    title: str
    detail: str
    tags: List[str] = field(default_factory=list)
    importance_score: float = 1.0
    source_url: Optional[str] = None
