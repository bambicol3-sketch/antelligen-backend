from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.agent.application.port.integrated_analysis_repository_port import (
    IntegratedAnalysisRepositoryPort,
)
from app.domains.agent.application.response.integrated_analysis_response import (
    IntegratedAnalysisResponse,
)
from app.domains.agent.infrastructure.orm.integrated_analysis_orm import IntegratedAnalysisOrm


class IntegratedAnalysisRepositoryImpl(IntegratedAnalysisRepositoryPort):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def find_recent(
        self, ticker: str, within_seconds: int
    ) -> Optional[IntegratedAnalysisResponse]:
        cutoff = datetime.now() - timedelta(seconds=within_seconds)
        stmt = (
            select(IntegratedAnalysisOrm)
            .where(IntegratedAnalysisOrm.ticker == ticker)
            .where(IntegratedAnalysisOrm.created_at >= cutoff)
            .order_by(IntegratedAnalysisOrm.created_at.desc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_response(row) if row else None

    async def save(self, result: IntegratedAnalysisResponse) -> None:
        row = IntegratedAnalysisOrm(
            ticker=result.ticker,
            query=result.query,
            overall_signal=result.overall_signal,
            confidence=result.confidence,
            summary=result.summary,
            key_points=result.key_points,
            sub_results=result.sub_results,
            execution_time_ms=result.execution_time_ms,
        )
        self._db.add(row)
        await self._db.commit()

    async def find_history(
        self, ticker: str, limit: int = 10
    ) -> list[IntegratedAnalysisResponse]:
        stmt = (
            select(IntegratedAnalysisOrm)
            .where(IntegratedAnalysisOrm.ticker == ticker)
            .order_by(IntegratedAnalysisOrm.created_at.desc())
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        rows = result.scalars().all()
        return [self._to_response(row) for row in rows]

    @staticmethod
    def _to_response(row: IntegratedAnalysisOrm) -> IntegratedAnalysisResponse:
        return IntegratedAnalysisResponse(
            ticker=row.ticker,
            query=row.query,
            overall_signal=row.overall_signal,
            confidence=row.confidence,
            summary=row.summary,
            key_points=row.key_points,
            sub_results=row.sub_results,
            execution_time_ms=row.execution_time_ms,
        )
