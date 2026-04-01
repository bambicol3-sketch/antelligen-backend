# 프론트엔드 플랜 프롬프트

> 이 문서는 백엔드 메인 에이전트 구현 완료 후 프론트엔드 팀이 UI 플랜을 세우는 데 사용하는 프롬프트입니다.

---

## 배경

주식 분석 AI 서비스의 프론트엔드를 개발해야 합니다.
백엔드는 FastAPI 기반이며, 아래 두 가지 API가 완성되어 있습니다.

---

## API 스펙

### 공통 응답 래퍼

모든 API 응답은 아래 구조로 감싸집니다.

```json
{
  "success": true,
  "message": "success",
  "data": { ... }
}
```

오류 시:
```json
{
  "success": false,
  "message": "오류 설명",
  "data": null
}
```

---

### 1. POST /api/v1/agent/query — 종합 분석 실행

**요청 (Request Body)**
```json
{
  "query": "삼성전자 투자해도 될까요?",
  "ticker": "005930",
  "session_id": "optional-string"
}
```

**응답 (Response Body) — 실제 예시**
```json
{
  "success": true,
  "message": "success",
  "data": {
    "session_id": "da038933-99ff-4f56-8dd4-d2f5145d4688",
    "result_status": "success",
    "answer": "삼성전자는 AI 반도체 투자 확대와 안정적 재무 성과를 바탕으로 긍정적 전망이 우세하나, 글로벌 공급망 불확실성은 주의가 필요합니다.",
    "agent_results": [
      {
        "agent_name": "news",
        "status": "success",
        "data": {
          "ticker": "005930"
        },
        "error_message": null,
        "execution_time_ms": 0,
        "signal": "bullish",
        "confidence": 0.82,
        "summary": "삼성전자 AI 반도체 투자 확대 발표로 긍정적 전망",
        "key_points": [
          "AI 반도체 설비 투자 3조원 추가 확정",
          "HBM4 양산 일정 앞당김",
          "주요 외국계 증권사 목표가 상향"
        ]
      },
      {
        "agent_name": "disclosure",
        "status": "success",
        "data": {
          "ticker": "005930",
          "filings": {
            "core": [
              {
                "title": "사업보고서 (2025.12)",
                "filed_at": "2026-03-10",
                "type": "report"
              }
            ],
            "other_summary": {
              "ownership": 35,
              "unknown": 12,
              "major_event": 2
            }
          }
        },
        "error_message": null,
        "execution_time_ms": 7864,
        "signal": "neutral",
        "confidence": 0.75,
        "summary": "삼성전자는 2025년 사업보고서를 통해 글로벌 시장에서의 경쟁력 유지와 신사업 확장 전략을 공개하며, 안정적인 사업 기반을 바탕으로 성장 잠재력을 갖추고 있음.",
        "key_points": [
          "[2026-03-10] 2025년 사업보고서 제출",
          "[positive] R&D 투자와 신사업 확장 전략 추진 중",
          "[positive] 글로벌 전자제품 시장에서 강력한 점유율 유지"
        ]
      },
      {
        "agent_name": "finance",
        "status": "success",
        "data": {
          "ticker": "005930",
          "stock_name": "삼성전자",
          "market": "KOSPI",
          "current_price": "₩189,600.00 KRW",
          "currency": null,
          "market_cap": null,
          "pe_ratio": null,
          "dividend_yield": null,
          "roe": 10.36,
          "roa": 7.97,
          "debt_ratio": 29.94,
          "fiscal_year": "2025",
          "sales": 333605900000000.0,
          "operating_income": 43601100000000.0,
          "net_income": 45206800000000.0,
          "reference_url": null,
          "collected_at": "2026-04-01T13:37:03.156283+00:00",
          "retrieved_chunk_count": 3,
          "cache_hit": false
        },
        "error_message": null,
        "execution_time_ms": 27219,
        "signal": "bullish",
        "confidence": 0.76,
        "summary": "2025년 재무지표는 매출·이익 성장률이 높고 수익성·재무건전성도 양호해 긍정적입니다.",
        "key_points": [
          "2025년 매출 3,336,059억원(+10.9%), 영업이익 436,011억원(+33.2%), 당기순이익 452,068억원(+31.2%)",
          "ROE 10.36%, ROA 7.97%로 수익성이 양호함",
          "부채비율 29.94%로 재무건전성이 높음"
        ]
      }
    ],
    "total_execution_time_ms": 29453
  }
}
```

**`result_status` 가능한 값**
- `success` — 전체 성공
- `partial_failure` — 일부 에이전트 실패 (나머지는 정상 표시)
- `failure` — 전체 실패

**`signal` 가능한 값**
- `bullish` — 매수
- `bearish` — 매도
- `neutral` — 중립
- `null` — 데이터 없음

**응답 시간 참고**
- 뉴스 에이전트: ~0ms (현재 Mock)
- 공시 에이전트: 7~20초 (LangGraph RAG 분석)
- 재무 에이전트: 12~27초 (DART API + LLM)
- 전체: 20~30초 (3개 에이전트 병렬 실행)
- **캐시 히트 시**: ~1초 이내 (동일 종목 재요청)

**finance `data` 필드 주의사항**
- `current_price`, `market_cap`, `pe_ratio`, `dividend_yield` — KRX 종목은 현재 `null`일 수 있음
- `sales`, `operating_income`, `net_income` — 단위: 원(₩). 표시 시 억원 또는 조원으로 변환 권장
  - 예: `333605900000000` → `3,336,059억원` 또는 `333.6조원`

**disclosure `data.filings` 구조**
- `core`: 사업보고서, 분기보고서 등 핵심 공시 상세 목록 (제목, 접수일, 유형)
- `other_summary`: 기타 공시 카테고리별 건수 (`ownership`, `major_event`, `unknown` 등)

---

### 2. GET /api/v1/agent/history — 분석 이력 조회

**쿼리 파라미터**
- `ticker` (필수): 종목 코드 (예: `005930`)
- `limit` (선택): 최대 50, 기본 10

**응답 (Response Body)**
```json
{
  "success": true,
  "message": "success",
  "data": [
    {
      "ticker": "005930",
      "query": "삼성전자 투자해도 될까요?",
      "overall_signal": "bullish",
      "confidence": 0.76,
      "summary": "AI 반도체 투자 확대와 안정적 재무 성과로 긍정적 전망",
      "key_points": [
        "매출 3,336,059억원(+10.9%)",
        "부채비율 29.94%로 재무건전성 높음",
        "글로벌 공급망 불확실성 주의"
      ],
      "sub_results": [...],
      "execution_time_ms": 29453,
      "created_at": "2026-04-01T13:37:03.156283+00:00"
    }
  ]
}
```

---

## UI 구현 요청

위 API를 기반으로 다음 화면을 구현해 주세요.

### 화면 1: 종목 분석 입력 페이지
- 종목 코드 입력 필드 (예: `005930`)
- 사용자 질문 입력 텍스트 영역 (예: "삼성전자 투자해도 될까요?")
- "분석하기" 버튼
- **로딩 상태 표시**: 분석에 20~30초 소요되므로 단계별 진행 표시 권장
  - 예: "뉴스 분석 중..." → "공시 분석 중..." → "재무 분석 중..." → "종합 분석 완료"

### 화면 2: 분석 결과 페이지

**상단 — 종합 결과**
- 종목 코드 표시
- **종합 시그널 배지**: `bullish`(매수) = 초록, `neutral`(중립) = 회색, `bearish`(매도) = 빨강
- **신뢰도 게이지**: 0~100% 바 형태 (`confidence × 100`)
- **LLM 종합 요약 텍스트** (`answer` 필드)

**중단 — 에이전트별 상세 결과 카드**

각 에이전트(뉴스 / 공시 / 재무)에 대해 카드 형태로:
- 에이전트 이름 (한글: 뉴스 / 공시 / 재무)
- 시그널 배지 + 신뢰도
- 요약 텍스트 (`summary`)
- 핵심 포인트 리스트 (`key_points`)
- 처리 시간 (`execution_time_ms`)

**재무 에이전트 카드 추가 표시 항목** (`data` 필드 활용):
- 주요 재무 지표 테이블: ROE, ROA, 부채비율, 매출액, 영업이익, 당기순이익
- 매출·영업이익·순이익은 억원 단위 변환 표시 (`값 / 100000000` → 반올림)
- 현재 주가 (`current_price`) — null이면 미표시

**공시 에이전트 카드 추가 표시 항목** (`data.filings` 활용):
- 핵심 공시 목록: 제목 + 접수일
- 기타 공시 현황: 카테고리별 건수 배지

**하단 — 분석 이력**
- `GET /api/v1/agent/history?ticker=005930` 호출
- 최근 분석 이력 타임라인 표시
- 각 이력 클릭 시 상세 결과 펼치기

### 에러 처리
- `result_status: "failure"` → "분석 결과를 가져오지 못했습니다" 메시지
- `result_status: "partial_failure"` → 결과 표시 + "일부 에이전트 응답 없음" 경고 배너
- 에이전트별 `status: "error"` → 해당 카드에 "분석 실패" 표시, 나머지 카드는 정상 표시
- 네트워크 에러 → 재시도 버튼

---

## 참고 사항

- 백엔드 서버: `http://localhost:33333`
- CORS 허용: `http://localhost:3000`
- 인증: 현재 `/agent/query`, `/agent/history`는 인증 불필요
- 뉴스 에이전트는 현재 Mock 데이터로 동작 (추후 실제 데이터로 교체 예정)
- `current_price`, `market_cap` 등 일부 재무 필드는 KRX 데이터 수집 한계로 `null`일 수 있음 — null 처리 필수
- 금액 단위 변환 예시:
  - `333605900000000` (원) → `3,336,059억원` 또는 `333.6조원`
  - 표시 기준: 1조 미만은 억원, 1조 이상은 조원 권장
