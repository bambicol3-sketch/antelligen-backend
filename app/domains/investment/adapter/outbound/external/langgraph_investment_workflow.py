"""
LangGraph 기반 투자 판단 멀티 에이전트 워크플로우.

흐름:
    START
      └→ orchestrator ──────────────────────────────────────────────────┐
              ↑           (conditional routing by next_agent)            │
              │      ┌── "retrieval"  → retrieval_agent                  │
              └──────┤── "analysis"   → analysis_agent                   │
                     ├── "synthesis"  → synthesis_agent                  │
                     └── "end"        → END ←──────────────────────────  ┘

Orchestrator 동작 순서:
  1) 첫 호출 시 QueryParser로 사용자 질문을 파싱하여 parsed_query를 State에 기록한다.
  2) State 상태에 따라 다음 에이전트를 동적으로 결정한다.
  3) 최대 반복 횟수(max_iterations)를 초과하면 강제 종료한다.

SOURCE_REGISTRY:
  investment_source_registry.py 에 등록된 키만 실제 호출한다.
  미구현 소스는 조용히 무시하며 확장 포인트 주석으로 표시한다.
"""

import asyncio
import traceback
from datetime import datetime, timezone
from typing import Any, Optional, TypedDict
from urllib.parse import parse_qs, urlparse

import json

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.investment.adapter.outbound.external.investment_source_registry import (
    IMPLEMENTED_SOURCE_KEYS,
)
from app.domains.investment.adapter.outbound.external.llm_query_parser import LLMQueryParser
from app.domains.investment.adapter.outbound.persistence.investment_youtube_repository import (
    InvestmentYoutubeRepository,
)
from app.domains.investment.application.port.investment_workflow_port import InvestmentWorkflowPort
from app.domains.investment.domain.value_object.parsed_query import ParsedQuery
from app.domains.market_video.adapter.outbound.external.youtube_comment_client import YoutubeCommentClient
from app.domains.market_video.adapter.outbound.external.youtube_search_client import YoutubeSearchClient
from app.domains.news.adapter.outbound.external.investment_news_collector import InvestmentNewsCollector
from app.domains.news.adapter.outbound.persistence.investment_news_repository import InvestmentNewsRepository

MAX_ITERATIONS = 10

# 영상당 최대 수집 댓글 수 / 댓글을 수집할 최대 영상 수
_MAX_COMMENTS_PER_VIDEO = 5
_MAX_VIDEOS_FOR_COMMENTS = 3


# ──────────────────────────────────────────────
# 공유 State 정의
# ──────────────────────────────────────────────

class InvestmentAgentState(TypedDict, total=False):
    user_id: str
    user_query: str

    # Query Parser 결과 (Orchestrator 첫 호출 시 기록)
    parsed_query: Optional[ParsedQuery]

    # Orchestrator 제어
    next_agent: str       # "retrieval" | "analysis" | "synthesis" | "end"
    iteration_count: int
    max_iterations: int

    # 각 에이전트 결과
    retrieved_data: list[dict[str, Any]]   # Retrieval Agent 결과
    analysis_insights: dict[str, Any]      # Analysis Agent 결과
    final_response: str                    # Synthesis Agent 최종 응답


# ──────────────────────────────────────────────
# 헬퍼 함수
# ──────────────────────────────────────────────

def _parse_youtube_datetime(dt_str: str) -> datetime | None:
    """YouTube API published_at 문자열('2024-01-15T12:34:56Z')을 timezone-aware datetime으로 변환한다."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return datetime.now(tz=timezone.utc)


def _extract_video_id(video_url: str) -> str | None:
    """YouTube URL에서 video_id를 추출한다. 파싱 실패 시 None 반환."""
    try:
        params = parse_qs(urlparse(video_url).query)
        ids = params.get("v", [])
        return ids[0] if ids else None
    except Exception:
        return None


# ──────────────────────────────────────────────
# 워크플로우 클래스 (노드는 인스턴스 메서드)
# ──────────────────────────────────────────────

class LangGraphInvestmentWorkflow(InvestmentWorkflowPort):
    """LangGraph 기반 투자 판단 워크플로우 Port 구현체."""

    def __init__(
        self,
        *,
        api_key: str,
        serp_api_key: str = "",
        youtube_api_key: str = "",
        db_session: Optional[AsyncSession] = None,
        query_parser_model: str = "gpt-5-mini",
        max_iterations: int = MAX_ITERATIONS,
    ) -> None:
        self._query_parser = LLMQueryParser(api_key=api_key, model=query_parser_model)
        self._max_iterations = max_iterations
        self._news_collector = InvestmentNewsCollector(serp_api_key=serp_api_key) if serp_api_key else None
        self._youtube_client = YoutubeSearchClient(api_key=youtube_api_key) if youtube_api_key else None
        self._youtube_comment_client = YoutubeCommentClient(api_key=youtube_api_key) if youtube_api_key else None
        self._db_session = db_session
        self._llm = ChatOpenAI(api_key=api_key, model=query_parser_model, temperature=0.3)
        self._graph = self._build_graph()
        print(
            f"[LangGraphInvestmentWorkflow] 그래프 빌드 완료 | max_iterations={max_iterations} | "
            f"뉴스수집={'활성' if self._news_collector else '비활성'} | "
            f"youtube={'활성' if self._youtube_client else '비활성'} | "
            f"db={'연결됨' if self._db_session else '미연결'}"
        )

    # ── 단일 진입점 ───────────────────────────

    async def run(self, *, user_id: str, query: str) -> dict:
        """워크플로우를 실행하고 최종 State를 반환한다."""
        print(f"\n[LangGraphInvestmentWorkflow] run_agent_workflow 진입 "
              f"| user_id={user_id} | query={query!r}")

        initial_state: InvestmentAgentState = {
            "user_id": user_id,
            "user_query": query,
            "iteration_count": 0,
            "max_iterations": self._max_iterations,
        }

        final_state = await self._graph.ainvoke(initial_state)

        print(f"\n[LangGraphInvestmentWorkflow] 워크플로우 종료 "
              f"| total_iterations={final_state.get('iteration_count', 0)}")
        return final_state

    # ── 그래프 빌드 ───────────────────────────

    def _build_graph(self):
        graph = StateGraph(InvestmentAgentState)

        graph.add_node("orchestrator", self._orchestrator_node)
        graph.add_node("retrieval", self._retrieval_node)
        graph.add_node("analysis", self._analysis_node)
        graph.add_node("synthesis", self._synthesis_node)

        graph.add_edge(START, "orchestrator")

        graph.add_conditional_edges(
            "orchestrator",
            self._route_from_orchestrator,
            {
                "retrieval": "retrieval",
                "analysis": "analysis",
                "synthesis": "synthesis",
                "end": END,
            },
        )

        graph.add_edge("retrieval", "orchestrator")
        graph.add_edge("analysis", "orchestrator")
        graph.add_edge("synthesis", "orchestrator")

        return graph.compile()

    # ── 라우팅 함수 ───────────────────────────

    def _route_from_orchestrator(self, state: InvestmentAgentState) -> str:
        next_agent = state.get("next_agent", "end")
        print(f"[Router] 조건부 엣지 → {next_agent}")
        return next_agent

    # ── 노드 구현 ─────────────────────────────

    async def _orchestrator_node(self, state: InvestmentAgentState) -> InvestmentAgentState:
        """
        현재 State를 기반으로 다음 실행 Agent를 결정한다.

        첫 호출 시 QueryParser로 질문을 파싱한다.
        이후 State 완성도에 따라 retrieval → analysis → synthesis → end 순으로 라우팅한다.
        """
        iteration = state.get("iteration_count", 0) + 1
        max_iter = state.get("max_iterations", MAX_ITERATIONS)

        print(f"\n[Orchestrator] ===== 반복 #{iteration} / 최대 {max_iter} =====")
        print(f"[Orchestrator] 사용자 질의: {state.get('user_query')!r}")
        print(
            f"[Orchestrator] 현재 State 요약 → "
            f"parsed_query={'있음' if state.get('parsed_query') else '없음'} | "
            f"retrieved_data={'있음' if state.get('retrieved_data') else '없음'} | "
            f"analysis_insights={'있음' if state.get('analysis_insights') else '없음'} | "
            f"final_response={'있음' if state.get('final_response') else '없음'}"
        )

        updates: InvestmentAgentState = {"iteration_count": iteration}

        # 최대 반복 초과 → 강제 종료
        if iteration > max_iter:
            print(f"[Orchestrator] 최대 반복 횟수 초과 → 워크플로우 강제 종료")
            updates["next_agent"] = "end"
            return updates

        # 첫 호출: Query Parser로 질문 파싱 후 State에 기록
        if not state.get("parsed_query"):
            print(f"[Orchestrator] Query Parser 호출 중...")
            parsed = await self._query_parser.parse(state.get("user_query", ""))
            updates["parsed_query"] = parsed
            print(
                f"[Orchestrator] 파싱 결과 State 기록 완료 → "
                f"company={parsed['company']!r} | "
                f"intent={parsed['intent']!r} | "
                f"required_data={parsed['required_data']}"
            )

        # 상태 기반 동적 라우팅 결정
        if not state.get("retrieved_data"):
            next_agent = "retrieval"
        elif not state.get("analysis_insights"):
            next_agent = "analysis"
        elif not state.get("final_response"):
            next_agent = "synthesis"
        else:
            next_agent = "end"

        print(f"[Orchestrator] 다음 실행 에이전트 → {next_agent}")
        updates["next_agent"] = next_agent
        return updates

    async def _retrieval_node(self, state: InvestmentAgentState) -> InvestmentAgentState:
        """
        required_data 배열을 읽어 호출할 데이터 소스를 결정하고 수집 결과를 State에 적재한다.

        지원 소스 (SOURCE_REGISTRY 참조):
          - "뉴스"   → SERP API Google News 검색
          - "유튜브" → YouTube Data API v3 검색 + 댓글 수집 + DB 저장
        그 외 항목은 무시하며 향후 분기를 추가할 수 있다.

        부분 실패 허용: 특정 소스 호출이 실패해도 나머지 소스는 정상 수집을 계속한다.
        """
        parsed: ParsedQuery = state.get("parsed_query") or {}
        company = parsed.get("company") or "전체 시장"
        required_data = parsed.get("required_data", [])
        user_id = state.get("user_id", "unknown")

        print(f"\n[RetrievalAgent] 데이터 수집 시작 | company={company!r} | required_data={required_data}")

        need_news = "뉴스" in required_data
        need_youtube = "유튜브" in required_data
        ignored = [d for d in required_data if d not in IMPLEMENTED_SOURCE_KEYS]

        print(
            f"[RetrievalAgent] 소스 라우팅 → 뉴스={need_news} | 유튜브={need_youtube}"
            + (f" | 무시됨={ignored}" if ignored else "")
        )

        # ── 비동기 병렬 수집 ─────────────────────────────────────────────────
        tasks: dict[str, Any] = {}

        if need_news:
            tasks["뉴스"] = self._fetch_news(company)
        if need_youtube:
            tasks["유튜브"] = self._fetch_youtube(company)

        # 확장 포인트: 추가 소스는 여기에 elif 분기로 연결한다
        # if "종목" in required_data:
        #     tasks["종목"] = self._fetch_stock(company)

        if not tasks:
            print(f"[RetrievalAgent] 처리 가능한 데이터 소스가 없습니다. 빈 데이터로 진행합니다.")
            return {"retrieved_data": []}

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        # ── 결과 병합 (부분 실패 허용) ───────────────────────────────────────
        retrieved_data: list[dict[str, Any]] = []
        source_statuses: dict[str, str] = {}

        youtube_videos: list[dict] = []

        for source_name, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                print(f"[RetrievalAgent] [{source_name}] 수집 실패 (부분 실패 허용): {result}")
                traceback.print_exc()
                source_statuses[source_name] = f"error: {result}"
                retrieved_data.append({
                    "source": source_name,
                    "status": "error",
                    "error": str(result),
                    "items": [],
                })
            else:
                print(f"[RetrievalAgent] [{source_name}] 수집 성공 | 항목 수: {len(result)}")
                source_statuses[source_name] = "ok"
                retrieved_data.append({
                    "source": source_name,
                    "status": "ok",
                    "items": result,
                })
                if source_name == "유튜브":
                    youtube_videos = result

        print(f"[RetrievalAgent] 전체 수집 완료 | 총 소스 수: {len(retrieved_data)}")

        # ── DB 저장 ───────────────────────────────────────────────────────────
        if self._db_session:
            news_items = next(
                (r["items"] for r in retrieved_data if r["source"] == "뉴스" and r["status"] == "ok"),
                [],
            )
            await self._persist_collected_data(
                user_id=user_id,
                company=parsed.get("company"),
                intent=parsed.get("intent", "기타"),
                required_data=required_data,
                source_statuses=source_statuses,
                youtube_videos=youtube_videos,
                news_articles=news_items,
            )

        return {"retrieved_data": retrieved_data}

    # ── 개별 소스 수집 헬퍼 ──────────────────────────────────────────────────

    async def _fetch_news(self, company: str) -> list[dict[str, Any]]:
        """
        InvestmentNewsCollector를 통해 뉴스 검색 + 본문 수집을 수행한다.

        company가 "전체 시장"이면 Collector 기본 키워드(방산 방위산업 한국 주식)를 사용한다.
        반환 항목마다 summary_text가 포함되어 Retrieval Agent 적재에 바로 사용된다.
        """
        if not self._news_collector:
            print(f"[RetrievalAgent] [뉴스] SERP API 키 미설정 — 빈 결과 반환")
            return []

        target = company if company != "전체 시장" else None
        print(f"[RetrievalAgent] [뉴스] 수집 시작 | company={target!r}")

        items = await self._news_collector.collect(company=target)
        print(f"[RetrievalAgent] [뉴스] 기사 {len(items)}건 수집 완료")
        return items

    async def _fetch_youtube(self, company: str) -> list[dict[str, Any]]:
        """
        YouTube Data API v3로 관련 영상을 수집하고 상위 영상의 댓글을 추가로 수집한다.

        published_at은 원본 문자열과 파싱된 datetime 객체를 함께 반환한다.
        """
        if not self._youtube_client:
            print(f"[RetrievalAgent] [유튜브] YouTube API 키 미설정 — 빈 결과 반환")
            return []

        keyword = f"{company} 주식" if company != "전체 시장" else None
        print(f"[RetrievalAgent] [유튜브] 영상 검색 중 | keyword={keyword!r}")

        videos, _, _, total = await self._youtube_client.search(keyword=keyword)

        items: list[dict[str, Any]] = []
        for i, video in enumerate(videos):
            video_id = _extract_video_id(video.video_url)
            published_at_dt = _parse_youtube_datetime(video.published_at)

            comments: list = []
            if self._youtube_comment_client and video_id and i < _MAX_VIDEOS_FOR_COMMENTS:
                print(f"[RetrievalAgent] [유튜브] 댓글 수집 중 | video_id={video_id}")
                try:
                    comments = await self._youtube_comment_client.fetch_comments(
                        video_id=video_id,
                        max_count=_MAX_COMMENTS_PER_VIDEO,
                    )
                    print(f"[RetrievalAgent] [유튜브] 댓글 {len(comments)}건 수집 | video_id={video_id}")
                except Exception as e:
                    print(f"[RetrievalAgent] [유튜브] 댓글 수집 실패 (무시) | video_id={video_id} | {e}")
                    comments = []

            items.append({
                "title": video.title,
                "channel_name": video.channel_name,
                "published_at": video.published_at,       # 원본 문자열
                "published_at_dt": published_at_dt,       # DB 저장용 datetime
                "video_url": video.video_url,
                "thumbnail_url": video.thumbnail_url,
                "video_id": video_id,
                "comments": comments,
            })

        print(f"[RetrievalAgent] [유튜브] 영상 {len(items)}건 수집 완료 (전체 검색결과: {total}건)")
        return items

    # ── DB 영속화 ────────────────────────────────────────────────────────────

    async def _persist_collected_data(
        self,
        *,
        user_id: str,
        company: str | None,
        intent: str,
        required_data: list[str],
        source_statuses: dict[str, str],
        youtube_videos: list[dict],
        news_articles: list[dict],
    ) -> None:
        """
        수집 결과를 네 테이블에 저장한다 (모두 PostgreSQL).

          1. investment_youtube_logs           — 워크플로우 실행 로그
          2. investment_youtube_videos         — YouTube 영상 메타데이터
          3. investment_youtube_video_comments — 영상별 댓글
          4. investment_news_contents          — SERP 뉴스 원문 (JSONB)

        예외 발생 시 traceback을 출력하고 워크플로우는 계속 진행한다 (부분 실패 허용).
        """
        print(
            f"\n[RetrievalAgent] [DB] 저장 시작 "
            f"| 영상={len(youtube_videos)}건 | 뉴스={len(news_articles)}건"
        )
        repo = InvestmentYoutubeRepository(self._db_session)

        try:
            # 1. 실행 로그 저장
            log_id = await repo.save_log(
                user_id=user_id,
                company=company,
                intent=intent,
                required_data=required_data,
                source_statuses=source_statuses,
            )

            # 2. YouTube 영상 저장 → (db_video_id, video_url) 목록 반환
            if youtube_videos:
                video_rows = await repo.save_videos(log_id, youtube_videos)

                # 3. 영상별 댓글 저장
                video_map = {url: db_id for db_id, url in video_rows}
                for video in youtube_videos:
                    comments = video.get("comments", [])
                    if not comments:
                        continue
                    db_video_id = video_map.get(video["video_url"])
                    if db_video_id:
                        await repo.save_comments(db_video_id, comments)

            # 4. 뉴스 메타데이터 + 본문 저장
            if news_articles:
                from app.domains.news.adapter.outbound.external.investment_news_collector import DEFAULT_KEYWORD
                keyword_used = f"{company} 주식 뉴스" if company else DEFAULT_KEYWORD
                news_repo = InvestmentNewsRepository(self._db_session)
                await news_repo.save_articles(
                    user_id=user_id,
                    company=company,
                    keyword_used=keyword_used,
                    articles=news_articles,
                )

            # 5. 커밋
            await repo.commit()
            print(f"[RetrievalAgent] [DB] 전체 저장 완료 | log_id={log_id}")

        except Exception:
            print("[RetrievalAgent] [DB] [ERROR] 데이터 저장 실패 (워크플로우 계속 진행):")
            traceback.print_exc()

    async def _analysis_node(self, state: InvestmentAgentState) -> InvestmentAgentState:
        """
        수집된 뉴스·YouTube 데이터를 LLM에 전달하여 종목 전망, 리스크, 투자 포인트를 분석한다.
        """
        parsed: ParsedQuery = state.get("parsed_query") or {}
        company = parsed.get("company") or "전체 시장"
        intent = parsed.get("intent", "기타")
        retrieved_data = state.get("retrieved_data", [])

        print(f"\n[AnalysisAgent] 분석 시작 | company={company!r} | intent={intent!r}")

        # ── 수집 데이터를 LLM 컨텍스트로 변환 ───────────────────────────────
        news_lines: list[str] = []
        youtube_lines: list[str] = []

        for source in retrieved_data:
            if source.get("status") != "ok":
                continue
            if source["source"] == "뉴스":
                for item in source["items"][:5]:
                    news_lines.append(item.get("summary_text") or item.get("title", ""))
            elif source["source"] == "유튜브":
                for item in source["items"][:5]:
                    youtube_lines.append(f"[{item.get('channel_name','')}] {item.get('title','')}")

        news_context = "\n".join(news_lines) if news_lines else "수집된 뉴스 없음"
        youtube_context = "\n".join(youtube_lines) if youtube_lines else "수집된 영상 없음"

        print(f"[AnalysisAgent] 컨텍스트 구성 | 뉴스={len(news_lines)}건 | 유튜브={len(youtube_lines)}건")

        system_prompt = """당신은 한국 주식 투자 분석 전문가입니다.
수집된 뉴스와 YouTube 영상 정보를 바탕으로 종목을 분석하세요.
반드시 아래 JSON 형식으로만 응답하세요 (마크다운, 코드블록 금지):
{
  "outlook": "종목 전망 (2~3문장, 구체적 근거 포함)",
  "risk": "주요 리스크 요인 (2~3문장)",
  "investment_points": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3"]
}"""

        user_prompt = f"""분석 대상: {company}
사용자 질문 의도: {intent}

[수집된 뉴스]
{news_context}

[수집된 YouTube 영상]
{youtube_context}"""

        response = await self._llm.ainvoke([
            ("system", system_prompt),
            ("human", user_prompt),
        ])

        raw = response.content.strip()
        print(f"[AnalysisAgent] LLM 응답 수신 | 길이={len(raw)}자")

        try:
            data = json.loads(raw)
            analysis_insights = {
                "outlook": str(data.get("outlook", "")),
                "risk": str(data.get("risk", "")),
                "investment_points": list(data.get("investment_points", [])),
            }
        except json.JSONDecodeError:
            print(f"[AnalysisAgent] JSON 파싱 실패 — 원문 텍스트로 fallback")
            analysis_insights = {
                "outlook": raw,
                "risk": "",
                "investment_points": [],
            }

        print(f"[AnalysisAgent] 분석 완료 | 전망={analysis_insights['outlook'][:50]!r}...")
        return {"analysis_insights": analysis_insights}

    async def _synthesis_node(self, state: InvestmentAgentState) -> InvestmentAgentState:
        """
        분석 인사이트를 바탕으로 사용자 질문에 대한 자연어 투자 참고 응답을 생성한다.
        """
        query = state.get("user_query", "")
        analysis_insights = state.get("analysis_insights", {})
        parsed: ParsedQuery = state.get("parsed_query") or {}
        company = parsed.get("company") or "전체 시장"
        intent = parsed.get("intent", "기타")

        print(f"\n[SynthesisAgent] 응답 종합 시작 | query={query!r} | intent={intent!r}")

        investment_points = analysis_insights.get("investment_points", [])
        points_text = "\n".join(f"  - {p}" for p in investment_points) if investment_points else "  - 없음"

        system_prompt = """당신은 친절하고 전문적인 한국 주식 투자 어드바이저입니다.
분석 결과를 바탕으로 사용자의 질문에 대해 명확하고 이해하기 쉬운 한국어로 응답하세요.

작성 규칙:
- 3~5문단 분량으로 작성
- 구체적인 근거와 수치를 포함
- 투자 권유가 아닌 정보 제공임을 자연스럽게 녹여낼 것
- 마크다운 헤더(#) 없이 일반 텍스트로 작성"""

        user_prompt = f"""사용자 질문: {query}
분석 대상: {company}
질문 의도: {intent}

[분석 결과]
전망: {analysis_insights.get('outlook', '')}
리스크: {analysis_insights.get('risk', '')}
핵심 투자 포인트:
{points_text}

위 분석을 바탕으로 사용자의 질문에 대한 투자 참고 응답을 작성하세요."""

        response = await self._llm.ainvoke([
            ("system", system_prompt),
            ("human", user_prompt),
        ])

        DISCLAIMER = (
            "\n\n※ 본 응답은 투자 권유가 아닌 정보 제공 목적으로만 활용되어야 하며, "
            "투자 판단 및 그에 따른 결과는 전적으로 투자자 본인의 책임입니다."
        )

        final_response = response.content.strip() + DISCLAIMER

        print(f"[SynthesisAgent] 응답 종합 완료 | 응답 길이: {len(final_response)}자")
        return {"final_response": final_response}
