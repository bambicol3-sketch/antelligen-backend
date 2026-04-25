"""OpenAIBusinessOverviewClient 확장 — founding_story / business_model 파싱 검증.

LLM JSON 응답을 가짜로 주입해 어댑터가 새 두 필드를 어떻게 추출하는지 검증한다.
실제 OpenAI 호출은 하지 않는다.
"""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.domains.company_profile.adapter.outbound.external import (
    openai_business_overview_client as adapter_module,
)
from app.domains.company_profile.adapter.outbound.external.openai_business_overview_client import (
    OpenAIBusinessOverviewClient,
)


def _mock_chat_response(payload: dict):
    raw = json.dumps(payload, ensure_ascii=False)
    message = SimpleNamespace(content=raw)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


def _patch_openai_client(payload: dict):
    """AsyncOpenAI() 인스턴스의 chat.completions.create 를 패치한다."""
    create_mock = AsyncMock(return_value=_mock_chat_response(payload))
    completions = SimpleNamespace(create=create_mock)
    chat = SimpleNamespace(completions=completions)
    instance = SimpleNamespace(chat=chat)
    return patch.object(adapter_module, "AsyncOpenAI", return_value=instance), create_mock


def _patch_settings(api_key="sk-test"):
    return patch.object(
        adapter_module,
        "get_settings",
        return_value=SimpleNamespace(
            openai_api_key=api_key,
            openai_finance_agent_model="gpt-5-mini",
        ),
    )


@pytest.mark.asyncio
async def test_generate_extracts_founding_story_and_business_model():
    payload = {
        "summary": "스마트폰을 만드는 회사.",
        "revenue_sources": ["스마트폰", "반도체", "디스플레이"],
        "founding_story": "1969년 창업. 초기 비전은 전자 산업 진출.",
        "business_model": "B2C 하드웨어 판매 + B2B 메모리 공급으로 수익 창출.",
    }
    openai_patch, _ = _patch_openai_client(payload)
    with _patch_settings(), openai_patch:
        client = OpenAIBusinessOverviewClient()
        result = await client.generate(
            corp_name="삼성전자",
            induty_code="264",
            rag_context=None,
        )

    assert result is not None
    assert result.founding_story == "1969년 창업. 초기 비전은 전자 산업 진출."
    assert result.business_model == "B2C 하드웨어 판매 + B2B 메모리 공급으로 수익 창출."
    assert result.summary == "스마트폰을 만드는 회사."
    assert result.revenue_sources == ["스마트폰", "반도체", "디스플레이"]


@pytest.mark.asyncio
async def test_generate_returns_none_for_missing_keys():
    payload = {
        "summary": "그래픽카드를 만든다.",
        "revenue_sources": ["GPU"],
        # founding_story / business_model 누락
    }
    openai_patch, _ = _patch_openai_client(payload)
    with _patch_settings(), openai_patch:
        client = OpenAIBusinessOverviewClient()
        result = await client.generate(
            corp_name="NVIDIA",
            induty_code=None,
            rag_context=None,
        )

    assert result is not None
    assert result.summary == "그래픽카드를 만든다."
    assert result.founding_story is None
    assert result.business_model is None


@pytest.mark.asyncio
async def test_generate_normalizes_empty_strings_to_none():
    payload = {
        "summary": "검색 광고 회사.",
        "revenue_sources": ["검색 광고"],
        "founding_story": "   ",
        "business_model": "",
    }
    openai_patch, _ = _patch_openai_client(payload)
    with _patch_settings(), openai_patch:
        client = OpenAIBusinessOverviewClient()
        result = await client.generate(
            corp_name="Google",
            induty_code=None,
            rag_context=None,
        )

    assert result is not None
    assert result.founding_story is None
    assert result.business_model is None


@pytest.mark.asyncio
async def test_generate_for_asset_returns_overview_with_asset_source():
    payload = {
        "summary": "S&P 500 추종 ETF.",
        "revenue_sources": ["대형 기술주", "금융", "헬스케어"],
    }
    openai_patch, create_mock = _patch_openai_client(payload)
    with _patch_settings(), openai_patch:
        client = OpenAIBusinessOverviewClient()
        result = await client.generate_for_asset(ticker="SPY", asset_type="ETF")

    assert result is not None
    assert result.summary == "S&P 500 추종 ETF."
    assert result.revenue_sources == ["대형 기술주", "금융", "헬스케어"]
    assert result.source == "asset_llm_only"
    assert result.founding_story is None
    assert result.business_model is None
    # 자산 프롬프트가 사용되었는지 확인 — 시스템 메시지 첫 줄 일부
    sent_messages = create_mock.call_args.kwargs["messages"]
    assert any("자산 분석가" in m["content"] for m in sent_messages if m["role"] == "system")


@pytest.mark.asyncio
async def test_generate_for_asset_returns_none_without_summary():
    payload = {
        "summary": "",
        "revenue_sources": [],
    }
    openai_patch, _ = _patch_openai_client(payload)
    with _patch_settings(), openai_patch:
        client = OpenAIBusinessOverviewClient()
        result = await client.generate_for_asset(ticker="^IXIC", asset_type="INDEX")

    assert result is None


@pytest.mark.asyncio
async def test_generate_returns_none_when_api_key_missing():
    with _patch_settings(api_key=""):
        client = OpenAIBusinessOverviewClient()
        result = await client.generate(
            corp_name="X", induty_code=None, rag_context=None,
        )
        asset = await client.generate_for_asset(ticker="SPY", asset_type="ETF")

    assert result is None
    assert asset is None
