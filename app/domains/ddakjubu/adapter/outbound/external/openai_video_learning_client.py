import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from openai import AsyncOpenAI

from app.domains.ddakjubu.application.port.video_learning_port import VideoLearningPort
from app.domains.ddakjubu.domain.entity.learning_note import LearningNote, StockInsight
from app.domains.ddakjubu.domain.entity.source_video import SourceVideo

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTIONS = (
    "너는 한국 주식 투자 교육 콘텐츠를 분석하는 금융 애널리스트다. "
    "주어진 영상 컨텍스트(핵심 요약, 제목, 설명, 자막)를 근거로 해당 영상에서 언급된 "
    "주식 종목, 투자 관점(강세/약세/중립/관망), 핵심 주장, 그리고 근거를 추출한다. "
    "반드시 지정된 JSON 스키마로만 응답하며, 추측이나 영상에 없는 내용은 추가하지 않는다. "
    "영상에 언급된 종목이 없으면 stock_insights는 빈 배열로 반환한다."
)

JSON_SCHEMA_GUIDE = """반드시 다음 JSON 형식으로만 응답하라. 다른 설명 텍스트·코드펜스 절대 금지.

{
  "stock_insights": [
    {
      "stock_name": "종목명 (한글)",
      "ticker": "티커 또는 종목 코드 (없으면 빈 문자열)",
      "investment_view": "강세 | 약세 | 중립 | 관망 중 하나",
      "key_claims": ["핵심 주장 1", "핵심 주장 2"],
      "supporting_evidence": ["근거 1", "근거 2"]
    }
  ]
}
"""


class OpenAIVideoLearningClient(VideoLearningPort):
    """OpenAI Responses API (gpt-5-mini)로 영상 학습 결과 stock_insights를 추출하는 2차 패스 어댑터."""

    def __init__(self, api_key: str, model: str = "gpt-5-mini"):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def learn(self, source_video: SourceVideo) -> LearningNote:
        prompt = self._build_prompt(source_video)

        try:
            response = await self._client.responses.create(
                model=self._model,
                input=[
                    {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                    {"role": "user", "content": prompt},
                ],
                reasoning={"effort": "minimal"},
            )
            raw_text = response.output_text or ""
        except Exception as e:
            logger.error(
                "[ddakjubu_llm] OpenAI responses 호출 실패 video_id=%s error=%s",
                source_video.video_id,
                e,
            )
            raise

        parsed = self._parse_json(raw_text)

        return LearningNote(
            video_id=source_video.video_id,
            video_title=source_video.title,
            channel_name=source_video.channel_name,
            program_category=source_video.program_category or "학습프로그램",
            published_at=source_video.published_at,
            learned_at=datetime.now(timezone.utc),
            summary=source_video.summary.strip(),
            stock_insights=self._parse_insights(parsed.get("stock_insights", [])),
        )

    def _build_prompt(self, source_video: SourceVideo) -> str:
        summary_section = (
            source_video.summary.strip()
            if source_video.summary
            else "(1차 패스 요약 없음)"
        )
        transcript_section = (
            source_video.transcript
            if source_video.transcript
            else "(자막/음성 변환 텍스트 제공되지 않음)"
        )
        return (
            "다음은 딱주부TV '학습프로그램' 영상 데이터와 1차 패스로 생성된 핵심 요약이다.\n\n"
            f"[영상 ID] {source_video.video_id}\n"
            f"[프로그램 카테고리] {source_video.program_category or '학습프로그램'}\n"
            f"[채널] {source_video.channel_name} ({source_video.channel_id})\n"
            f"[업로드 일시] {source_video.published_at.isoformat()}\n"
            f"[수집 일시] {source_video.collected_at.isoformat()}\n"
            f"[제목]\n{source_video.title}\n\n"
            f"[설명]\n{source_video.description}\n\n"
            f"[1차 패스 핵심 요약]\n{summary_section}\n\n"
            f"[자막/음성 변환]\n{transcript_section}\n\n"
            f"위 컨텍스트만을 근거로 종목별 인사이트를 추출하라.\n\n"
            f"{JSON_SCHEMA_GUIDE}"
        )

    @staticmethod
    def _parse_json(raw_text: str) -> Dict[str, Any]:
        text = raw_text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    pass
        logger.warning("[ddakjubu_llm] LLM 응답 JSON 파싱 실패, 빈 결과 반환")
        return {"stock_insights": []}

    @staticmethod
    def _parse_insights(raw_insights: List[dict]) -> List[StockInsight]:
        insights: List[StockInsight] = []
        for item in raw_insights or []:
            if not isinstance(item, dict):
                continue
            insights.append(
                StockInsight(
                    stock_name=str(item.get("stock_name", "")).strip(),
                    ticker=str(item.get("ticker", "")).strip(),
                    investment_view=str(item.get("investment_view", "")).strip(),
                    key_claims=[str(c) for c in (item.get("key_claims") or []) if c],
                    supporting_evidence=[
                        str(e) for e in (item.get("supporting_evidence") or []) if e
                    ],
                )
            )
        return insights
