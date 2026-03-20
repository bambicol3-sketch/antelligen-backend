from fastapi import APIRouter, Query, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response.base_response import BaseResponse
from app.domains.news.adapter.outbound.external.article_content_scraper import (
    ArticleContentScraper,
)
from app.domains.news.adapter.outbound.external.openai_article_analysis_provider import (
    OpenAIArticleAnalysisProvider,
)
from app.domains.news.adapter.outbound.external.serp_news_search_provider import (
    SerpNewsSearchProvider,
)
from app.domains.news.adapter.outbound.persistence.saved_article_repository_impl import (
    SavedArticleRepositoryImpl,
)
from app.domains.news.application.request.save_article_request import (
    SaveArticleRequest,
)
from app.domains.news.application.request.search_news_request import SearchNewsRequest
from app.domains.news.application.response.analyze_article_response import (
    AnalyzeArticleResponse,
)
from app.domains.news.application.response.save_article_response import (
    SaveArticleResponse,
)
from app.domains.news.application.response.search_news_response import (
    SearchNewsResponse,
)
from app.domains.news.application.usecase.analyze_article_usecase import (
    AnalyzeArticleUseCase,
)
from app.domains.news.application.usecase.save_article_usecase import (
    SaveArticleUseCase,
)
from app.domains.news.application.usecase.search_news_usecase import SearchNewsUseCase
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.database import get_db

router = APIRouter(prefix="/news", tags=["News"])


@router.get("/search", response_model=BaseResponse[SearchNewsResponse])
async def search_news(
    keyword: str = Query(..., min_length=1, description="검색 키워드"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(10, ge=1, le=100, description="페이지 크기"),
):
    """인증 없이 뉴스를 검색하고 페이징된 결과를 반환한다."""
    settings = get_settings()
    provider = SerpNewsSearchProvider(api_key=settings.serp_api_key)
    usecase = SearchNewsUseCase(news_search_provider=provider)
    request = SearchNewsRequest(keyword=keyword, page=page, page_size=page_size)
    result = await usecase.execute(request)
    return BaseResponse.ok(data=result)


@router.post("/save", response_model=BaseResponse[SaveArticleResponse], status_code=201)
async def save_article(
    request: SaveArticleRequest,
    db: AsyncSession = Depends(get_db),
):
    """인증 없이 관심 기사를 저장한다. 링크에서 본문을 스크래핑하여 함께 저장한다."""
    repository = SavedArticleRepositoryImpl(db)
    content_provider = ArticleContentScraper()
    usecase = SaveArticleUseCase(repository=repository, content_provider=content_provider)
    result = await usecase.execute(request)
    return BaseResponse.ok(data=result)


@router.get("/analyze/{article_id}", response_model=BaseResponse[AnalyzeArticleResponse])
async def analyze_article(
    article_id: int = Path(..., ge=1, description="분석할 기사 ID"),
    db: AsyncSession = Depends(get_db),
):
    """저장된 기사의 핵심 키워드와 감정 분석 결과를 반환한다."""
    settings = get_settings()
    repository = SavedArticleRepositoryImpl(db)
    analysis_provider = OpenAIArticleAnalysisProvider(api_key=settings.openai_api_key)
    usecase = AnalyzeArticleUseCase(repository=repository, analysis_provider=analysis_provider)
    result = await usecase.execute(article_id)
    return BaseResponse.ok(data=result)


# Mock 뉴스 에이전트 엔드포인트 - 실제 API 없이 SubAgentResponse 형식으로 반환
@router.get("/agent-result")
async def get_news_agent_result(
    ticker: str = Query(..., description="종목 코드 (예: 005930)"),
):
    """메인 에이전트가 호출하는 뉴스 서브 에이전트 mock 엔드포인트"""
    mock_response = {
        "agent_name": "news",
        "status": "success",
        "data": {
            "ticker": ticker,
            "articles": [
                {
                    "title": f"{ticker} 관련 뉴스 mock 데이터",
                    "url": "https://example.com/news/1",
                    "summary": "mock 뉴스 요약입니다.",
                    "published_at": "2026-03-20"
                }
            ]
        },
        "signal": "bullish",
        "confidence": 0.75,
        "summary": f"{ticker} 종목에 대한 뉴스 감성 분석 결과 긍정적 신호가 감지되었습니다.",
        "key_points": [
            "긍정적 실적 발표",
            "신규 사업 확장",
            "업계 호황"
        ]
    }
    return BaseResponse.ok(data=mock_response)