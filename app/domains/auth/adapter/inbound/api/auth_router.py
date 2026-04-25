import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response.base_response import BaseResponse
from app.domains.account.adapter.outbound.persistence.account_repository_impl import AccountRepositoryImpl
from app.domains.account.adapter.outbound.persistence.account_save_repository_impl import AccountSaveRepositoryImpl
from app.domains.account.adapter.outbound.persistence.stock_master_repository_impl import StockMasterRepositoryImpl
from app.domains.account.adapter.outbound.persistence.watchlist_repository_impl import WatchlistRepositoryImpl
from app.domains.account.application.request.signup_request import SignupRequest
from app.domains.account.application.response.signup_response import SignupResponse
from app.domains.account.application.usecase.signup_usecase import SignupUseCase
from app.domains.auth.adapter.outbound.in_memory.redis_session_repository import RedisSessionRepository
from app.domains.auth.application.request.login_request import LoginRequest
from app.domains.auth.application.usecase.get_session_usecase import GetSessionUseCase
from app.domains.auth.application.usecase.login_usecase import LoginUseCase
from app.domains.auth.application.usecase.logout_usecase import LogoutUseCase
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

settings = get_settings()


@router.post("/signup", response_model=BaseResponse[SignupResponse], status_code=201)
async def signup(
    request: SignupRequest,
    db: AsyncSession = Depends(get_db),
):
    """관심종목을 선택하여 회원가입한다. 인증 불필요."""
    usecase = SignupUseCase(
        account_repository=AccountRepositoryImpl(db),
        account_save_port=AccountSaveRepositoryImpl(db),
        stock_master_port=StockMasterRepositoryImpl(db),
        watchlist_save_port=WatchlistRepositoryImpl(db),
    )
    result = await usecase.execute(request)
    return BaseResponse.ok(data=result, message="회원가입이 완료되었습니다.")


@router.post("/login")
async def login(
    request: LoginRequest,
    redis: aioredis.Redis = Depends(get_redis),
):
    repo = RedisSessionRepository(redis)
    usecase = LoginUseCase(repo, settings.auth_password, settings.session_ttl_seconds)
    try:
        response = await usecase.execute(request)
        return BaseResponse.ok(data=response, message="로그인 성공")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid credentials")


@router.get("/session/{token}")
async def get_session(
    token: str,
    redis: aioredis.Redis = Depends(get_redis),
):
    repo = RedisSessionRepository(redis)
    usecase = GetSessionUseCase(repo)
    session = await usecase.execute(token)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return BaseResponse.ok(data=session)


@router.delete("/logout/{token}")
async def logout(
    token: str,
    redis: aioredis.Redis = Depends(get_redis),
):
    repo = RedisSessionRepository(redis)
    usecase = LogoutUseCase(repo)
    await usecase.execute(token)
    return BaseResponse.ok(message="로그아웃 성공")
