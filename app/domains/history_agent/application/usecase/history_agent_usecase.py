import asyncio
import json
import logging
from datetime import timedelta
from typing import Awaitable, Callable, Dict, List, Optional, Tuple

import redis.asyncio as aioredis
from langchain_core.messages import HumanMessage, SystemMessage

from app.domains.dashboard.adapter.outbound.external.dart_announcement_client import (
    DartAnnouncementClient,
)
from app.domains.dashboard.adapter.outbound.external.dart_corporate_event_client import (
    DartCorporateEventClient,
)
from app.domains.dashboard.application.port.out.asset_type_port import AssetTypePort
from app.domains.dashboard.application.port.out.sec_edgar_announcement_port import (
    SecEdgarAnnouncementPort,
)
from app.domains.dashboard.application.port.out.stock_bars_port import StockBarsPort
from app.domains.dashboard.application.port.out.yfinance_corporate_event_port import (
    YahooFinanceCorporateEventPort,
)
from app.domains.dashboard.application.response.announcement_response import AnnouncementsResponse
from app.domains.dashboard.application.response.corporate_event_response import CorporateEventsResponse
from app.domains.dashboard.application.response.price_event_response import PriceEventsResponse
from app.domains.dashboard.application.usecase.get_announcements_usecase import (
    GetAnnouncementsUseCase,
)
from app.domains.dashboard.application.usecase.get_corporate_events_usecase import (
    GetCorporateEventsUseCase,
)
from app.domains.dashboard.application.usecase.get_price_events_usecase import GetPriceEventsUseCase
from app.domains.history_agent.application.port.out.event_enrichment_repository_port import (
    EventEnrichmentRepositoryPort,
)
from app.domains.history_agent.application.response.timeline_response import (
    HypothesisResult,
    TimelineEvent,
    TimelineResponse,
)
from app.domains.history_agent.domain.entity.event_enrichment import (
    EventEnrichment,
    compute_detail_hash,
)
from app.infrastructure.langgraph.llm_factory import get_workflow_llm

logger = logging.getLogger(__name__)

_CACHE_TTL = 3600

# ── 인과관계 자동 호출 기준 ─────────────────────────────────────
_CAUSALITY_TRIGGER_TYPES = {"SURGE", "PLUNGE"}
_MAX_CAUSALITY_EVENTS = 3
_CAUSALITY_PRE_DAYS = 14
_CAUSALITY_POST_DAYS = 3

# ── 표시 제외 이벤트 타입 ────────────────────────────────────────
_EXCLUDED_PRICE_TYPES = {"HIGH_52W"}

# value 필드가 변화율(%)인 PRICE 타입 — change_pct 세팅용
_PCT_VALUE_TYPES = {"SURGE", "PLUNGE", "GAP_UP", "GAP_DOWN"}

# ── 타이틀 생성 ─────────────────────────────────────────────────
_TITLE_MODEL = "gpt-5-mini"
_TITLE_BATCH = 15
_TITLE_CONCURRENCY = 10

# PRICE 이벤트 중 LLM 타이틀을 생성할 상위 건수 (중요도 내림차순).
# 나머지는 rule-based 타이틀로 즉시 대체되어 응답 시간을 단축한다.
_PRICE_LLM_TOP_N = 50

# PRICE: 원인 기반 타이틀
_PRICE_TITLE_SYSTEM = """\
당신은 주식 시장 분석가입니다.
각 가격 이벤트에 대해, 그 이벤트가 발생한 원인을 한 구절로 요약한 타이틀을 생성하십시오.

규칙:
- 타이틀은 15자 이내의 한국어
- 단순 현상 설명이 아닌 원인·배경을 담는다
- 인과 가설이 제공되면 반드시 활용한다
- JSON 배열로만 응답: ["타이틀1", "타이틀2", ...]
- 이벤트 순서와 배열 순서를 반드시 일치시킨다

예시:
- "연준 금리 동결 기대감"
- "실적 쇼크 우려"
- "AI 수혜 기대감으로 갭 상승"
- "기관 대량 매도세"
- "거시 불확실성 고조"
"""

# CORPORATE / ANNOUNCEMENT: 이벤트 설명 타이틀
_OTHER_TITLE_SYSTEM = """\
당신은 주식 투자 이벤트 편집자입니다.
각 이벤트의 type / detail 을 읽고, 그 이벤트를 가장 잘 표현하는 짧은 한국어 타이틀을 생성하십시오.

규칙:
- 타이틀은 12자 이내
- JSON 배열로만 응답: ["타이틀1", "타이틀2", ...]
- 이벤트 순서와 배열 순서를 반드시 일치시킨다
"""

_FALLBACK_TITLE: dict[str, str] = {
    "LOW_52W": "52주 신저가",
    "SURGE": "급등",
    "PLUNGE": "급락",
    "GAP_UP": "갭 상승",
    "GAP_DOWN": "갭 하락",
    "EARNINGS": "실적 발표",
    "DIVIDEND": "배당",
    "EX_DIVIDEND": "배당락",
    "STOCK_SPLIT": "주식 분할",
    "RIGHTS_OFFERING": "유상증자",
    "BUYBACK": "자사주 취득",
    "BUYBACK_CANCEL": "자사주 소각",
    "MANAGEMENT_CHANGE": "임원 변동",
    "DISCLOSURE": "공시",
    "MERGER_ACQUISITION": "합병·인수",
    "CONTRACT": "계약 체결",
    "MAJOR_EVENT": "주요 공시",
}


_ANNOUNCEMENT_SUMMARY_SYSTEM = """\
당신은 SEC 공시 요약 전문가입니다.
8-K 공시 원문을 읽고 핵심 내용을 한국어 2~3문장으로 요약하십시오.

규칙:
- 회사명, 날짜, 금액, 거래 내용 등 핵심 정보를 포함한다
- 투자자가 이해할 수 있는 평이한 한국어를 사용한다
- 요약문만 출력한다. 다른 설명은 추가하지 않는다
"""


def _is_english_text(text: str) -> bool:
    """ASCII 알파벳 비율이 60% 이상이면 영문 원문으로 판단한다."""
    if len(text) < 30:
        return False
    ascii_count = sum(1 for c in text if c.isascii() and c.isalpha())
    return ascii_count / len(text) > 0.6


async def _summarize_to_korean(detail: str) -> str:
    """영문 8-K 본문을 한국어 2~3문장으로 요약한다. 실패 시 원문 반환."""
    try:
        llm = get_workflow_llm(model=_TITLE_MODEL)
        response = await llm.ainvoke([
            SystemMessage(content=_ANNOUNCEMENT_SUMMARY_SYSTEM),
            HumanMessage(content=detail),
        ])
        return response.content.strip()
    except Exception as exc:
        logger.warning("[HistoryAgent] 공시 요약 실패: %s", exc)
        return detail


async def _enrich_announcement_details(timeline: List[TimelineEvent]) -> None:
    """ANNOUNCEMENT 이벤트의 영문 detail을 한국어 요약으로 교체한다."""
    targets = [
        e for e in timeline
        if e.category == "ANNOUNCEMENT" and _is_english_text(e.detail)
    ]
    if not targets:
        return

    logger.info("[HistoryAgent] ✦ 공시 한국어 요약 시작: %d건", len(targets))
    summaries = await asyncio.gather(
        *[_summarize_to_korean(e.detail) for e in targets],
        return_exceptions=True,
    )

    for event, summary in zip(targets, summaries):
        if isinstance(summary, Exception):
            logger.warning("[HistoryAgent] 공시 요약 gather 예외: %s", summary)
            continue
        event.detail = summary
    logger.info("[HistoryAgent] ✦ 공시 한국어 요약 완료")


def _hypothesis_summary(event: TimelineEvent) -> str:
    """인과 가설이 있으면 첫 번째 가설의 핵심 원인 부분을 반환한다."""
    if not event.causality:
        return "(없음)"
    text = event.causality[0].hypothesis
    # "→" 앞부분(원인)만 추출, 없으면 전체 80자
    cause = text.split("→")[0].strip() if "→" in text else text[:80]
    return cause


async def _batch_titles(
    events: List[TimelineEvent],
    system_prompt: str,
    build_line: callable,
) -> List[str]:
    """배치 단위 LLM 호출을 병렬 실행해 타이틀 목록을 반환한다. 실패 시 fallback."""
    if not events:
        return []

    fallbacks = [_FALLBACK_TITLE.get(e.type, e.type) for e in events]
    llm = get_workflow_llm(model=_TITLE_MODEL)
    semaphore = asyncio.Semaphore(_TITLE_CONCURRENCY)

    async def _run_batch(start: int, batch: List[TimelineEvent]) -> List[str]:
        lines = "\n".join(
            f"{j + 1}. {build_line(e)}" for j, e in enumerate(batch)
        )
        async with semaphore:
            try:
                response = await llm.ainvoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=lines),
                ])
                parsed = json.loads(response.content.strip())
                if isinstance(parsed, list) and len(parsed) == len(batch):
                    return [str(t) for t in parsed]
            except Exception as exc:
                logger.warning("[HistoryAgent] 타이틀 배치 생성 실패: %s", exc)
        return fallbacks[start: start + len(batch)]

    tasks = [
        _run_batch(i, events[i: i + _TITLE_BATCH])
        for i in range(0, len(events), _TITLE_BATCH)
    ]
    results = await asyncio.gather(*tasks)
    titles: List[str] = []
    for sub in results:
        titles.extend(sub)
    return titles


def _is_fallback_title(event: TimelineEvent) -> bool:
    fallback = _FALLBACK_TITLE.get(event.type, event.type)
    return event.title == fallback


def _price_importance(e: TimelineEvent) -> float:
    """PRICE 이벤트의 LLM 타이틀 우선순위 점수. 높을수록 먼저 LLM 처리."""
    score = abs(e.change_pct or 0.0)
    if e.causality:
        score += 100
    if e.type in {"SURGE", "PLUNGE"}:
        score += 50
    if e.type == "LOW_52W":
        score += 30
    if e.type in {"GAP_UP", "GAP_DOWN"}:
        score += 5
    return score


def _rule_based_price_title(e: TimelineEvent) -> str:
    """LLM 없이 생성하는 타이틀. 변화율이 있으면 '급등 (+5.2%)' 형태, 없으면 기본 라벨."""
    kind = _FALLBACK_TITLE.get(e.type, e.type)
    if e.change_pct is not None:
        sign = "+" if e.change_pct >= 0 else ""
        return f"{kind} ({sign}{e.change_pct:.1f}%)"
    return kind


async def _enrich_price_titles(timeline: List[TimelineEvent]) -> None:
    """PRICE 이벤트 타이틀 생성. 중요도 상위 _PRICE_LLM_TOP_N 건만 LLM, 나머지는 rule-based."""
    candidates = [e for e in timeline if e.category == "PRICE" and _is_fallback_title(e)]
    if not candidates:
        return

    candidates.sort(key=_price_importance, reverse=True)
    llm_targets = candidates[:_PRICE_LLM_TOP_N]
    rule_targets = candidates[_PRICE_LLM_TOP_N:]

    logger.info(
        "[HistoryAgent] ✦ PRICE 타이틀: LLM=%d, rule-based=%d (total=%d, cutoff=top %d)",
        len(llm_targets), len(rule_targets), len(candidates), _PRICE_LLM_TOP_N,
    )

    for e in rule_targets:
        e.title = _rule_based_price_title(e)

    if not llm_targets:
        return

    def build_line(e: TimelineEvent) -> str:
        return f"type={e.type} detail={e.detail} | 인과가설: {_hypothesis_summary(e)}"

    titles = await _batch_titles(llm_targets, _PRICE_TITLE_SYSTEM, build_line)
    for event, title in zip(llm_targets, titles):
        event.title = title
    logger.info("[HistoryAgent] ✦ PRICE 타이틀 생성 완료 (LLM=%d)", len(llm_targets))


async def _enrich_other_titles(timeline: List[TimelineEvent]) -> None:
    """CORPORATE / ANNOUNCEMENT 이벤트 타이틀을 생성한다."""
    other_events = [e for e in timeline if e.category != "PRICE" and _is_fallback_title(e)]
    if not other_events:
        return

    logger.info("[HistoryAgent] ✦ CORPORATE/ANNOUNCEMENT 타이틀 생성 시작: %d건", len(other_events))

    def build_line(e: TimelineEvent) -> str:
        return f"type={e.type} detail={e.detail}"

    titles = await _batch_titles(other_events, _OTHER_TITLE_SYSTEM, build_line)
    for event, title in zip(other_events, titles):
        event.title = title
    logger.info("[HistoryAgent] ✦ CORPORATE/ANNOUNCEMENT 타이틀 생성 완료")


def _from_price_events(result: PriceEventsResponse) -> List[TimelineEvent]:
    return [
        TimelineEvent(
            title=_FALLBACK_TITLE.get(e.type, e.type),
            date=e.date,
            category="PRICE",
            type=e.type,
            detail=e.detail,
            source=None,
            url=None,
            change_pct=e.value if e.type in _PCT_VALUE_TYPES else None,
        )
        for e in result.events
        if e.type not in _EXCLUDED_PRICE_TYPES   # HIGH_52W 제외
    ]


def _from_corporate_events(result: CorporateEventsResponse) -> List[TimelineEvent]:
    return [
        TimelineEvent(
            title=_FALLBACK_TITLE.get(e.type, e.type),
            date=e.date,
            category="CORPORATE",
            type=e.type,
            detail=e.detail,
            source=e.source,
            url=None,
        )
        for e in result.events
    ]


def _from_announcements(result: AnnouncementsResponse) -> List[TimelineEvent]:
    return [
        TimelineEvent(
            title=_FALLBACK_TITLE.get(e.type, e.type),
            date=e.date,
            category="ANNOUNCEMENT",
            type=e.type,
            detail=e.title,
            source=e.source,
            url=e.url,
        )
        for e in result.events
    ]


async def _run_causality(ticker: str, event: TimelineEvent) -> List[HypothesisResult]:
    from app.domains.causality_agent.application.causality_agent_workflow import run_causality_agent

    start_date = event.date - timedelta(days=_CAUSALITY_PRE_DAYS)
    end_date = event.date + timedelta(days=_CAUSALITY_POST_DAYS)
    try:
        state = await run_causality_agent(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
        )
        return [HypothesisResult(**h) for h in state.get("hypotheses", [])]
    except Exception as exc:
        logger.warning(
            "[HistoryAgent] causality 분석 실패: ticker=%s, date=%s, type=%s, error=%s",
            ticker, event.date, event.type, exc,
        )
        return []


async def _enrich_causality(ticker: str, timeline: List[TimelineEvent]) -> None:
    targets = [
        e for e in timeline
        if e.category == "PRICE"
        and e.type in _CAUSALITY_TRIGGER_TYPES
        and e.causality is None
    ][:_MAX_CAUSALITY_EVENTS]

    if not targets:
        logger.info("[HistoryAgent] ✦ 인과관계 분석 대상 없음 (SURGE/PLUNGE 이벤트 없음)")
        return

    logger.info(
        "[HistoryAgent] ✦ 인과관계 분석 시작: %d건 %s",
        len(targets),
        [(e.type, str(e.date)) for e in targets],
    )
    results = await asyncio.gather(
        *[_run_causality(ticker, e) for e in targets],
        return_exceptions=True,
    )

    success = 0
    for event, result in zip(targets, results):
        if isinstance(result, Exception):
            logger.warning("[HistoryAgent] causality gather 예외: %s", result)
            continue
        if result:
            event.causality = result
            success += 1
    logger.info("[HistoryAgent] ✦ 인과관계 분석 완료: %d/%d 성공", success, len(targets))


class HistoryAgentUseCase:

    def __init__(
        self,
        stock_bars_port: StockBarsPort,
        yfinance_corporate_port: YahooFinanceCorporateEventPort,
        dart_corporate_client: DartCorporateEventClient,
        sec_edgar_port: SecEdgarAnnouncementPort,
        dart_announcement_client: DartAnnouncementClient,
        redis: aioredis.Redis,
        enrichment_repo: EventEnrichmentRepositoryPort,
        asset_type_port: AssetTypePort,
    ):
        self._stock_bars_port = stock_bars_port
        self._yfinance_corporate_port = yfinance_corporate_port
        self._dart_corporate_client = dart_corporate_client
        self._sec_edgar_port = sec_edgar_port
        self._dart_announcement_client = dart_announcement_client
        self._redis = redis
        self._enrichment_repo = enrichment_repo
        self._asset_type_port = asset_type_port

    async def execute(
        self,
        ticker: str,
        period: str,
        corp_code: Optional[str] = None,
        on_progress: Optional[Callable[[str, str, int], Awaitable[None]]] = None,
    ) -> TimelineResponse:
        async def _notify(step: str, label: str, pct: int) -> None:
            if on_progress:
                try:
                    await on_progress(step, label, pct)
                except Exception:
                    pass

        cache_key = f"history_agent:{ticker}:{period}"

        cached = await self._redis.get(cache_key)
        if cached:
            try:
                logger.info("[HistoryAgent] 캐시 히트: ticker=%s, period=%s", ticker, period)
                return TimelineResponse.model_validate_json(cached)
            except Exception:
                pass

        logger.info("[HistoryAgent] ══════════════════════════════════════")
        logger.info("[HistoryAgent] 시작: ticker=%s, period=%s", ticker, period)
        logger.info("[HistoryAgent] ══════════════════════════════════════")

        is_etf = await self._asset_type_port.is_etf(ticker)
        if is_etf:
            logger.info("[HistoryAgent] ETF 감지: 타임라인 수집 전체 생략 (ticker=%s)", ticker)
            await _notify("done", "ETF는 타임라인 미제공", 100)
            response = TimelineResponse(
                ticker=ticker,
                period=period,
                count=0,
                events=[],
                is_etf=True,
            )
            await self._redis.setex(cache_key, _CACHE_TTL, response.model_dump_json())
            return response

        price_uc = GetPriceEventsUseCase(stock_bars_port=self._stock_bars_port)
        corporate_uc = GetCorporateEventsUseCase(
            yfinance_port=self._yfinance_corporate_port,
            dart_client=self._dart_corporate_client,
        )
        announcement_uc = GetAnnouncementsUseCase(
            sec_edgar_port=self._sec_edgar_port,
            dart_client=self._dart_announcement_client,
        )

        logger.info("[HistoryAgent] [1/4] 데이터 수집 시작 (가격/기업이벤트/공시 병렬)")
        await _notify("data_fetch", "데이터 수집 중...", 10)
        price_result, corporate_result, announcement_result = await asyncio.gather(
            price_uc.execute(ticker=ticker, period=period),
            corporate_uc.execute(ticker=ticker, period=period, corp_code=corp_code),
            announcement_uc.execute(ticker=ticker, period=period, corp_code=corp_code),
            return_exceptions=True,
        )

        timeline: List[TimelineEvent] = []

        if isinstance(price_result, PriceEventsResponse):
            events = _from_price_events(price_result)
            timeline.extend(events)
            logger.info("[HistoryAgent]   └ 가격 이벤트: %d건", len(events))
        else:
            logger.warning("[HistoryAgent]   └ 가격 이벤트 수집 실패: %s", price_result)

        if isinstance(corporate_result, CorporateEventsResponse):
            events = _from_corporate_events(corporate_result)
            timeline.extend(events)
            logger.info("[HistoryAgent]   └ 기업 이벤트: %d건", len(events))
        else:
            logger.warning("[HistoryAgent]   └ 기업 이벤트 수집 실패: %s", corporate_result)

        if isinstance(announcement_result, AnnouncementsResponse):
            events = _from_announcements(announcement_result)
            timeline.extend(events)
            logger.info("[HistoryAgent]   └ 공시: %d건", len(events))
        else:
            logger.warning("[HistoryAgent]   └ 공시 수집 실패: %s", announcement_result)

        logger.info("[HistoryAgent]   └ 타임라인 합계: %d건", len(timeline))
        timeline.sort(key=lambda e: e.date, reverse=True)

        # 1) DB에서 기존 enrichment 로드
        await _notify("enrichment_load", "캐시 데이터 확인 중...", 35)
        db_map = await self._load_enrichments(ticker, timeline)
        new_events = self._apply_enrichments(ticker, timeline, db_map)
        logger.info(
            "[HistoryAgent] [2/4] DB enrichment 조회: hit=%d, miss=%d",
            len(timeline) - len(new_events), len(new_events),
        )

        # 2) 인과관계 분석 먼저 (PRICE 타이틀이 가설을 활용해야 하므로)
        logger.info("[HistoryAgent] [3/4] 인과관계 분석 + 타이틀 생성 (신규 이벤트만)")
        await _notify("causality", "인과관계 분석 중...", 55)
        await _enrich_causality(ticker, timeline)

        # 3) 타이틀 생성 + 공시 한국어 요약 병렬
        await _notify("title_gen", "AI 타이틀 생성 중...", 75)
        await asyncio.gather(
            _enrich_price_titles(timeline),
            _enrich_other_titles(timeline),
            _enrich_announcement_details(timeline),
        )

        # 4) 신규 이벤트만 DB 저장
        await _notify("saving", "저장 중...", 90)
        await self._save_enrichments(ticker, new_events)
        logger.info("[HistoryAgent] [4/4] 캐시 저장 후 응답 반환")

        response = TimelineResponse(
            ticker=ticker,
            period=period,
            count=len(timeline),
            events=timeline,
        )
        await self._redis.setex(cache_key, _CACHE_TTL, response.model_dump_json())
        logger.info("[HistoryAgent] 완료: ticker=%s, period=%s, total=%d", ticker, period, len(timeline))
        return response

    async def _load_enrichments(
        self, ticker: str, timeline: List[TimelineEvent]
    ) -> Dict[Tuple, "EventEnrichment"]:
        keys = [(ticker, e.date, e.type, compute_detail_hash(e.detail)) for e in timeline]
        enrichments = await self._enrichment_repo.find_by_keys(keys)
        return {(e.ticker, e.event_date, e.event_type, e.detail_hash): e for e in enrichments}

    def _apply_enrichments(
        self,
        ticker: str,
        timeline: List[TimelineEvent],
        db_map: Dict,
    ) -> List[TimelineEvent]:
        new_events = []
        for event in timeline:
            key = (ticker, event.date, event.type, compute_detail_hash(event.detail))
            enrichment = db_map.get(key)
            if enrichment:
                event.title = enrichment.title
                if enrichment.causality:
                    event.causality = [HypothesisResult(**h) for h in enrichment.causality]
            else:
                new_events.append(event)
        return new_events

    async def _save_enrichments(self, ticker: str, events: List[TimelineEvent]) -> None:
        if not events:
            return
        enrichments = [
            EventEnrichment(
                ticker=ticker,
                event_date=e.date,
                event_type=e.type,
                detail_hash=compute_detail_hash(e.detail),
                title=e.title,
                causality=(
                    [h.model_dump() for h in e.causality] if e.causality else None
                ),
            )
            for e in events
        ]
        saved = await self._enrichment_repo.upsert_bulk(enrichments)
        logger.info("[HistoryAgent] DB enrichment 저장: %d건", saved)
