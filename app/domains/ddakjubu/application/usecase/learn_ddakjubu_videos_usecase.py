import logging
from typing import List

from app.domains.ddakjubu.application.port.ddakjubu_note_writer_port import DdakjubuNoteWriterPort
from app.domains.ddakjubu.application.port.ddakjubu_video_fetch_port import DdakjubuVideoFetchPort
from app.domains.ddakjubu.application.port.video_learning_port import VideoLearningPort
from app.domains.ddakjubu.application.port.video_summarization_port import (
    VideoSummarizationPort,
)
from app.domains.ddakjubu.application.port.video_transcript_fetch_port import (
    VideoTranscriptFetchPort,
)
from app.domains.ddakjubu.application.response.learn_ddakjubu_response import (
    LearnDdakjubuResponse,
    LearnedVideoItem,
)
from app.domains.ddakjubu.domain.entity.learning_note import LearningNote
from app.domains.ddakjubu.domain.entity.source_video import SourceVideo

logger = logging.getLogger(__name__)

DDAKJUBU_CHANNEL_IDS: List[str] = [
    "UC2-YdiOkgqWzIdDwCYW1utw",  # 딱딱한 주식 부드럽게 | 딱주부TV
]

PROGRAM_FILTERS: List[str] = [
    "back to the basic",
    "리듬",
]

MAX_RESULTS_PER_CHANNEL = 30


class LearnDdakjubuVideosUseCase:
    """딱주부TV 학습프로그램 영상을 LLM으로 학습하고 ddakjubu.md에 저장한다."""

    def __init__(
        self,
        video_fetch_port: DdakjubuVideoFetchPort,
        transcript_fetch_port: VideoTranscriptFetchPort,
        video_summarization_port: VideoSummarizationPort,
        video_learning_port: VideoLearningPort,
        note_writer_port: DdakjubuNoteWriterPort,
    ):
        self._video_fetch_port = video_fetch_port
        self._transcript_fetch_port = transcript_fetch_port
        self._video_summarization_port = video_summarization_port
        self._video_learning_port = video_learning_port
        self._note_writer_port = note_writer_port

    async def execute(self) -> LearnDdakjubuResponse:
        if not DDAKJUBU_CHANNEL_IDS:
            logger.info("[ddakjubu] 채널 목록이 비어있어 영상 조회를 수행하지 않습니다.")
            return LearnDdakjubuResponse(
                file_path="",
                processed_count=0,
                skipped_duplicate_count=0,
                videos=[],
            )

        source_videos = await self._video_fetch_port.fetch_learning_videos(
            channel_ids=DDAKJUBU_CHANNEL_IDS,
            program_filters=PROGRAM_FILTERS,
            max_results_per_channel=MAX_RESULTS_PER_CHANNEL,
        )

        if not source_videos:
            logger.info("[ddakjubu] 학습 대상 영상이 존재하지 않습니다.")
            return LearnDdakjubuResponse(
                file_path="",
                processed_count=0,
                skipped_duplicate_count=0,
                videos=[],
            )

        sorted_videos = self._sort_and_deduplicate(source_videos)

        existing_video_ids = self._note_writer_port.load_existing_video_ids()
        new_videos = [v for v in sorted_videos if v.video_id not in existing_video_ids]
        skipped = len(sorted_videos) - len(new_videos)

        if not new_videos:
            logger.info(
                "[ddakjubu] 새로 학습할 영상이 없습니다. skipped=%d",
                skipped,
            )
            return LearnDdakjubuResponse(
                file_path="",
                processed_count=0,
                skipped_duplicate_count=skipped,
                videos=[],
            )

        learned_notes: List[LearningNote] = []
        for video in new_videos:
            try:
                video.transcript = await self._transcript_fetch_port.fetch_transcript(
                    video.video_id
                )
                video.summary = await self._video_summarization_port.summarize(video)
                note = await self._video_learning_port.learn(video)
                learned_notes.append(note)
            except Exception as e:
                logger.warning(
                    "[ddakjubu] 학습 실패 video_id=%s error=%s",
                    video.video_id,
                    e,
                )
                continue

        if not learned_notes:
            return LearnDdakjubuResponse(
                file_path="",
                processed_count=0,
                skipped_duplicate_count=skipped,
                videos=[],
            )

        file_path = self._note_writer_port.append_notes(learned_notes)

        logger.info(
            "[ddakjubu] 학습 노트 저장 완료: file_path=%s, processed=%d, skipped_duplicates=%d",
            file_path,
            len(learned_notes),
            skipped,
        )

        items = [
            LearnedVideoItem(
                video_id=note.video_id,
                video_title=note.video_title,
                program_category=note.program_category,
                stock_count=len(note.stock_insights),
            )
            for note in learned_notes
        ]

        return LearnDdakjubuResponse(
            file_path=file_path,
            processed_count=len(learned_notes),
            skipped_duplicate_count=skipped,
            videos=items,
        )

    @staticmethod
    def _sort_and_deduplicate(videos: List[SourceVideo]) -> List[SourceVideo]:
        unique: dict[str, SourceVideo] = {}
        for video in videos:
            if video.video_id and video.video_id not in unique:
                unique[video.video_id] = video
        return sorted(
            unique.values(),
            key=lambda v: v.published_at,
            reverse=True,
        )
