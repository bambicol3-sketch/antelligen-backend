import random

from app.domains.agent.application.port.sub_agent_provider import SubAgentProvider
from app.domains.agent.application.response.investment_signal_response import (
    InvestmentSignalResponse,
)
from app.domains.agent.application.response.sub_agent_response import SubAgentResponse

MOCK_NEWS_SIGNALS: dict[str, dict] = {
    "005930": {
        "agent_name": "news", "ticker": "005930",
        "signal": "bullish", "confidence": 0.82,
        "summary": "삼성전자 AI 반도체 투자 확대 발표로 긍정적 전망",
        "key_points": [
            "AI 반도체 설비 투자 3조원 추가 확정",
            "HBM4 양산 일정 앞당김",
            "주요 외국계 증권사 목표가 상향",
        ],
    },
    "000660": {
        "agent_name": "news", "ticker": "000660",
        "signal": "bullish", "confidence": 0.78,
        "summary": "SK하이닉스 HBM4 양산 본격화로 실적 개선 기대",
        "key_points": [
            "HBM4 양산 라인 가동 시작",
            "엔비디아 공급 계약 확대",
        ],
    },
    "005380": {
        "agent_name": "news", "ticker": "005380",
        "signal": "neutral", "confidence": 0.65,
        "summary": "현대자동차 전기차 전환 속도 조절 관련 뉴스 혼재",
        "key_points": [
            "전기차 생산 목표 하향 조정",
            "하이브리드 모델 판매 호조",
        ],
    },
}

DEFAULT_TICKER = "005930"


class MockNewsAgentProvider(SubAgentProvider):
    def call(self, agent_name: str, ticker: str | None, query: str) -> SubAgentResponse:
        if agent_name != "news":
            return SubAgentResponse.error(
                agent_name,
                f"MockNewsAgentProvider는 'news' 에이전트만 처리합니다: {agent_name}",
                0,
            )

        t = ticker or DEFAULT_TICKER
        execution_time_ms = random.randint(100, 600)

        signal_data = MOCK_NEWS_SIGNALS.get(t)
        if signal_data:
            signal = InvestmentSignalResponse(**signal_data)
            return SubAgentResponse.success_with_signal(signal, {"ticker": t}, execution_time_ms)
        return SubAgentResponse.no_data("news", execution_time_ms)
