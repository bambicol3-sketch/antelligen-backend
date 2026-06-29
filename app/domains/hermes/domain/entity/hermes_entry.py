from dataclasses import dataclass, field
from datetime import datetime

from app.domains.hermes.domain.value_object.entry_type import HermesEntryType


@dataclass
class HermesEntry:
    """Claude 사용 노하우 1건. 저장소에서는 entries/<id>.md 파일 하나에 대응한다."""

    id: str
    title: str
    type: HermesEntryType
    content: str
    tags: list[str] = field(default_factory=list)
    project: str = "global"
    source: str = "web"  # cli | web
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def summary(self) -> str:
        """본문 첫 비어있지 않은 줄 — 인덱스/목록 요약용."""
        for line in self.content.splitlines():
            stripped = line.strip().lstrip("#").strip()
            if stripped:
                return stripped
        return ""

    def matches(self, query: str) -> bool:
        """제목·본문·태그에 대한 단순 부분 일치 검색."""
        q = query.lower()
        return (
            q in self.title.lower()
            or q in self.content.lower()
            or any(q in tag.lower() for tag in self.tags)
        )
