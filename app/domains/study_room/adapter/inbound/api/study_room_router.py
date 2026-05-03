from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.study_room.adapter.outbound.persistence.dashboard_snapshot_repository_impl import (
    DashboardSnapshotRepositoryImpl,
)
from app.domains.study_room.application.response.dashboard_response import DashboardResponse
from app.domains.study_room.application.usecase.get_study_room_dashboard_usecase import (
    GetStudyRoomDashboardUseCase,
)
from app.infrastructure.database.database import get_db

router = APIRouter(prefix="/study-room", tags=["study-room"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    repository = DashboardSnapshotRepositoryImpl(db)
    use_case = GetStudyRoomDashboardUseCase(repository)
    return await use_case.execute()
