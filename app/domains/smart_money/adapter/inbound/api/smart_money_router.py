from datetime import date, timedelta

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response.base_response import BaseResponse
from app.domains.smart_money.adapter.outbound.external.krx_investor_flow_client import KrxInvestorFlowClient
from app.domains.smart_money.adapter.outbound.external.sec_edgar_13f_client import SecEdgar13FClient
from app.domains.smart_money.adapter.outbound.persistence.global_portfolio_repository_impl import GlobalPortfolioRepositoryImpl
from app.domains.smart_money.adapter.outbound.persistence.investor_flow_repository_impl import InvestorFlowRepositoryImpl
from app.domains.smart_money.application.response.collect_global_portfolio_response import CollectGlobalPortfolioResponse
from app.domains.smart_money.application.response.collect_investor_flow_response import CollectInvestorFlowResponse
from app.domains.smart_money.application.response.investor_flow_ranking_response import InvestorFlowRankingResponse
from app.domains.smart_money.application.response.global_portfolio_response import GlobalPortfolioResponse, InvestorListResponse
from app.domains.smart_money.application.response.concentrated_buying_response import ConcentratedBuyingResponse
from app.domains.smart_money.application.usecase.collect_global_portfolio_usecase import CollectGlobalPortfolioUseCase
from app.domains.smart_money.application.usecase.collect_investor_flow_usecase import CollectInvestorFlowUseCase
from app.domains.smart_money.application.usecase.get_investor_flow_ranking_usecase import GetInvestorFlowRankingUseCase
from app.domains.smart_money.application.usecase.get_global_portfolio_usecase import GetGlobalPortfolioUseCase
from app.domains.smart_money.application.usecase.get_concentrated_buying_usecase import GetConcentratedBuyingUseCase
from app.domains.smart_money.application.response.investor_flow_trend_response import InvestorFlowTrendResponse
from app.domains.smart_money.application.usecase.get_investor_flow_trend_usecase import GetInvestorFlowTrendUseCase
from app.domains.smart_money.domain.entity.investor_flow import InvestorType
from app.domains.smart_money.domain.entity.global_portfolio import ChangeType
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.database import get_db

router = APIRouter(prefix="/smart-money", tags=["Smart Money"])


@router.post("/collect", response_model=BaseResponse[CollectInvestorFlowResponse], status_code=201)
async def collect_investor_flow(
    target_date: date | None = Query(default=None, description="수집 날짜 (YYYY-MM-DD, 생략 시 전일)"),
    db: AsyncSession = Depends(get_db),
):
    """KRX에서 외국인·기관·개인 투자자 유형별 순매수 데이터를 수집하여 저장한다."""
    settings = get_settings()
    krx_client = KrxInvestorFlowClient(krx_id=settings.krx_id, krx_pw=settings.krx_pw)
    repository = InvestorFlowRepositoryImpl(db)
    usecase = CollectInvestorFlowUseCase(krx_port=krx_client, repository=repository)
    result = await usecase.execute(target_date=target_date)
    return BaseResponse.ok(data=result)


@router.post("/global-portfolio/collect", response_model=BaseResponse[CollectGlobalPortfolioResponse], status_code=201)
async def collect_global_portfolio(
    db: AsyncSession = Depends(get_db),
):
    """SEC EDGAR 13F 공시에서 글로벌 저명 투자자 포트폴리오를 수집하여 저장한다."""
    settings = get_settings()
    fetch_client = SecEdgar13FClient(user_agent=settings.sec_edgar_user_agent)
    repository = GlobalPortfolioRepositoryImpl(db)
    usecase = CollectGlobalPortfolioUseCase(fetch_port=fetch_client, repository=repository)
    result = await usecase.execute()
    return BaseResponse.ok(data=result)


@router.get("/investor-flow", response_model=BaseResponse[InvestorFlowRankingResponse])
async def get_investor_flow_ranking(
    investor_type: InvestorType = Query(..., description="투자자 유형 (FOREIGN | INSTITUTION | INDIVIDUAL)"),
    date: date | None = Query(default=None, description="조회 날짜 (YYYY-MM-DD, 생략 시 최근 영업일)"),
    limit: int = Query(default=20, ge=1, le=100, description="반환 종목 수 (기본: 20)"),
    db: AsyncSession = Depends(get_db),
):
    """투자자 유형별 순매수 금액 내림차순 종목 랭킹을 반환한다."""
    repository = InvestorFlowRepositoryImpl(db)
    usecase = GetInvestorFlowRankingUseCase(repository=repository)
    result = await usecase.execute(investor_type=investor_type, target_date=date, limit=limit)
    return BaseResponse.ok(data=result)


@router.get("/investors", response_model=BaseResponse[InvestorListResponse])
async def get_investor_list():
    """수집 대상 글로벌 저명 투자자 목록을 반환한다 (DB 수집 여부 무관)."""
    from app.domains.smart_money.application.usecase.collect_global_portfolio_usecase import INVESTOR_CIK_MAP
    return BaseResponse.ok(data=InvestorListResponse(investors=list(INVESTOR_CIK_MAP.keys())))


@router.get("/global-portfolio", response_model=BaseResponse[GlobalPortfolioResponse])
async def get_global_portfolio(
    investor_name: str | None = Query(default=None, description="투자자 이름 필터 (생략 시 전체)"),
    change_type: ChangeType | None = Query(default=None, description="변동 유형 필터 (NEW | INCREASED | DECREASED | CLOSED)"),
    db: AsyncSession = Depends(get_db),
):
    """글로벌 저명 투자자 최신 분기 포트폴리오를 반환한다."""
    repository = GlobalPortfolioRepositoryImpl(db)
    usecase = GetGlobalPortfolioUseCase(repository=repository)
    result = await usecase.execute(investor_name=investor_name, change_type=change_type)
    return BaseResponse.ok(data=result)


@router.get("/concentrated", response_model=BaseResponse[ConcentratedBuyingResponse])
async def get_concentrated_buying(
    days: int = Query(default=5, ge=1, le=30, description="최근 N 영업일 누적 집계 (기본: 5)"),
    limit: int = Query(default=50, ge=1, le=200, description="반환 종목 수 (기본: 50)"),
    db: AsyncSession = Depends(get_db),
):
    """외국인·기관 동시 순매수 상위 집중 매수 종목을 반환한다."""
    repository = InvestorFlowRepositoryImpl(db)
    usecase = GetConcentratedBuyingUseCase(repository=repository)
    result = await usecase.execute(days=days, limit=limit)
    return BaseResponse.ok(data=result)


@router.get("/trend/{stock_code}", response_model=BaseResponse[InvestorFlowTrendResponse])
async def get_investor_flow_trend(
    stock_code: str = Path(..., description="종목 코드 (예: 005930)"),
    days: int = Query(default=30, ge=1, le=365, description="최근 N일 추이 (기본: 30)"),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """종목별 외국인·기관·개인 일별 순매수 추이를 반환한다. (Redis TTL 10분)"""
    latest_date = await InvestorFlowRepositoryImpl(db).find_latest_date(InvestorType.FOREIGN.value)
    if latest_date is None:
        from app.common.exception.app_exception import AppException
        raise AppException(status_code=404, message="수집된 투자자 순매수 데이터가 없습니다.")
    since_date = latest_date - timedelta(days=days - 1)
    repository = InvestorFlowRepositoryImpl(db)
    usecase = GetInvestorFlowTrendUseCase(repository=repository, redis=redis)
    result = await usecase.execute(stock_code=stock_code, since_date=since_date, days=days)
    return BaseResponse.ok(data=result)
