from typing import Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.app_exception import AppException
from app.domains.authentication.adapter.outbound.cache.session_query_cache_impl import SessionQueryCacheImpl
from app.domains.authentication.adapter.outbound.cache.temp_token_query_cache_impl import TempTokenQueryCacheImpl
from app.domains.authentication.adapter.outbound.persistence.account_info_query_impl import AccountInfoQueryImpl
from app.domains.authentication.application.usecase.get_auth_me_usecase import GetAuthMeUseCase
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.database.database import get_db

router = APIRouter(prefix="/authentication", tags=["authentication"])


@router.get("/me")
async def get_me(
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise AppException(status_code=401, message="토큰이 없습니다.")

    token = authorization.removeprefix("Bearer ").strip()

    return await GetAuthMeUseCase(
        temp_token_query_port=TempTokenQueryCacheImpl(redis),
        session_query_port=SessionQueryCacheImpl(redis),
        account_info_query_port=AccountInfoQueryImpl(db),
    ).execute(token=token)
