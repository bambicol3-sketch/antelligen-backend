from typing import Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Cookie, Depends, Header, Path, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.app_exception import AppException
from app.common.response.base_response import BaseResponse
from app.domains.account.adapter.outbound.persistence.stock_master_repository_impl import StockMasterRepositoryImpl
from app.domains.account.adapter.outbound.persistence.watchlist_repository_impl import WatchlistRepositoryImpl
from app.domains.account.application.request.add_watchlist_stock_request import AddWatchlistStockRequest
from app.domains.account.application.response.watchlist_response import GetWatchlistResponse, WatchlistResponse
from app.domains.account.application.request.update_watchlist_stock_request import UpdateWatchlistStockRequest
from app.domains.account.application.usecase.add_watchlist_stock_usecase import AddWatchlistStockUseCase
from app.domains.account.application.usecase.get_watchlist_usecase import GetWatchlistUseCase
from app.domains.account.application.usecase.remove_watchlist_stock_usecase import RemoveWatchlistStockUseCase
from app.domains.account.application.usecase.update_watchlist_stock_usecase import UpdateWatchlistStockUseCase
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.database.database import get_db

router = APIRouter(prefix="/users", tags=["users"])

SESSION_KEY_PREFIX = "session:"


def _extract_token(user_token: Optional[str], authorization: Optional[str]) -> Optional[str]:
    if user_token:
        return user_token
    if authorization and authorization.startswith("Bearer "):
        return authorization.removeprefix("Bearer ").strip()
    return None


async def _resolve_account_id(
    user_token: Optional[str],
    authorization: Optional[str],
    redis: aioredis.Redis,
) -> int:
    token = _extract_token(user_token, authorization)
    if not token:
        raise AppException(status_code=401, message="인증이 필요합니다.")
    account_id_str = await redis.get(f"{SESSION_KEY_PREFIX}{token}")
    if not account_id_str:
        raise AppException(status_code=401, message="세션이 만료되었거나 유효하지 않습니다.")
    return int(account_id_str)


@router.get("/me/watchlist", response_model=BaseResponse[GetWatchlistResponse])
async def get_watchlist(
    user_token: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """인증된 사용자의 관심종목 목록을 종목 코드·종목명·테마명과 함께 반환한다."""
    account_id = await _resolve_account_id(user_token, authorization, redis)
    usecase = GetWatchlistUseCase(watchlist_port=WatchlistRepositoryImpl(db))
    result = await usecase.execute(account_id=account_id)
    return BaseResponse.ok(data=result)


@router.post("/me/watchlist", response_model=BaseResponse[WatchlistResponse], status_code=201)
async def add_watchlist_stock(
    request: AddWatchlistStockRequest,
    user_token: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """인증된 사용자의 관심종목에 종목을 추가한다. 성공 시 전체 watchlist를 반환한다."""
    account_id = await _resolve_account_id(user_token, authorization, redis)

    usecase = AddWatchlistStockUseCase(
        watchlist_port=WatchlistRepositoryImpl(db),
        stock_master_port=StockMasterRepositoryImpl(db),
    )
    result = await usecase.execute(account_id=account_id, stock_code=request.stock_code)
    return BaseResponse.ok(data=result, message="관심종목이 등록되었습니다.")


@router.put("/me/watchlist/{stock_code}", response_model=BaseResponse[GetWatchlistResponse])
async def update_watchlist_stock(
    request: UpdateWatchlistStockRequest,
    stock_code: str = Path(..., description="교체 대상 기존 종목 코드"),
    user_token: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """인증된 사용자의 관심종목에서 기존 종목을 새 종목으로 교체한다."""
    account_id = await _resolve_account_id(user_token, authorization, redis)
    usecase = UpdateWatchlistStockUseCase(
        watchlist_port=WatchlistRepositoryImpl(db),
        stock_master_port=StockMasterRepositoryImpl(db),
    )
    result = await usecase.execute(
        account_id=account_id,
        old_stock_code=stock_code,
        new_stock_code=request.new_stock_code,
    )
    return BaseResponse.ok(data=result, message="관심종목이 수정되었습니다.")


@router.delete("/me/watchlist/{stock_code}", status_code=204)
async def remove_watchlist_stock(
    stock_code: str = Path(..., description="삭제할 종목 코드"),
    user_token: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """인증된 사용자의 관심종목에서 종목을 삭제한다."""
    account_id = await _resolve_account_id(user_token, authorization, redis)
    usecase = RemoveWatchlistStockUseCase(watchlist_port=WatchlistRepositoryImpl(db))
    await usecase.execute(account_id=account_id, stock_code=stock_code)
    return Response(status_code=204)
