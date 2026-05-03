from dataclasses import dataclass, field
from typing import Any


@dataclass
class DashboardSection:
    """원본 대시보드의 임의 섹션(카드/표/요약 영역)을 일반 형태로 보존한다.

    파서가 인식한 알려진 표 외에도 화면 재현에 필요한
    카드/요약/차트 데이터 등을 손실 없이 담기 위해 사용한다.
    """

    key: str
    title: str
    kind: str  # "card" | "table" | "chart" | "summary"
    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)
