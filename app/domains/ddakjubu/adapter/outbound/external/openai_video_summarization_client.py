import logging

from openai import AsyncOpenAI

from app.domains.ddakjubu.application.port.video_summarization_port import (
    VideoSummarizationPort,
)
from app.domains.ddakjubu.domain.entity.source_video import SourceVideo

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTIONS = (
    "너는 한국 주식 투자 교육 영상을 요약하는 전문가다. "
    "YouTube Premium의 AI 영상 요약처럼, 제공된 자막·제목·설명을 기반으로 "
    "영상의 흐름·논거·핵심 포인트를 체계적으로 재구성한다. "
    "요약은 반드시 영상 내용에 근거해야 하며, 추측하거나 없는 내용을 추가하지 않는다. "
    "응답은 순수한 한국어 요약 문단이며, 코드펜스·JSON·머릿말 없이 본문만 반환한다."
)

INSTRUCTION_TEMPLATE = """다음 영상 데이터를 바탕으로 '핵심 요약'을 작성하라.

요약 작성 규칙:
- 전체 분량은 5~10문장 (한국어)
- 첫 문장은 이 영상의 주제/결론을 한 줄로 요약
- 이후 문장들은 시간 순 또는 논리 순으로 핵심 근거, 주요 수치/레벨, 주장된 결론을 기술
- 영상 내 언급된 종목명·가격대·이벤트 날짜는 가능한 유지
- 자막이 없으면 제목과 설명만으로 합리적으로 요약
- 가치 판단(매수/매도)은 영상에서 명시적으로 언급된 경우에만 포함

영상 데이터:
[영상 ID] {video_id}
[프로그램] {program_category}
[채널] {channel_name} ({channel_id})
[업로드 일시] {published_at}
[제목]
{title}

[설명]
{description}

[자막/음성 변환]
{transcript_block}
"""


class OpenAIVideoSummarizationClient(VideoSummarizationPort):
    """OpenAI Responses API (gpt-5-mini)로 영상 핵심 요약을 생성하는 1차 패스 어댑터."""

    def __init__(self, api_key: str, model: str = "gpt-5-mini"):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def summarize(self, source_video: SourceVideo) -> str:
        prompt = INSTRUCTION_TEMPLATE.format(
            video_id=source_video.video_id,
            program_category=source_video.program_category or "학습프로그램",
            channel_name=source_video.channel_name,
            channel_id=source_video.channel_id,
            published_at=source_video.published_at.isoformat(),
            title=source_video.title,
            description=source_video.description,
            transcript_block=(
                source_video.transcript
                if source_video.transcript
                else "(자막 없음 — 제목과 설명만으로 요약)"
            ),
        )

        try:
            response = await self._client.responses.create(
                model=self._model,
                input=[
                    {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                    {"role": "user", "content": prompt},
                ],
                reasoning={"effort": "minimal"},
            )
        except Exception as e:
            logger.error(
                "[ddakjubu_summarize] OpenAI responses 호출 실패 video_id=%s error=%s",
                source_video.video_id,
                e,
            )
            raise

        text = (response.output_text or "").strip()
        return self._unwrap_codefence(text)

    @staticmethod
    def _unwrap_codefence(text: str) -> str:
        if text.startswith("```"):
            stripped = text.strip("`").strip()
            if stripped.lower().startswith("json"):
                stripped = stripped[4:].strip()
            return stripped
        return text
