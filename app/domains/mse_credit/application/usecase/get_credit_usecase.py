from dataclasses import asdict

from fastapi import HTTPException, status

from app.domains.mse_credit.application.port.credit_snapshot_repository import (
    CreditSnapshotRepositoryPort,
)
from app.domains.mse_credit.application.response.credit_response import (
    CreditResponse,
    DashboardSectionItem,
    LeadingIndustryItem,
    StockMetricItem,
)
from app.domains.mse_credit.domain.entity.credit_snapshot import CreditSnapshot


class GetCreditUseCase:
    """저장된 최신 신용 스프레드 분석 스냅샷을 응답 DTO 로 반환한다."""

    def __init__(self, repository: CreditSnapshotRepositoryPort):
        self._repository = repository

    async def execute(self) -> CreditResponse:
        latest = await self._repository.find_latest()
        if latest is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="신용 스프레드 분석 스냅샷이 아직 수집되지 않았습니다.",
            )

        if latest.is_successful():
            return self._to_response(latest, fallback=latest, is_stale=False)

        fallback = await self._repository.find_latest_successful()
        if fallback is None:
            return self._to_response(latest, fallback=latest, is_stale=False)
        return self._to_response(latest, fallback=fallback, is_stale=True)

    @staticmethod
    def _to_response(
        latest: CreditSnapshot,
        fallback: CreditSnapshot,
        is_stale: bool,
    ) -> CreditResponse:
        return CreditResponse(
            source_url=latest.source_url,
            collected_at=fallback.collected_at,
            status=latest.status.value,
            error_reason=latest.error_reason,
            is_stale=is_stale,
            stock_metrics=[StockMetricItem(**asdict(m)) for m in fallback.stock_metrics],
            leading_industries=[
                LeadingIndustryItem(**asdict(i)) for i in fallback.leading_industries
            ],
            sections=[DashboardSectionItem(**asdict(s)) for s in fallback.sections],
        )
