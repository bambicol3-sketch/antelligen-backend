"""
DB enrichment 캐시 통합 테스트.

EventEnrichmentRepository를 mock으로 대체하므로
실제 DB 없이 즉시 실행된다.
"""
import datetime
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.history_agent.application.response.timeline_response import (
    HypothesisResult,
    TimelineEvent,
)
from app.domains.history_agent.application.service.title_generation_service import (
    FALLBACK_TITLE as _FALLBACK_TITLE,
    is_fallback_title as _is_fallback_title,
)
from app.domains.history_agent.application.usecase.history_agent_usecase import (
    HistoryAgentUseCase,
)
from app.domains.history_agent.domain.entity.event_enrichment import (
    EventEnrichment,
    compute_detail_hash,
)

_TODAY = datetime.date.today()
_TICKER = "AAPL"


def _make_event(
    event_type: str,
    detail: str = "테스트 이벤트",
    days_ago: int = 5,
    category: str = "PRICE",
) -> TimelineEvent:
    return TimelineEvent(
        title=_FALLBACK_TITLE.get(event_type, event_type),
        date=_TODAY - datetime.timedelta(days=days_ago),
        category=category,
        type=event_type,
        detail=detail,
    )


def _make_enrichment(event: TimelineEvent, title: str, causality=None) -> EventEnrichment:
    return EventEnrichment(
        ticker=_TICKER,
        event_date=event.date,
        event_type=event.type,
        detail_hash=compute_detail_hash(event.detail),
        title=title,
        causality=causality,
    )


def _make_usecase(enrichment_repo) -> HistoryAgentUseCase:
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()
    return HistoryAgentUseCase(
        stock_bars_port=MagicMock(),
        yfinance_corporate_port=MagicMock(),
        dart_corporate_client=MagicMock(),
        sec_edgar_port=MagicMock(),
        dart_announcement_client=MagicMock(),
        redis=redis_mock,
        enrichment_repo=enrichment_repo,
        asset_type_port=MagicMock(),
        fred_macro_port=MagicMock(),
    )


# ─────────────────────────────────────────────────────────────
# _is_fallback_title
# ─────────────────────────────────────────────────────────────

def test_is_fallback_title_returns_true_for_fallback():
    event = _make_event("SURGE")
    assert _is_fallback_title(event) is True


def test_is_fallback_title_returns_false_for_enriched():
    event = _make_event("SURGE")
    event.title = "연준 금리 동결 기대감"
    assert _is_fallback_title(event) is False


# ─────────────────────────────────────────────────────────────
# _load_enrichments / _apply_enrichments
# ─────────────────────────────────────────────────────────────

async def test_apply_enrichments_sets_title_from_db():
    """DB에 있는 이벤트는 DB의 title로 교체된다."""
    event = _make_event("SURGE", detail="급등 +8%")
    enrichment = _make_enrichment(event, title="관세 유예 기대감")

    repo = AsyncMock()
    repo.find_by_keys = AsyncMock(return_value=[enrichment])
    repo.upsert_bulk = AsyncMock(return_value=0)

    usecase = _make_usecase(repo)
    db_map = await usecase._load_enrichments(_TICKER, [event])
    new_events = usecase._apply_enrichments(_TICKER, [event], db_map)

    assert event.title == "관세 유예 기대감"
    assert new_events == []  # DB hit → 신규 없음


async def test_apply_enrichments_sets_causality_from_db():
    """DB에 causality가 있으면 HypothesisResult로 복원된다."""
    event = _make_event("PLUNGE", detail="급락 -6%")
    causality_data = [
        {"hypothesis": "관세 충격 → 매도세", "supporting_tools_called": ["get_fred_series"]}
    ]
    enrichment = _make_enrichment(event, title="관세 충격", causality=causality_data)

    repo = AsyncMock()
    repo.find_by_keys = AsyncMock(return_value=[enrichment])

    usecase = _make_usecase(repo)
    db_map = await usecase._load_enrichments(_TICKER, [event])
    usecase._apply_enrichments(_TICKER, [event], db_map)

    assert event.causality is not None
    assert isinstance(event.causality[0], HypothesisResult)
    assert event.causality[0].hypothesis == "관세 충격 → 매도세"


async def test_apply_enrichments_returns_new_events_for_db_miss():
    """DB에 없는 이벤트는 new_events로 반환된다."""
    event = _make_event("GAP_UP", detail="갭 상승 +3%")

    repo = AsyncMock()
    repo.find_by_keys = AsyncMock(return_value=[])  # DB miss

    usecase = _make_usecase(repo)
    db_map = await usecase._load_enrichments(_TICKER, [event])
    new_events = usecase._apply_enrichments(_TICKER, [event], db_map)

    assert new_events == [event]
    assert _is_fallback_title(event)  # fallback 그대로


# ─────────────────────────────────────────────────────────────
# LLM 호출 0건 검증 (신규 이벤트 없을 때)
# ─────────────────────────────────────────────────────────────

async def test_no_llm_call_when_all_events_in_db():
    """모든 이벤트가 DB에 있으면 LLM이 호출되지 않는다."""
    events = [
        _make_event("SURGE", detail="급등 A", days_ago=3),
        _make_event("PLUNGE", detail="급락 B", days_ago=5),
        _make_event("GAP_UP", detail="갭 상승 C", days_ago=7),
    ]
    enrichments = [
        _make_enrichment(e, title=f"DB 타이틀 {i}") for i, e in enumerate(events)
    ]

    repo = AsyncMock()
    repo.find_by_keys = AsyncMock(return_value=enrichments)
    repo.upsert_bulk = AsyncMock(return_value=0)

    usecase = _make_usecase(repo)
    db_map = await usecase._load_enrichments(_TICKER, events)
    new_events = usecase._apply_enrichments(_TICKER, events, db_map)

    assert new_events == []

    with patch(
        "app.domains.history_agent.application.usecase.history_agent_usecase.get_workflow_llm"
    ) as mock_llm:
        await usecase._save_enrichments(_TICKER, new_events)
        mock_llm.assert_not_called()

    for i, event in enumerate(events):
        assert event.title == f"DB 타이틀 {i}"


# ─────────────────────────────────────────────────────────────
# 신규 이벤트만 DB 저장 검증
# ─────────────────────────────────────────────────────────────

async def test_save_enrichments_only_saves_new_events():
    """_save_enrichments는 new_events만 DB에 저장한다."""
    new_event = _make_event("SURGE", detail="급등 신규")
    new_event.title = "LLM 생성 타이틀"

    repo = AsyncMock()
    repo.upsert_bulk = AsyncMock(return_value=1)

    usecase = _make_usecase(repo)
    await usecase._save_enrichments(_TICKER, [new_event])

    repo.upsert_bulk.assert_called_once()
    saved = repo.upsert_bulk.call_args[0][0]
    assert len(saved) == 1
    assert saved[0].title == "LLM 생성 타이틀"
    assert saved[0].ticker == _TICKER
    assert saved[0].detail_hash == compute_detail_hash("급등 신규")


async def test_save_enrichments_skips_when_no_new_events():
    """new_events가 없으면 upsert_bulk가 호출되지 않는다."""
    repo = AsyncMock()
    repo.upsert_bulk = AsyncMock()

    usecase = _make_usecase(repo)
    await usecase._save_enrichments(_TICKER, [])

    repo.upsert_bulk.assert_not_called()


# ─────────────────────────────────────────────────────────────
# Redis 캐시 유지 검증
# ─────────────────────────────────────────────────────────────

async def test_no_llm_title_call_when_enrich_titles_false():
    """enrich_titles=False이면 enrich_price_titles / enrich_other_titles가 호출되지 않는다."""
    from app.domains.dashboard.application.response.announcement_response import AnnouncementsResponse
    from app.domains.dashboard.application.response.corporate_event_response import CorporateEventsResponse
    from app.domains.dashboard.application.response.price_event_response import PriceEventsResponse

    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()

    repo = AsyncMock()
    repo.find_by_keys = AsyncMock(return_value=[])
    repo.upsert_bulk = AsyncMock(return_value=0)

    asset_type_mock = AsyncMock()
    asset_type_mock.get_quote_type = AsyncMock(return_value="EQUITY")

    usecase = HistoryAgentUseCase(
        stock_bars_port=MagicMock(),
        yfinance_corporate_port=MagicMock(),
        dart_corporate_client=MagicMock(),
        sec_edgar_port=MagicMock(),
        dart_announcement_client=MagicMock(),
        redis=redis_mock,
        enrichment_repo=repo,
        asset_type_port=asset_type_mock,
        fred_macro_port=MagicMock(),
    )

    _module = "app.domains.history_agent.application.usecase.history_agent_usecase"

    price_response = PriceEventsResponse(ticker=_TICKER, period="1M", count=0, events=[])
    corp_response = CorporateEventsResponse(ticker=_TICKER, period="1M", count=0, events=[])
    ann_response = AnnouncementsResponse(ticker=_TICKER, period="1M", count=0, events=[])

    with patch(f"{_module}.enrich_price_titles", new_callable=AsyncMock) as mock_price_titles, \
         patch(f"{_module}.enrich_other_titles", new_callable=AsyncMock) as mock_other_titles, \
         patch(f"{_module}.GetPriceEventsUseCase") as MockPriceUC, \
         patch(f"{_module}.GetCorporateEventsUseCase") as MockCorpUC, \
         patch(f"{_module}.GetAnnouncementsUseCase") as MockAnnUC, \
         patch(f"{_module}._enrich_causality", new_callable=AsyncMock), \
         patch(f"{_module}._enrich_announcement_details", new_callable=AsyncMock):

        MockPriceUC.return_value.execute = AsyncMock(return_value=price_response)
        MockCorpUC.return_value.execute = AsyncMock(return_value=corp_response)
        MockAnnUC.return_value.execute = AsyncMock(return_value=ann_response)

        await usecase.execute(ticker=_TICKER, period="1M", enrich_titles=False)

        mock_price_titles.assert_not_called()
        mock_other_titles.assert_not_called()


async def test_redis_cache_hit_skips_db_query():
    """Redis 캐시 히트 시 DB 조회가 수행되지 않는다."""
    from app.domains.history_agent.application.response.timeline_response import TimelineResponse

    cached_response = TimelineResponse(ticker=_TICKER, period="1M", count=0, events=[])

    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=cached_response.model_dump_json())

    repo = AsyncMock()
    repo.find_by_keys = AsyncMock()

    asset_type_mock = AsyncMock()
    asset_type_mock.get_quote_type = AsyncMock(return_value="EQUITY")

    usecase = HistoryAgentUseCase(
        stock_bars_port=MagicMock(),
        yfinance_corporate_port=MagicMock(),
        dart_corporate_client=MagicMock(),
        sec_edgar_port=MagicMock(),
        dart_announcement_client=MagicMock(),
        redis=redis_mock,
        enrichment_repo=repo,
        asset_type_port=asset_type_mock,
        fred_macro_port=MagicMock(),
    )

    result = await usecase.execute(ticker=_TICKER, period="1M")

    assert result.ticker == _TICKER
    repo.find_by_keys.assert_not_called()
