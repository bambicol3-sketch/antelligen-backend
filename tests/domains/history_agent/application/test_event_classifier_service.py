"""EventClassifierService — MAJOR_EVENT만 LLM 재분류, reclassified_type 영속화."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.history_agent.application.response.timeline_response import TimelineEvent
from app.domains.history_agent.application.service.event_classifier_service import (
    EventClassifierService,
)
from app.domains.history_agent.domain.entity.event_enrichment import (
    EventEnrichment,
    compute_detail_hash,
)

pytestmark = pytest.mark.asyncio


def _event(
    idx: int,
    *,
    category: str = "ANNOUNCEMENT",
    event_type: str = "MAJOR_EVENT",
    items_str: str = "8.01",
    detail: str | None = None,
) -> TimelineEvent:
    return TimelineEvent(
        title=f"title-{idx}",
        date=datetime.date(2024, 1, idx + 1),
        category=category,
        type=event_type,
        detail=detail or f"detail-{idx}",
        items_str=items_str,
    )


class _FakeLLM:
    def __init__(self, types: list[str]):
        # JSON 배열로 출력
        self._payload = "[" + ",".join(f'"{t}"' for t in types) + "]"
        self.calls = 0

    async def ainvoke(self, messages):
        self.calls += 1
        mock_response = MagicMock()
        mock_response.content = self._payload
        return mock_response


async def test_classifier_reclassifies_major_event_with_llm():
    """MAJOR_EVENT만 LLM 호출. 재분류 시 event.type을 in-place로 갱신."""
    events = [
        _event(0, items_str="2.02", detail="Q4 results"),         # → EARNINGS_RELEASE
        _event(1, items_str="8.01", detail="senior notes due 2030"),  # → DEBT_ISSUANCE
        _event(2, items_str="8.01", detail="annual meeting voted"),   # → SHAREHOLDER_MEETING
    ]
    repo = MagicMock()
    repo.find_by_keys = AsyncMock(return_value=[])
    repo.upsert_bulk = AsyncMock(return_value=3)

    fake_llm = _FakeLLM(["EARNINGS_RELEASE", "DEBT_ISSUANCE", "SHAREHOLDER_MEETING"])

    with patch(
        "app.domains.history_agent.application.service.event_classifier_service.get_workflow_llm",
        return_value=fake_llm,
    ):
        service = EventClassifierService(enrichment_repo=repo)
        await service.classify("AAPL", events)

    assert events[0].type == "EARNINGS_RELEASE"
    assert events[1].type == "DEBT_ISSUANCE"
    assert events[2].type == "SHAREHOLDER_MEETING"
    assert all(e.classifier_version == "v2" for e in events)
    assert fake_llm.calls == 1
    repo.upsert_bulk.assert_awaited_once()
    saved = repo.upsert_bulk.call_args.args[0]
    assert all(row.classifier_version == "v2" for row in saved)
    assert all(row.event_type == "MAJOR_EVENT" for row in saved)  # 원본 type 보존
    assert [row.reclassified_type for row in saved] == [
        "EARNINGS_RELEASE", "DEBT_ISSUANCE", "SHAREHOLDER_MEETING",
    ]


async def test_classifier_skips_non_major_event():
    """이미 명시 분류된 type은 신뢰하고 건드리지 않음."""
    events = [
        _event(0, event_type="MERGER_ACQUISITION"),
        _event(1, event_type="CRISIS"),
    ]
    repo = MagicMock()
    repo.find_by_keys = AsyncMock(return_value=[])

    fake_llm = _FakeLLM(["MAJOR_EVENT"])  # 호출되지 않아야 함

    with patch(
        "app.domains.history_agent.application.service.event_classifier_service.get_workflow_llm",
        return_value=fake_llm,
    ):
        service = EventClassifierService(enrichment_repo=repo)
        await service.classify("AAPL", events)

    assert events[0].type == "MERGER_ACQUISITION"
    assert events[1].type == "CRISIS"
    assert fake_llm.calls == 0
    repo.find_by_keys.assert_not_awaited()


async def test_classifier_uses_cache_when_available():
    """v2 캐시 hit 시 LLM 미호출. reclassified_type을 event.type에 적용."""
    events = [_event(0, items_str="2.02", detail="Q3 results")]
    cached = [
        EventEnrichment(
            ticker="AAPL",
            event_date=events[0].date,
            event_type="MAJOR_EVENT",
            detail_hash=compute_detail_hash(events[0].detail),
            title=events[0].title,
            reclassified_type="EARNINGS_RELEASE",
            classifier_version="v2",
        )
    ]
    repo = MagicMock()
    repo.find_by_keys = AsyncMock(return_value=cached)

    fake_llm = _FakeLLM(["MAJOR_EVENT"])  # 호출되지 않아야 함

    with patch(
        "app.domains.history_agent.application.service.event_classifier_service.get_workflow_llm",
        return_value=fake_llm,
    ):
        service = EventClassifierService(enrichment_repo=repo)
        await service.classify("AAPL", events)

    assert events[0].type == "EARNINGS_RELEASE"
    assert events[0].classifier_version == "v2"
    assert fake_llm.calls == 0


async def test_classifier_keeps_major_event_when_llm_says_so():
    """LLM이 MAJOR_EVENT를 그대로 유지하면 변경 없음 (정상 동작)."""
    events = [_event(0, items_str="8.01", detail="ambiguous content")]
    repo = MagicMock()
    repo.find_by_keys = AsyncMock(return_value=[])
    repo.upsert_bulk = AsyncMock(return_value=1)

    fake_llm = _FakeLLM(["MAJOR_EVENT"])

    with patch(
        "app.domains.history_agent.application.service.event_classifier_service.get_workflow_llm",
        return_value=fake_llm,
    ):
        service = EventClassifierService(enrichment_repo=repo)
        await service.classify("AAPL", events)

    assert events[0].type == "MAJOR_EVENT"
    # classifier_version은 변경 안 됨 (재분류 없음)
    saved = repo.upsert_bulk.call_args.args[0]
    assert saved[0].reclassified_type == "MAJOR_EVENT"


async def test_classifier_falls_back_on_llm_failure():
    """LLM 실패 시 MAJOR_EVENT 유지 (잘못된 재분류보다 안전)."""
    events = [_event(0), _event(1)]
    repo = MagicMock()
    repo.find_by_keys = AsyncMock(return_value=[])
    repo.upsert_bulk = AsyncMock(return_value=2)

    broken_llm = MagicMock()
    broken_llm.ainvoke = AsyncMock(side_effect=RuntimeError("boom"))

    with patch(
        "app.domains.history_agent.application.service.event_classifier_service.get_workflow_llm",
        return_value=broken_llm,
    ):
        service = EventClassifierService(enrichment_repo=repo)
        await service.classify("AAPL", events)

    assert all(e.type == "MAJOR_EVENT" for e in events)


async def test_classifier_rejects_unknown_type():
    """LLM이 후보 외 type 출력 시 MAJOR_EVENT로 안전 fallback."""
    events = [_event(0)]
    repo = MagicMock()
    repo.find_by_keys = AsyncMock(return_value=[])
    repo.upsert_bulk = AsyncMock(return_value=1)

    fake_llm = _FakeLLM(["UNKNOWN_FAKE_TYPE"])

    with patch(
        "app.domains.history_agent.application.service.event_classifier_service.get_workflow_llm",
        return_value=fake_llm,
    ):
        service = EventClassifierService(enrichment_repo=repo)
        await service.classify("AAPL", events)

    assert events[0].type == "MAJOR_EVENT"


async def test_classifier_handles_empty_input():
    repo = MagicMock()
    service = EventClassifierService(enrichment_repo=repo)
    await service.classify("AAPL", [])
    # find_by_keys 호출 없어야 함
