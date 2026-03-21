import uuid

import redis.asyncio as aioredis

from app.domains.account.application.port.out.account_token_cache_port import AccountTokenCachePort

KAKAO_TOKEN_KEY_PREFIX = "kakao_token:"
SESSION_KEY_PREFIX = "session:"


class AccountTokenCacheImpl(AccountTokenCachePort):
    def __init__(self, redis: aioredis.Redis, user_token_ttl: int):
        self._redis = redis
        self._user_token_ttl = user_token_ttl

    async def save_kakao_token(self, account_id: int, kakao_access_token: str) -> None:
        await self._redis.setex(
            f"{KAKAO_TOKEN_KEY_PREFIX}{account_id}",
            self._user_token_ttl,
            kakao_access_token,
        )

    async def issue_user_token(self, account_id: int) -> str:
        token = str(uuid.uuid4())
        await self._redis.setex(
            f"{SESSION_KEY_PREFIX}{token}",
            self._user_token_ttl,
            str(account_id),
        )
        return token
