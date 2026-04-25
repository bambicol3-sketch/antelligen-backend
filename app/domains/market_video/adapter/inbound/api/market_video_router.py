from typing import Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Cookie, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.app_exception import AppException
from app.common.response.base_response import BaseResponse
from app.domains.account.adapter.outbound.persistence.account_repository_impl import AccountRepositoryImpl
from app.domains.account.adapter.outbound.persistence.watchlist_repository_impl import WatchlistRepositoryImpl
from app.domains.market_video.adapter.outbound.external.youtube_channel_video_client import YoutubeChannelVideoClient
from app.domains.market_video.adapter.outbound.external.youtube_comment_client import YoutubeCommentClient
from app.domains.market_video.adapter.outbound.external.youtube_search_client import YoutubeSearchClient
from app.domains.market_video.adapter.outbound.external.youtube_video_client import YoutubeVideoClient
from app.domains.market_video.adapter.outbound.persistence.collected_video_repository_impl import CollectedVideoRepositoryImpl
from app.domains.market_video.adapter.outbound.persistence.video_comment_repository_impl import VideoCommentRepositoryImpl
from app.domains.market_video.application.usecase.collect_defense_video_usecase import CollectDefenseVideoUseCase
from app.domains.market_video.application.usecase.collect_video_comments_usecase import CollectVideoCommentsUseCase
from app.domains.market_video.application.usecase.extract_nouns_usecase import ExtractNounsUseCase
from app.domains.market_video.application.usecase.get_watchlist_youtube_feed_usecase import GetWatchlistYoutubeFeedUseCase
from app.domains.market_video.application.usecase.get_youtube_video_list_usecase import GetYoutubeVideoListUseCase
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.database import get_db
from app.infrastructure.nlp.kiwi_morpheme_analyzer import get_morpheme_analyzer

SESSION_KEY_PREFIX = "session:"

router = APIRouter(prefix="/youtube", tags=["youtube"])


@router.get("/feed")
async def get_youtube_feed(
    page_token: Optional[str] = Query(default=None, description="페이지 토큰 (더보기용)"),
    user_token: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """인증된 사용자는 관심종목 기반 YouTube 영상을, 비로그인 사용자는 전체 테마 기본 영상을 반환한다."""
    account_id: Optional[int] = None
    token = user_token
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
    if token:
        account_id_str = await redis.get(f"{SESSION_KEY_PREFIX}{token}")
        if account_id_str:
            account_id = int(account_id_str)

    settings = get_settings()
    search_client = YoutubeSearchClient(api_key=settings.youtube_api_key)
    watchlist_repo = WatchlistRepositoryImpl(db)
    usecase = GetWatchlistYoutubeFeedUseCase(
        youtube_search_port=search_client,
        watchlist_port=watchlist_repo,
    )
    result = await usecase.execute(account_id=account_id, page_token=page_token)
    return BaseResponse.ok(data=result)


@router.get("/list")
async def get_youtube_video_list(
    page_token: Optional[str] = Query(default=None),
    user_token: str = Cookie(None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    if not user_token:
        raise AppException(status_code=401, message="인증이 필요합니다.")

    account_id_str = await redis.get(f"{SESSION_KEY_PREFIX}{user_token}")
    if not account_id_str:
        raise AppException(status_code=401, message="세션이 만료되었거나 유효하지 않습니다.")

    account_id = int(account_id_str)

    account_repo = AccountRepositoryImpl(db)
    account = await account_repo.find_by_id(account_id)
    if not account:
        raise AppException(status_code=401, message="유효하지 않은 계정입니다.")

    settings = get_settings()
    provider = YoutubeVideoClient(api_key=settings.youtube_api_key)
    usecase = GetYoutubeVideoListUseCase(youtube_video_provider=provider)
    response = await usecase.execute(page_token=page_token)

    return BaseResponse.ok(data=response, message="YouTube 영상 목록 조회 성공")


@router.post("/collect")
async def collect_defense_videos(
    user_token: str = Cookie(None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    if not user_token:
        raise AppException(status_code=401, message="인증이 필요합니다.")

    account_id_str = await redis.get(f"{SESSION_KEY_PREFIX}{user_token}")
    if not account_id_str:
        raise AppException(status_code=401, message="세션이 만료되었거나 유효하지 않습니다.")

    account_id = int(account_id_str)

    account_repo = AccountRepositoryImpl(db)
    account = await account_repo.find_by_id(account_id)
    if not account:
        raise AppException(status_code=401, message="유효하지 않은 계정입니다.")

    settings = get_settings()
    fetch_port = YoutubeChannelVideoClient(api_key=settings.youtube_api_key)
    repository = CollectedVideoRepositoryImpl(db)
    usecase = CollectDefenseVideoUseCase(
        channel_video_fetch_port=fetch_port,
        collected_video_repository_port=repository,
    )
    response = await usecase.execute()

    return BaseResponse.ok(data=response, message="방산 영상 수집 완료")


@router.post("/collect-comments")
async def collect_video_comments(
    user_token: str = Cookie(None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    if not user_token:
        raise AppException(status_code=401, message="인증이 필요합니다.")

    account_id_str = await redis.get(f"{SESSION_KEY_PREFIX}{user_token}")
    if not account_id_str:
        raise AppException(status_code=401, message="세션이 만료되었거나 유효하지 않습니다.")

    account_id = int(account_id_str)

    account_repo = AccountRepositoryImpl(db)
    account = await account_repo.find_by_id(account_id)
    if not account:
        raise AppException(status_code=401, message="유효하지 않은 계정입니다.")

    settings = get_settings()
    comment_client = YoutubeCommentClient(api_key=settings.youtube_api_key)
    collected_video_repo = CollectedVideoRepositoryImpl(db)
    comment_repo = VideoCommentRepositoryImpl(db)
    usecase = CollectVideoCommentsUseCase(
        comment_fetch_port=comment_client,
        collected_video_repository=collected_video_repo,
        video_comment_repository=comment_repo,
    )
    response = await usecase.execute()

    return BaseResponse.ok(data=response, message="댓글 수집 완료")


@router.get("/nouns")
async def extract_nouns(
    top_n: int = Query(default=30, ge=1, le=200),
    user_token: str = Cookie(None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    if not user_token:
        raise AppException(status_code=401, message="인증이 필요합니다.")

    account_id_str = await redis.get(f"{SESSION_KEY_PREFIX}{user_token}")
    if not account_id_str:
        raise AppException(status_code=401, message="세션이 만료되었거나 유효하지 않습니다.")

    account_id = int(account_id_str)

    account_repo = AccountRepositoryImpl(db)
    account = await account_repo.find_by_id(account_id)
    if not account:
        raise AppException(status_code=401, message="유효하지 않은 계정입니다.")

    comment_repo = VideoCommentRepositoryImpl(db)
    analyzer = get_morpheme_analyzer()
    usecase = ExtractNounsUseCase(
        video_comment_repository=comment_repo,
        morpheme_analyzer=analyzer,
    )
    response = await usecase.execute(top_n=top_n)

    return BaseResponse.ok(data=response, message="명사 추출 성공")
