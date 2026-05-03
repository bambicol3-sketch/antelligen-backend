from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.mse_sectors.adapter.outbound.persistence.sectors_snapshot_repository_impl import (
    SectorsSnapshotRepositoryImpl,
)
from app.domains.mse_sectors.application.response.sectors_response import SectorsResponse
from app.domains.mse_sectors.application.usecase.get_sectors_usecase import GetSectorsUseCase
from app.infrastructure.database.database import get_db

router = APIRouter(prefix="/mse-sectors", tags=["mse-sectors"])


@router.get("/sectors", response_model=SectorsResponse)
async def get_sectors(db: AsyncSession = Depends(get_db)):
    repository = SectorsSnapshotRepositoryImpl(db)
    use_case = GetSectorsUseCase(repository)
    return await use_case.execute()
