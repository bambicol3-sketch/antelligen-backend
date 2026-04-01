import time

from app.domains.agent.application.port.news_agent_port import NewsAgentPort
from app.domains.agent.application.response.investment_signal_response import (
    InvestmentSignal,
    InvestmentSignalResponse,
)
from app.domains.agent.application.response.sub_agent_response import SubAgentResponse

# TODO: 뉴스 팀원 구현 완료 시 실제 UseCase 연동으로 교체
# SearchNewsUseCase + AnalyzeArticleUseCase 활용 예정
_MOCK_NEWS_SIGNALS: dict[str, dict] = {
    "005930": {
        "signal": "bullish",
        "confidence": 0.82,
        "summary": "삼성전자 AI 반도체 투자 확대 발표로 긍정적 전망",
        "key_points": [
            "AI 반도체 설비 투자 3조원 추가 확정",
            "HBM4 양산 일정 앞당김",
            "주요 외국계 증권사 목표가 상향",
        ],
    },
    "000660": {
        "signal": "bullish",
        "confidence": 0.78,
        "summary": "SK하이닉스 HBM4 양산 본격화로 실적 개선 기대",
        "key_points": [
            "HBM4 양산 라인 가동 시작",
            "엔비디아 공급 계약 확대",
        ],
    },
    "005380": {
        "signal": "neutral",
        "confidence": 0.60,
        "summary": "현대자동차 전기차 전환 가속화로 단기 비용 부담",
        "key_points": [
            "전기차 전용 플랫폼 투자 확대",
            "단기 수익성 압박 우려",
        ],
    },
}


class NewsSubAgentAdapter(NewsAgentPort):
    """뉴스 에이전트 어댑터 — 팀원 구현 완료 전까지 Mock 사용."""

    async def analyze(self, ticker: str, query: str) -> SubAgentResponse:
        start = time.monotonic()
        signal_data = _MOCK_NEWS_SIGNALS.get(ticker)
        elapsed = int((time.monotonic() - start) * 1000)

        if not signal_data:
            return SubAgentResponse.no_data("news", elapsed)

        signal_response = InvestmentSignalResponse(
            agent_name="news",
            ticker=ticker,
            signal=InvestmentSignal(signal_data["signal"]),
            confidence=signal_data["confidence"],
            summary=signal_data["summary"],
            key_points=signal_data["key_points"],
        )
        return SubAgentResponse.success_with_signal(
            signal_response, {"ticker": ticker}, elapsed
        )
