# 메인 에이전트 (통합 분석 에이전트) 개발 문서

## 개요

뉴스 · 공시 · 재무 서브에이전트를 **병렬 호출**하여 종합 투자 시그널과 LLM 기반 분석 요약을 반환하는 오케스트레이터 에이전트입니다.

---

## 아키텍처 개요

```
[POST /api/v1/agent/query]
        │
        ▼
ProcessAgentQueryUseCase
        │
        ├─ PostgreSQL 캐시 확인 (1시간 이내 결과 재사용)
        │
        ├─ asyncio.gather() ──────────────────────────────────┐
        │       ├─ NewsSubAgentAdapter (뉴스, 현재 Mock)       │
        │       ├─ DisclosureSubAgentAdapter (공시)            │ 병렬
        │       └─ FinanceSubAgentAdapter (재무)               │
        │                                                     ◄┘
        ├─ 시그널 가중 집계 (bullish/bearish/neutral + confidence)
        │
        ├─ OpenAISynthesisClient → LLM 종합 요약 생성
        │
        ├─ IntegratedAnalysisRepositoryImpl.save() → PostgreSQL 저장
        │
        └─ AgentQueryResponse 반환
```

### 레이어별 파일 위치

| 레이어 | 파일 |
|--------|------|
| **Inbound Adapter** | `adapter/inbound/api/agent_router.py` |
| **UseCase** | `application/usecase/process_agent_query_usecase.py` |
| **Ports** | `application/port/news_agent_port.py` |
| | `application/port/disclosure_agent_port.py` |
| | `application/port/finance_agent_port.py` |
| | `application/port/llm_synthesis_port.py` |
| | `application/port/integrated_analysis_repository_port.py` |
| **Response DTO** | `application/response/integrated_analysis_response.py` |
| **Service** | `application/service/synthesis_prompt_builder.py` |
| **Outbound Adapters** | `adapter/outbound/external/disclosure_sub_agent_adapter.py` |
| | `adapter/outbound/external/finance_sub_agent_adapter.py` |
| | `adapter/outbound/external/news_sub_agent_adapter.py` (Mock) |
| | `adapter/outbound/external/openai_synthesis_client.py` |
| | `adapter/outbound/persistence/integrated_analysis_repository_impl.py` |
| **ORM** | `infrastructure/orm/integrated_analysis_orm.py` |

---

## 엔드포인트 스펙

### POST /api/v1/agent/query — 종합 분석 실행

**요청**
```json
{
  "query": "삼성전자 투자해도 될까요?",
  "ticker": "005930",
  "session_id": "optional-uuid"
}
```

**응답**
```json
{
  "status": "success",
  "data": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "result_status": "success",
    "answer": "삼성전자는 AI 반도체 투자 확대로 긍정적 흐름이나, 공시 기준 자기주식 처분으로 단기 수급 부담이 있습니다. 재무는 중립입니다.",
    "agent_results": [
      {
        "agent_name": "news",
        "status": "success",
        "signal": "bullish",
        "confidence": 0.82,
        "summary": "삼성전자 AI 반도체 투자 확대 발표로 긍정적 전망",
        "key_points": ["AI 반도체 설비 투자 3조원 추가 확정", "HBM4 양산 일정 앞당김"],
        "execution_time_ms": 12
      },
      {
        "agent_name": "disclosure",
        "status": "success",
        "signal": "bearish",
        "confidence": 0.71,
        "summary": "자기주식 처분 공시로 단기 수급 부담",
        "key_points": ["자기주식 500만주 처분 결정", "처분 예정 기간 3개월"],
        "execution_time_ms": 1850
      },
      {
        "agent_name": "finance",
        "status": "success",
        "signal": "neutral",
        "confidence": 0.55,
        "summary": "매출 성장세 유지되나 영업이익률 소폭 하락",
        "key_points": ["2025-Q4 매출 258조 (전년 대비 +12%)", "영업이익률 2.5% 하락"],
        "execution_time_ms": 3200
      }
    ],
    "total_execution_time_ms": 3420
  }
}
```

---

### GET /api/v1/agent/history — 분석 이력 조회

**쿼리 파라미터**
- `ticker` (필수): 종목 코드 (예: `005930`)
- `limit` (선택, 기본 10, 최대 50): 조회할 이력 개수

**응답**
```json
{
  "status": "success",
  "data": [
    {
      "ticker": "005930",
      "query": "삼성전자 투자해도 될까요?",
      "overall_signal": "neutral",
      "confidence": 0.69,
      "summary": "...",
      "key_points": ["...", "..."],
      "sub_results": [...],
      "execution_time_ms": 3420
    }
  ]
}
```

---

## DB 테이블: integrated_analysis_results

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | INTEGER (PK) | 자동 증가 |
| `ticker` | VARCHAR(20) | 종목 코드 (인덱스) |
| `query` | TEXT | 사용자 질문 |
| `overall_signal` | VARCHAR(20) | bullish / bearish / neutral |
| `confidence` | FLOAT | 0.0 ~ 1.0 |
| `summary` | TEXT | LLM 종합 요약 |
| `key_points` | JSON | 핵심 포인트 리스트 |
| `sub_results` | JSON | 서브에이전트별 결과 전체 |
| `execution_time_ms` | INTEGER | 처리 시간 (ms) |
| `created_at` | DATETIME | 생성 시각 |

### 캐시 전략

- 동일 `ticker` 재조회 시 `created_at` 기준 **1시간 이내** 결과 재사용
- 만료 시 서브에이전트 재호출 → 새 row INSERT

---

## 시그널 집계 로직

| 조건 | 결과 |
|------|------|
| 가중 평균 점수 > 0.2 | bullish |
| 가중 평균 점수 < -0.2 | bearish |
| 그 외 | neutral |

가중치 계산: `score = Σ(signal_score × confidence) / Σ(confidence)`

- bullish = +1.0, neutral = 0.0, bearish = -1.0

---

## 뉴스 에이전트 연동 방법 (팀원 완료 후)

`app/domains/agent/adapter/outbound/external/news_sub_agent_adapter.py` 에서:

1. `# TODO` 주석 제거
2. `SearchNewsUseCase` + `AnalyzeArticleUseCase` import 추가
3. `analyze()` 메서드 내 Mock 데이터 → 실제 UseCase 호출로 교체

```python
async def analyze(self, ticker: str, query: str) -> SubAgentResponse:
    # 1. 종목명으로 뉴스 검색
    news_list = await self._search_usecase.execute(SearchNewsRequest(keyword=ticker))
    # 2. 각 기사 감정 분석 후 시그널 집계
    ...
```

---

## 설정값 (settings.py)

| 설정 키 | 기본값 | 설명 |
|---------|--------|------|
| `openai_api_key` | — | LLM 종합 요약용 OpenAI 키 |
| `openai_finance_agent_model` | gpt-5-mini | 재무 에이전트 모델 |
| `openai_embedding_model` | text-embedding-3-small | 임베딩 모델 |
| `finance_rag_top_k` | 3 | RAG 검색 청크 수 |
| `finance_analysis_cache_ttl_seconds` | 3600 | 재무 분석 Redis TTL |

통합 분석 캐시 TTL은 `ProcessAgentQueryUseCase.execute()` 내 `within_seconds=3600`을 직접 수정합니다.
