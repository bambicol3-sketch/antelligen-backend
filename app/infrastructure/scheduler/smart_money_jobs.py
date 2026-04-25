import logging

from app.infrastructure.database.database import AsyncSessionLocal
from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


async def job_collect_global_portfolio() -> None:
    """분기별 글로벌 저명 투자자 13F 포트폴리오 데이터를 수집한다."""
    from app.domains.smart_money.adapter.outbound.external.sec_edgar_13f_client import SecEdgar13FClient
    from app.domains.smart_money.adapter.outbound.persistence.global_portfolio_repository_impl import GlobalPortfolioRepositoryImpl
    from app.domains.smart_money.application.usecase.collect_global_portfolio_usecase import CollectGlobalPortfolioUseCase

    logger.info("[smart_money.job] 글로벌 포트폴리오 수집 시작")
    settings = get_settings()
    try:
        async with AsyncSessionLocal() as db:
            usecase = CollectGlobalPortfolioUseCase(
                fetch_port=SecEdgar13FClient(user_agent=settings.sec_edgar_user_agent),
                repository=GlobalPortfolioRepositoryImpl(db),
            )
            result = await usecase.execute()
            logger.info(
                "[smart_money.job] 글로벌 포트폴리오 완료 — 투자자 %d명, 총 %d건 저장",
                len(result.results), result.total_saved,
            )
    except Exception as exc:
        logger.exception("[smart_money.job] 글로벌 포트폴리오 수집 실패: %s", exc)


async def job_collect_kr_portfolio() -> None:
    """월 1회 DART OpenAPI에서 국내 유명 투자자 5% 이상 대량보유 현황을 수집한다."""
    from app.domains.smart_money.adapter.outbound.external.dart_client import DartClient
    from app.domains.smart_money.adapter.outbound.persistence.kr_portfolio_repository_impl import KrPortfolioRepositoryImpl
    from app.domains.smart_money.application.usecase.collect_kr_portfolio_usecase import CollectKrPortfolioUseCase

    logger.info("[smart_money.job] 국내 포트폴리오 수집 시작")
    settings = get_settings()
    if not settings.open_dart_api_key:
        logger.warning("[smart_money.job] OPEN_DART_API_KEY 미설정 — 국내 포트폴리오 수집 건너뜀")
        return
    try:
        async with AsyncSessionLocal() as db:
            usecase = CollectKrPortfolioUseCase(
                dart_client=DartClient(api_key=settings.open_dart_api_key),
                repository=KrPortfolioRepositoryImpl(db),
            )
            result = await usecase.execute()
            logger.info("[smart_money.job] 국내 포트폴리오 완료 — %d건 저장", result.get("total_saved", 0))
    except Exception as exc:
        logger.exception("[smart_money.job] 국내 포트폴리오 수집 실패: %s", exc)


async def job_collect_investor_flow() -> None:
    """매 영업일 장 마감 후(16:30 KST) 투자자 유형별 순매수 데이터를 수집한다."""
    from app.domains.smart_money.adapter.outbound.external.krx_investor_flow_client import KrxInvestorFlowClient
    from app.domains.smart_money.adapter.outbound.persistence.investor_flow_repository_impl import InvestorFlowRepositoryImpl
    from app.domains.smart_money.application.usecase.collect_investor_flow_usecase import CollectInvestorFlowUseCase

    logger.info("[smart_money.job] 투자자 순매수 수집 시작")
    settings = get_settings()
    try:
        async with AsyncSessionLocal() as db:
            usecase = CollectInvestorFlowUseCase(
                krx_port=KrxInvestorFlowClient(
                    krx_id=settings.krx_id,
                    krx_pw=settings.krx_pw,
                ),
                repository=InvestorFlowRepositoryImpl(db),
            )
            result = await usecase.execute()
            logger.info(
                "[smart_money.job] 완료 — date=%s, saved=%d, skipped=%d",
                result.target_date, result.total_collected, result.skipped_duplicates,
            )
    except Exception as exc:
        logger.exception("[smart_money.job] 수집 실패: %s", exc)
