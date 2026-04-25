"""RedisBusinessOverviewCache v2 — 신규 필드 round-trip 및 키 prefix 검증."""
import json
from typing import Optional

import pytest

from app.domains.company_profile.adapter.outbound.cache.business_overview_cache import (
    RedisBusinessOverviewCache,
)
from app.domains.company_profile.domain.value_object.business_overview import BusinessOverview


class FakeRedis:
    def __init__(self):
        self._store: dict[str, str] = {}
        self.last_setex_ttl: Optional[int] = None

    async def get(self, key: str):
        return self._store.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self.last_setex_ttl = ttl
        self._store[key] = value


def test_cache_key_uses_v2_prefix():
    assert RedisBusinessOverviewCache._key("00126380") == "company_overview:v2:00126380"
    assert RedisBusinessOverviewCache._key("asset:SPY") == "company_overview:v2:asset:SPY"


@pytest.mark.asyncio
async def test_save_and_get_round_trip_includes_new_fields():
    redis = FakeRedis()
    cache = RedisBusinessOverviewCache(redis)
    overview = BusinessOverview(
        summary="요약",
        revenue_sources=["A", "B"],
        source="rag_summary",
        founding_story="창업 배경",
        business_model="비즈니스 모델",
    )

    await cache.save("00126380", overview, 7200)
    fetched = await cache.get("00126380")

    assert fetched == overview
    assert redis.last_setex_ttl == 7200

    raw = redis._store["company_overview:v2:00126380"]
    payload = json.loads(raw)
    assert payload["founding_story"] == "창업 배경"
    assert payload["business_model"] == "비즈니스 모델"


@pytest.mark.asyncio
async def test_get_returns_none_for_missing_key():
    cache = RedisBusinessOverviewCache(FakeRedis())
    assert await cache.get("nope") is None


@pytest.mark.asyncio
async def test_get_handles_legacy_payload_without_new_fields():
    """v1 payload (founding_story/business_model 없음) 가 v2 prefix 에 들어왔다고 가정한 graceful path."""
    redis = FakeRedis()
    redis._store["company_overview:v2:legacy"] = json.dumps(
        {"summary": "옛 요약", "revenue_sources": [], "source": "llm_only"}
    )
    cache = RedisBusinessOverviewCache(redis)
    fetched = await cache.get("legacy")

    assert fetched is not None
    assert fetched.summary == "옛 요약"
    assert fetched.founding_story is None
    assert fetched.business_model is None


@pytest.mark.asyncio
async def test_save_persists_asset_overview_with_namespaced_key():
    redis = FakeRedis()
    cache = RedisBusinessOverviewCache(redis)
    overview = BusinessOverview(
        summary="ETF 설명",
        revenue_sources=["대형 기술주"],
        source="asset_llm_only",
        founding_story=None,
        business_model=None,
    )

    await cache.save("asset:SPY", overview, 600)
    fetched = await cache.get("asset:SPY")

    assert fetched == overview
    assert "company_overview:v2:asset:SPY" in redis._store
