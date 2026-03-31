import json
from typing import Any

import redis.asyncio as aioredis

from app.domains.agent.application.port.finance_analysis_cache_port import (
    FinanceAnalysisCachePort,
)

CACHE_KEY_PREFIX = "finance-analysis:"


class RedisFinanceAnalysisCache(FinanceAnalysisCachePort):
    def __init__(self, redis: aioredis.Redis, ttl_seconds: int):
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    async def get(self, cache_key: str) -> dict[str, Any] | None:
        raw = await self._redis.get(f"{CACHE_KEY_PREFIX}{cache_key}")
        if not raw:
            return None
        return json.loads(raw)

    async def set(self, cache_key: str, payload: dict[str, Any]) -> None:
        await self._redis.setex(
            f"{CACHE_KEY_PREFIX}{cache_key}",
            self._ttl_seconds,
            json.dumps(payload, ensure_ascii=False),
        )
