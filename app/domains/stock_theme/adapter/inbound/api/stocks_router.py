from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.stock_theme.adapter.outbound.persistence.stock_theme_repository_impl import StockThemeRepositoryImpl
from app.domains.stock_theme.application.response.stocks_by_theme_response import (
    StocksByThemeGroupedResponse,
    StocksByThemeListResponse,
)
from app.domains.stock_theme.application.usecase.get_stocks_by_theme_usecase import GetStocksByThemeUseCase
from app.infrastructure.database.database import get_db

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/themes", response_model=StocksByThemeGroupedResponse)
async def get_stocks_by_themes(db: AsyncSession = Depends(get_db)):
    """전체 테마 목록과 테마별 종목 목록을 반환한다. 인증 불필요."""
    usecase = GetStocksByThemeUseCase(StockThemeRepositoryImpl(db))
    return await usecase.get_all_grouped()


@router.get("", response_model=StocksByThemeListResponse)
async def get_stocks_by_theme(
    theme: str = Query(..., description="테마명 (예: 반도체, IT, 바이오, 2차전지, 금융, 방산, 에너지, 소비재)"),
    db: AsyncSession = Depends(get_db),
):
    """특정 테마에 속한 종목 목록을 반환한다. 인증 불필요."""
    usecase = GetStocksByThemeUseCase(StockThemeRepositoryImpl(db))
    return await usecase.get_by_theme(theme)
