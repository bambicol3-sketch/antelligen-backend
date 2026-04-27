"""FredInvestmentInfoClient._fetch_with_retry — 5xx/네트워크 오류 retry 동작 검증."""
import json
from typing import Any

import httpx
import pytest

from app.domains.schedule.adapter.outbound.external import (
    fred_investment_info_client as mod,
)
from app.domains.schedule.adapter.outbound.external.fred_investment_info_client import (
    FredInvestmentInfoClient,
)
from app.domains.schedule.domain.value_object.investment_info_type import (
    InvestmentInfoType,
)


class _MockResponse:
    def __init__(self, status_code: int, body: Any = None):
        self.status_code = status_code
        self._body = body if body is not None else {}
        self.text = json.dumps(self._body) if isinstance(body, dict) else str(body)

    def json(self):
        return self._body


class _MockAsyncClient:
    """미리 준비된 응답을 순서대로 반환. RequestError 도 시뮬레이션."""

    def __init__(self, responses: list):
        # responses: [_MockResponse | Exception, ...]
        self._responses = list(responses)
        self.call_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params=None):
        self.call_count += 1
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _patch_client(monkeypatch, responses: list) -> _MockAsyncClient:
    instance = _MockAsyncClient(responses)

    def _factory(*args, **kwargs):
        return instance

    monkeypatch.setattr(mod.httpx, "AsyncClient", _factory)
    return instance


@pytest.fixture(autouse=True)
def _patch_sleep(monkeypatch):
    """asyncio.sleep 을 즉시 통과시켜 테스트 시간 단축."""
    async def _instant_sleep(*args, **kwargs):
        return None

    monkeypatch.setattr(mod.asyncio, "sleep", _instant_sleep)


@pytest.mark.asyncio
async def test_200_returns_immediately(monkeypatch):
    body = {"observations": [{"date": "2026-04-25", "value": "4.5"}]}
    mock = _patch_client(monkeypatch, [_MockResponse(200, body)])

    client = FredInvestmentInfoClient(api_key="fake", max_retries=2)
    info = await client.fetch(InvestmentInfoType.US_T2Y)

    assert info.value == 4.5
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_500_then_200_retries_once(monkeypatch):
    body = {"observations": [{"date": "2026-04-25", "value": "100.0"}]}
    mock = _patch_client(
        monkeypatch,
        [_MockResponse(500, {"error": "Internal Server Error"}), _MockResponse(200, body)],
    )

    client = FredInvestmentInfoClient(api_key="fake", max_retries=2, initial_backoff=0.01)
    info = await client.fetch(InvestmentInfoType.US_T2Y)

    assert info.value == 100.0
    assert mock.call_count == 2  # 500 → retry → 200


@pytest.mark.asyncio
async def test_500_exhausts_retries_raises(monkeypatch):
    mock = _patch_client(
        monkeypatch,
        [
            _MockResponse(500, {"err": "1"}),
            _MockResponse(500, {"err": "2"}),
            _MockResponse(500, {"err": "3"}),
        ],
    )

    client = FredInvestmentInfoClient(api_key="fake", max_retries=2, initial_backoff=0.01)
    with pytest.raises(RuntimeError, match=r"FRED 응답 오류 status=500"):
        await client.fetch(InvestmentInfoType.US_T2Y)
    assert mock.call_count == 3  # initial + 2 retries


@pytest.mark.asyncio
async def test_4xx_does_not_retry(monkeypatch):
    """400/401/404 같은 4xx 는 deterministic 이라 즉시 fail — retry 안 함."""
    mock = _patch_client(
        monkeypatch,
        [_MockResponse(400, {"error": "Bad request"})],
    )

    client = FredInvestmentInfoClient(api_key="fake", max_retries=2, initial_backoff=0.01)
    with pytest.raises(RuntimeError, match=r"FRED 응답 오류 status=400"):
        await client.fetch(InvestmentInfoType.US_T2Y)
    assert mock.call_count == 1  # 한 번만


@pytest.mark.asyncio
async def test_request_error_retries(monkeypatch):
    body = {"observations": [{"date": "2026-04-25", "value": "1.23"}]}
    mock = _patch_client(
        monkeypatch,
        [
            httpx.ConnectError("connection refused"),
            _MockResponse(200, body),
        ],
    )

    client = FredInvestmentInfoClient(api_key="fake", max_retries=2, initial_backoff=0.01)
    info = await client.fetch(InvestmentInfoType.US_T2Y)

    assert info.value == 1.23
    assert mock.call_count == 2


@pytest.mark.asyncio
async def test_request_error_exhausts_raises(monkeypatch):
    mock = _patch_client(
        monkeypatch,
        [
            httpx.ConnectError("conn err 1"),
            httpx.ConnectError("conn err 2"),
            httpx.ConnectError("conn err 3"),
        ],
    )

    client = FredInvestmentInfoClient(api_key="fake", max_retries=2, initial_backoff=0.01)
    with pytest.raises(httpx.ConnectError):
        await client.fetch(InvestmentInfoType.US_T2Y)
    assert mock.call_count == 3
