from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.mse_market_analysis.adapter.outbound.persistence.market_analysis_snapshot_repository_impl import (
    MarketAnalysisSnapshotRepositoryImpl,
)
from app.domains.mse_market_analysis.application.response.market_analysis_response import (
    MarketAnalysisResponse,
)
from app.domains.mse_market_analysis.application.usecase.get_market_analysis_usecase import (
    GetMarketAnalysisUseCase,
)
from app.infrastructure.database.database import get_db

router = APIRouter(prefix="/mse-market-analysis", tags=["mse-market-analysis"])


@router.get("/market", response_model=MarketAnalysisResponse)
async def get_market_analysis(db: AsyncSession = Depends(get_db)):
    repository = MarketAnalysisSnapshotRepositoryImpl(db)
    use_case = GetMarketAnalysisUseCase(repository)
    return await use_case.execute()
