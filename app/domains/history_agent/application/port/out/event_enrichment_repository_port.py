from abc import ABC, abstractmethod
from datetime import date
from typing import List, Tuple, Union

from app.domains.history_agent.domain.entity.event_enrichment import EventEnrichment

# 4-tuple은 v1 호환(classifier_version="v1" 암시), 5-tuple은 명시적 버전 지정.
EnrichmentKey = Union[
    Tuple[str, date, str, str],
    Tuple[str, date, str, str, str],
]


class EventEnrichmentRepositoryPort(ABC):

    @abstractmethod
    async def find_by_keys(
        self, keys: List[EnrichmentKey]
    ) -> List[EventEnrichment]:
        """(ticker, event_date, event_type, detail_hash[, classifier_version]) 키 목록으로 배치 조회.

        4-tuple이 들어오면 classifier_version="v1"로 간주(v1 호환).
        """
        pass

    @abstractmethod
    async def upsert_bulk(self, enrichments: List[EventEnrichment]) -> int:
        """enrichment 결과를 upsert한다. 저장된 건수를 반환한다."""
        pass

    async def rollback(self) -> None:
        """세션이 aborted 상태일 때 복구용. 기본 구현은 no-op."""
        return None
