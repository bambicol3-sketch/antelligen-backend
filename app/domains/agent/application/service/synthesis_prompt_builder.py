from app.domains.agent.application.response.sub_agent_response import SubAgentResponse

_SIGNAL_LABEL = {
    "bullish": "매수",
    "bearish": "매도",
    "neutral": "중립",
}

_AGENT_LABEL = {
    "news": "뉴스",
    "disclosure": "공시",
    "finance": "재무",
}


def build_synthesis_prompt(ticker: str, query: str, sub_results: list[SubAgentResponse]) -> str:
    lines = [f"[종목코드: {ticker}] 사용자 질문: {query}\n"]

    for r in sub_results:
        agent_label = _AGENT_LABEL.get(r.agent_name, r.agent_name)

        if not r.is_success() or r.signal is None:
            lines.append(f"- {agent_label} 에이전트: 데이터 없음 또는 오류")
            continue

        signal_label = _SIGNAL_LABEL.get(r.signal.value, r.signal.value)
        confidence_str = f"{r.confidence:.0%}" if r.confidence is not None else "N/A"
        key_points_str = " / ".join(r.key_points) if r.key_points else "없음"

        lines.append(
            f"- {agent_label} 에이전트: 시그널={signal_label}, 신뢰도={confidence_str}\n"
            f"  요약: {r.summary or '없음'}\n"
            f"  핵심포인트: {key_points_str}"
        )

    return "\n".join(lines)
