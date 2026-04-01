import json
import logging

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.domains.agent.application.port.llm_synthesis_port import LlmSynthesisPort
from app.domains.agent.application.response.sub_agent_response import SubAgentResponse
from app.domains.agent.application.service.synthesis_prompt_builder import build_synthesis_prompt

logger = logging.getLogger(__name__)

_SYNTHESIS_MODEL = "gpt-4.1-nano"

_SYSTEM_PROMPT = """당신은 주식 종합 분석 전문가입니다.
뉴스, 공시, 재무 에이전트의 분석 결과를 종합하여 투자자에게 유용한 의견을 제공하세요.

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요:
{{"summary": "200자 이내 종합 의견", "key_points": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3"]}}"""


class OpenAISynthesisClient(LlmSynthesisPort):
    def __init__(self, api_key: str, model: str = _SYNTHESIS_MODEL) -> None:
        llm = ChatOpenAI(model=model, api_key=api_key, temperature=0)
        prompt = ChatPromptTemplate.from_messages([
            ("system", _SYSTEM_PROMPT),
            ("human", "{context}"),
        ])
        self._chain = prompt | llm | StrOutputParser()

    async def synthesize(
        self,
        ticker: str,
        query: str,
        sub_results: list[SubAgentResponse],
    ) -> tuple[str, list[str]]:
        context = build_synthesis_prompt(ticker, query, sub_results)
        try:
            raw = await self._chain.ainvoke({"context": context})
            parsed = json.loads(raw)
            summary = parsed.get("summary", "")
            key_points = parsed.get("key_points", [])
            if summary:
                return summary, key_points
        except Exception as exc:
            logger.warning("LLM synthesis failed, using fallback: %s", exc)

        # Fallback: 서브에이전트 요약 단순 연결
        summaries = [r.summary for r in sub_results if r.is_success() and r.summary]
        return " ".join(summaries) or "분석 결과를 생성하지 못했습니다.", []
