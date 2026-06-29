from collections import Counter

from app.domains.hermes.application.port.hermes_repository_port import HermesRepositoryPort
from app.domains.hermes.application.response.hermes_entry_response import (
    HermesEntryListResponse,
    HermesEntryResponse,
)


class ListHermesEntriesUseCase:
    def __init__(self, repository: HermesRepositoryPort):
        self._repository = repository

    async def execute(
        self,
        query: str | None = None,
        entry_type: str | None = None,
        tag: str | None = None,
    ) -> HermesEntryListResponse:
        entries = await self._repository.find_all()

        # type_counts 는 필터 적용 전 전체 분포 — UI 필터 칩 카운트용
        type_counts = Counter(e.type.value for e in entries)

        if entry_type:
            entries = [e for e in entries if e.type.value == entry_type]
        if tag:
            entries = [e for e in entries if tag.lower() in (t.lower() for t in e.tags)]
        if query:
            entries = [e for e in entries if e.matches(query)]

        return HermesEntryListResponse(
            entries=[HermesEntryResponse.from_entity(e) for e in entries],
            total=len(entries),
            type_counts=dict(type_counts),
        )
