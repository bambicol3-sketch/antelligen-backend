from dataclasses import dataclass, field
from typing import Any


@dataclass
class DashboardSection:
    """산업군 분석 페이지의 임의 섹션(카드/표/요약/차트 영역)을 일반 형태로 보존."""

    key: str
    title: str
    kind: str  # "card" | "table" | "chart" | "summary" | "raw_html" | "full_html_document"
    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)
