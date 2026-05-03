from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.mse_credit.adapter.outbound.persistence.credit_snapshot_repository_impl import (
    CreditSnapshotRepositoryImpl,
)
from app.domains.mse_credit.application.response.credit_response import CreditResponse
from app.domains.mse_credit.application.usecase.get_credit_usecase import GetCreditUseCase
from app.infrastructure.database.database import get_db

router = APIRouter(prefix="/mse-credit", tags=["mse-credit"])


@router.get("/credit-spread", response_model=CreditResponse)
async def get_credit_spread(db: AsyncSession = Depends(get_db)):
    repository = CreditSnapshotRepositoryImpl(db)
    use_case = GetCreditUseCase(repository)
    return await use_case.execute()
