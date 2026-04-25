"""GetCompanyProfileUseCase asset_type 분기 검증.

- INDEX/ETF 티커 → 합성 profile + generate_for_asset
- EQUITY (US/KR) 티커 → 기존 경로 유지
- asset_type_port 가 UNKNOWN/미지원 타입 반환 → EQUITY 폴백
"""
from typing import Optional

import pytest

from app.domains.company_profile.application.usecase.get_company_profile_usecase import (
    GetCompanyProfileUseCase,
)
from app.domains.company_profile.domain.entity.company_profile import CompanyProfile
from app.domains.company_profile.domain.value_object.business_overview import BusinessOverview


# ── Fakes ────────────────────────────────────────────────────────────────────


class FakeAssetTypePort:
    def __init__(self, quote_type: str):
        self._quote_type = quote_type
        self.calls: list[str] = []

    async def get_quote_type(self, ticker: str) -> str:
        self.calls.append(ticker)
        return self._quote_type


class FakeBusinessOverviewPort:
    def __init__(self):
        self.generate_calls: list[dict] = []
        self.asset_calls: list[dict] = []

    async def generate(
        self,
        corp_name: str,
        induty_code: Optional[str],
        rag_context: Optional[str],
    ) -> Optional[BusinessOverview]:
        self.generate_calls.append(
            {"corp_name": corp_name, "induty_code": induty_code, "rag_context": rag_context}
        )
        return BusinessOverview(
            summary=f"{corp_name} 사업 요약",
            revenue_sources=["부문1"],
            source="llm_only",
            founding_story="창업 배경",
            business_model="비즈니스 모델",
        )

    async def generate_for_asset(
        self,
        ticker: str,
        asset_type: str,
    ) -> Optional[BusinessOverview]:
        self.asset_calls.append({"ticker": ticker, "asset_type": asset_type})
        return BusinessOverview(
            summary=f"{ticker} ({asset_type}) 설명",
            revenue_sources=["테마1", "테마2"],
            source="asset_llm_only",
            founding_story=None,
            business_model=None,
        )


class InMemoryOverviewCache:
    def __init__(self):
        self._store: dict[str, BusinessOverview] = {}
        self.save_calls: list[tuple[str, BusinessOverview, int]] = []

    async def get(self, key: str) -> Optional[BusinessOverview]:
        return self._store.get(key)

    async def save(self, key: str, overview: BusinessOverview, ttl_seconds: int) -> None:
        self.save_calls.append((key, overview, ttl_seconds))
        self._store[key] = overview


class InMemoryProfileCache:
    def __init__(self):
        self._store: dict[str, CompanyProfile] = {}

    async def get(self, key: str) -> Optional[CompanyProfile]:
        return self._store.get(key)

    async def save(self, key: str, profile: CompanyProfile, ttl_seconds: int) -> None:
        self._store[key] = profile


class FakeCompanyRepository:
    def __init__(self, found: bool, corp_code: str = "00126380"):
        self._found = found
        self._corp_code = corp_code
        self.calls: list[str] = []

    async def find_by_stock_code(self, stock_code: str):
        self.calls.append(stock_code)
        if not self._found:
            return None

        class _Co:
            corp_code = self._corp_code

        return _Co()


class FakeDartCompanyInfo:
    def __init__(self, profile: Optional[CompanyProfile]):
        self._profile = profile
        self.calls: list[str] = []

    async def fetch(self, corp_code: str) -> Optional[CompanyProfile]:
        self.calls.append(corp_code)
        return self._profile


class FakeUsCompanyName:
    async def resolve_company_name(self, ticker: str) -> Optional[str]:
        return f"{ticker} Inc."


def _kr_profile() -> CompanyProfile:
    return CompanyProfile(
        corp_code="00126380",
        corp_name="삼성전자",
        corp_name_eng="Samsung Electronics",
        stock_name="삼성전자",
        stock_code="005930",
        ceo_nm="이재용",
        corp_cls="Y",
        jurir_no=None,
        bizr_no=None,
        adres=None,
        hm_url=None,
        ir_url=None,
        phn_no=None,
        fax_no=None,
        induty_code="264",
        est_dt=None,
        acc_mt=None,
    )


def _build_usecase(
    asset_type: str,
    *,
    company_found: bool = True,
    profile: Optional[CompanyProfile] = None,
):
    asset_port = FakeAssetTypePort(asset_type)
    overview_port = FakeBusinessOverviewPort()
    overview_cache = InMemoryOverviewCache()
    profile_cache = InMemoryProfileCache()
    repo = FakeCompanyRepository(found=company_found)
    dart = FakeDartCompanyInfo(profile or _kr_profile())

    usecase = GetCompanyProfileUseCase(
        company_repository=repo,
        dart_company_info=dart,
        cache=profile_cache,
        rag_chunk_repository=None,
        business_overview=overview_port,
        overview_cache=overview_cache,
        us_company_name=FakeUsCompanyName(),
        asset_type_port=asset_port,
    )
    return usecase, asset_port, overview_port, overview_cache, repo, dart


# ── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_index_ticker_uses_asset_branch():
    usecase, asset_port, overview_port, overview_cache, repo, dart = _build_usecase("INDEX")
    profile, overview = await usecase.execute("^IXIC")

    assert profile is not None
    assert profile.asset_type == "INDEX"
    assert profile.corp_code == "^IXIC"

    assert len(overview_port.asset_calls) == 1
    assert overview_port.asset_calls[0] == {"ticker": "^IXIC", "asset_type": "INDEX"}
    assert overview_port.generate_calls == []

    assert overview is not None
    assert overview.source == "asset_llm_only"

    # DART/repo 미접근
    assert repo.calls == []
    assert dart.calls == []

    # 캐시는 asset: namespace 사용
    saved_keys = [k for k, _, _ in overview_cache.save_calls]
    assert saved_keys == ["asset:^IXIC"]


@pytest.mark.asyncio
async def test_etf_ticker_uses_asset_branch():
    usecase, _, overview_port, overview_cache, repo, dart = _build_usecase("ETF")
    profile, overview = await usecase.execute("SPY")

    assert profile is not None
    assert profile.asset_type == "ETF"

    assert overview_port.asset_calls == [{"ticker": "SPY", "asset_type": "ETF"}]
    assert overview_port.generate_calls == []
    assert overview is not None
    assert overview.source == "asset_llm_only"
    assert repo.calls == []
    assert dart.calls == []
    assert [k for k, _, _ in overview_cache.save_calls] == ["asset:SPY"]


@pytest.mark.asyncio
async def test_us_equity_falls_through_to_us_branch():
    usecase, _, overview_port, _, repo, dart = _build_usecase("EQUITY")
    profile, overview = await usecase.execute("AAPL")

    assert profile is not None
    assert profile.asset_type == "EQUITY"
    assert profile.corp_cls == "US"
    assert profile.corp_name == "AAPL Inc."

    # SEC 회사명 + LLM-only generate 경로
    assert overview_port.generate_calls == [
        {"corp_name": "AAPL Inc.", "induty_code": None, "rag_context": None}
    ]
    assert overview_port.asset_calls == []
    assert overview is not None

    assert repo.calls == []
    assert dart.calls == []


@pytest.mark.asyncio
async def test_kr_equity_uses_dart_branch():
    usecase, _, overview_port, _, repo, dart = _build_usecase("EQUITY")
    profile, overview = await usecase.execute("005930")

    assert profile is not None
    assert profile.asset_type == "EQUITY"
    assert profile.corp_cls == "Y"
    assert profile.corp_code == "00126380"

    assert overview_port.generate_calls == [
        {"corp_name": "삼성전자", "induty_code": "264", "rag_context": None}
    ]
    assert overview_port.asset_calls == []
    assert overview is not None

    assert repo.calls == ["005930"]
    assert dart.calls == ["00126380"]


@pytest.mark.asyncio
async def test_kr_equity_returns_none_when_company_missing():
    usecase, _, _, _, _, _ = _build_usecase("EQUITY", company_found=False)
    profile, overview = await usecase.execute("999999")

    assert profile is None
    assert overview is None


@pytest.mark.asyncio
async def test_unsupported_asset_type_falls_back_to_equity():
    """yfinance 가 MUTUALFUND 등을 반환해도 EQUITY 경로로 graceful fallback."""
    usecase, _, overview_port, _, repo, _ = _build_usecase("MUTUALFUND")
    # MUTUALFUND → EQUITY 폴백 → US 형식 ticker(MUTF) 는 region.is_us() True (4자리 알파벳)
    profile, _ = await usecase.execute("VFIAX")

    assert profile is not None
    assert profile.asset_type == "EQUITY"
    # asset 분기 안 탐
    assert overview_port.asset_calls == []


@pytest.mark.asyncio
async def test_cache_hit_skips_generate_for_asset():
    usecase, _, overview_port, overview_cache, _, _ = _build_usecase("ETF")
    # 캐시에 미리 저장
    pre = BusinessOverview(
        summary="cached", revenue_sources=[], source="asset_llm_only",
    )
    await overview_cache.save("asset:SPY", pre, 100)
    overview_cache.save_calls.clear()

    _, overview = await usecase.execute("SPY")

    assert overview is pre
    assert overview_port.asset_calls == []  # cache hit → LLM 미호출
    assert overview_cache.save_calls == []  # 재저장 안 함
