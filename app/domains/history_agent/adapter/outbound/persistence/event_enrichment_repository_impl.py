from datetime import date
from typing import List, Tuple, Union

from sqlalchemy import select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.history_agent.application.port.out.event_enrichment_repository_port import (
    EnrichmentKey,
    EventEnrichmentRepositoryPort,
)
from app.domains.history_agent.domain.entity.event_enrichment import EventEnrichment
from app.domains.history_agent.infrastructure.mapper.event_enrichment_mapper import (
    EventEnrichmentMapper,
)
from app.domains.history_agent.infrastructure.orm.event_enrichment_orm import EventEnrichmentOrm


def _normalize_key(key: EnrichmentKey) -> Tuple[str, date, str, str, str]:
    """4-tuple은 classifier_version='v1' 암시. 5-tuple은 그대로."""
    if len(key) == 4:
        ticker, event_date, event_type, detail_hash = key
        return (ticker, event_date, event_type, detail_hash, "v1")
    return key  # type: ignore[return-value]


class EventEnrichmentRepositoryImpl(EventEnrichmentRepositoryPort):

    def __init__(self, db: AsyncSession):
        self._db = db

    async def find_by_keys(
        self, keys: List[EnrichmentKey]
    ) -> List[EventEnrichment]:
        if not keys:
            return []

        normalized = [_normalize_key(k) for k in keys]

        stmt = select(EventEnrichmentOrm).where(
            tuple_(
                EventEnrichmentOrm.ticker,
                EventEnrichmentOrm.event_date,
                EventEnrichmentOrm.event_type,
                EventEnrichmentOrm.detail_hash,
                EventEnrichmentOrm.classifier_version,
            ).in_(normalized)
        )
        result = await self._db.execute(stmt)
        return [EventEnrichmentMapper.to_entity(orm) for orm in result.scalars().all()]

    async def upsert_bulk(self, enrichments: List[EventEnrichment]) -> int:
        if not enrichments:
            return 0

        values = [
            {
                "ticker": e.ticker,
                "event_date": e.event_date,
                "event_type": e.event_type,
                "detail_hash": e.detail_hash,
                "title": e.title,
                "causality": e.causality,
                "importance_score": e.importance_score,
                "importance_score_1to5": e.importance_score_1to5,
                "items_str": e.items_str,
                "reclassified_type": e.reclassified_type,
                "classifier_version": e.classifier_version,
            }
            for e in enrichments
        ]

        excluded = insert(EventEnrichmentOrm).excluded
        stmt = (
            insert(EventEnrichmentOrm)
            .values(values)
            .on_conflict_do_update(
                constraint="uq_event_enrichments_key",
                set_={
                    "title": excluded.title,
                    "causality": excluded.causality,
                    "importance_score": excluded.importance_score,
                    "importance_score_1to5": excluded.importance_score_1to5,
                    "items_str": excluded.items_str,
                    "reclassified_type": excluded.reclassified_type,
                    "updated_at": excluded.updated_at,
                },
            )
            .returning(EventEnrichmentOrm.id)
        )

        result = await self._db.execute(stmt)
        await self._db.commit()
        return len(result.fetchall())

    async def rollback(self) -> None:
        """세션이 aborted 상태에서 후속 쿼리를 살리기 위한 명시적 롤백."""
        try:
            await self._db.rollback()
        except Exception:  # noqa: BLE001
            pass
