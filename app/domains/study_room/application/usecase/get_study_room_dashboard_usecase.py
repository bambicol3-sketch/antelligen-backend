from dataclasses import asdict

from fastapi import HTTPException, status

from app.domains.study_room.application.port.dashboard_snapshot_repository import (
    DashboardSnapshotRepositoryPort,
)
from app.domains.study_room.application.response.dashboard_response import (
    DashboardResponse,
    DashboardSectionItem,
    LeadingIndustryItem,
    StockMetricItem,
)
from app.domains.study_room.domain.entity.dashboard_snapshot import DashboardSnapshot


class GetStudyRoomDashboardUseCase:
    """저장된 최신 대시보드 스냅샷을 응답 DTO 로 반환한다.

    최신 스냅샷이 실패/구조 변경 상태라면
    마지막 성공 스냅샷을 데이터로 사용하면서 status 와 error_reason 을 함께 노출한다.
    """

    def __init__(self, repository: DashboardSnapshotRepositoryPort):
        self._repository = repository

    async def execute(self) -> DashboardResponse:
        latest = await self._repository.find_latest()
        if latest is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="대시보드 스냅샷이 아직 수집되지 않았습니다.",
            )

        if latest.is_successful():
            return self._to_response(latest, fallback=latest, is_stale=False)

        fallback = await self._repository.find_latest_successful()
        if fallback is None:
            return self._to_response(latest, fallback=latest, is_stale=False)
        return self._to_response(latest, fallback=fallback, is_stale=True)

    @staticmethod
    def _to_response(
        latest: DashboardSnapshot,
        fallback: DashboardSnapshot,
        is_stale: bool,
    ) -> DashboardResponse:
        return DashboardResponse(
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
