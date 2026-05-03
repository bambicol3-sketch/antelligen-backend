import asyncio
from datetime import datetime
from typing import List

from app.domains.ddakjubu2.application.port.ddakjubu2_note_writer_port import (
    Ddakjubu2NoteWriterPort,
)
from app.domains.ddakjubu2.application.port.ddakjubu2_video_fetch_port import (
    Ddakjubu2VideoFetchPort,
)
from app.domains.ddakjubu2.application.port.video_learning_port import VideoLearningPort
from app.domains.ddakjubu2.application.port.video_summarization_port import (
    VideoSummarizationPort,
)
from app.domains.ddakjubu2.application.port.video_transcript_fetch_port import (
    VideoTranscriptFetchPort,
)
from app.domains.ddakjubu2.application.response.learn_ddakjubu2_response import (
    LearnDdakjubu2Response,
    LearnedVideoItem,
)
from app.domains.ddakjubu2.domain.entity.learning_note import LearningNote
from app.domains.ddakjubu2.domain.entity.source_video import SourceVideo

DDAKJUBU2_CHANNEL_IDS: List[str] = [
    "UC2-YdiOkgqWzIdDwCYW1utw",  # 딱딱한 주식 부드럽게 | 딱주부TV
]

BATCH_SAVE_SIZE = 3


class EnhanceDdakjubu2VideosUseCase:
    """딱주부TV 2026년 업로드 영상을 자막 포함 재학습하여 별도 Markdown 파일에 저장한다.

    기존 ddakjubu2.md (자막 없이 학습됨) 와는 별개 파일로 관리한다.
    IP 차단을 유발하지 않도록 영상 사이에 sleep 을 넣어 느리게 진행한다.
    """

    def __init__(
        self,
        video_fetch_port: Ddakjubu2VideoFetchPort,
        transcript_fetch_port: VideoTranscriptFetchPort,
        video_summarization_port: VideoSummarizationPort,
        video_learning_port: VideoLearningPort,
        note_writer_port: Ddakjubu2NoteWriterPort,
        published_after: datetime,
        sleep_between_videos_seconds: int,
    ):
        self._video_fetch_port = video_fetch_port
        self._transcript_fetch_port = transcript_fetch_port
        self._video_summarization_port = video_summarization_port
        self._video_learning_port = video_learning_port
        self._note_writer_port = note_writer_port
        self._published_after = published_after
        self._sleep_seconds = sleep_between_videos_seconds

    async def execute(self) -> LearnDdakjubu2Response:
        print(
            f"[ddakjubu2_enhance] 재학습 파이프라인 시작 "
            f"published_after={self._published_after.isoformat()} "
            f"sleep={self._sleep_seconds}s",
            flush=True,
        )

        if not DDAKJUBU2_CHANNEL_IDS:
            print("[ddakjubu2_enhance] 채널 목록이 비어있어 종료", flush=True)
            return LearnDdakjubu2Response(
                file_path="",
                processed_count=0,
                skipped_duplicate_count=0,
                videos=[],
            )

        source_videos = await self._video_fetch_port.fetch_channel_videos(
            channel_ids=DDAKJUBU2_CHANNEL_IDS,
            published_after=self._published_after,
        )
        print(
            f"[ddakjubu2_enhance] 채널에서 조회된 2026 영상 수: {len(source_videos)}",
            flush=True,
        )

        if not source_videos:
            print("[ddakjubu2_enhance] 재학습 대상 영상이 없습니다.", flush=True)
            return LearnDdakjubu2Response(
                file_path="",
                processed_count=0,
                skipped_duplicate_count=0,
                videos=[],
            )

        sorted_videos = self._sort_and_deduplicate(source_videos)

        # 기존에 이미 enhanced 파일에 저장된 video_id 는 skip (중단 후 재실행 시 이어서 진행)
        existing_video_ids = self._note_writer_port.load_existing_video_ids()
        new_videos = [v for v in sorted_videos if v.video_id not in existing_video_ids]
        skipped = len(sorted_videos) - len(new_videos)
        print(
            f"[ddakjubu2_enhance] 신규 재학습 대상: {len(new_videos)}, "
            f"기존 enhanced 파일 skip: {skipped}",
            flush=True,
        )

        if not new_videos:
            print("[ddakjubu2_enhance] 새로 재학습할 영상이 없습니다.", flush=True)
            return LearnDdakjubu2Response(
                file_path="",
                processed_count=0,
                skipped_duplicate_count=skipped,
                videos=[],
            )

        batch_buffer: List[LearningNote] = []
        all_notes: List[LearningNote] = []
        file_path = ""

        for idx, video in enumerate(new_videos, start=1):
            print(
                f"[ddakjubu2_enhance] ({idx}/{len(new_videos)}) 학습 시작 "
                f"video_id={video.video_id} title={video.title[:40]}",
                flush=True,
            )
            try:
                video.transcript = await self._transcript_fetch_port.fetch_transcript(
                    video.video_id
                )
                print(
                    f"[ddakjubu2_enhance]   - 자막 길이={len(video.transcript)}",
                    flush=True,
                )

                video.summary = await self._video_summarization_port.summarize(video)
                note = await self._video_learning_port.learn(video)
                print(
                    f"[ddakjubu2_enhance]   - 요약 {len(video.summary)}자, "
                    f"종목 {len(note.stock_insights)}개",
                    flush=True,
                )
                batch_buffer.append(note)
                all_notes.append(note)
            except Exception as e:
                print(
                    f"[ddakjubu2_enhance]   ! 학습 실패 video_id={video.video_id} error={e}",
                    flush=True,
                )

            if len(batch_buffer) >= BATCH_SAVE_SIZE:
                file_path = self._note_writer_port.append_notes(batch_buffer)
                print(
                    f"[ddakjubu2_enhance] 배치 저장 batch={len(batch_buffer)} "
                    f"cumulative={len(all_notes)}/{len(new_videos)} path={file_path}",
                    flush=True,
                )
                batch_buffer = []

            if idx < len(new_videos):
                print(
                    f"[ddakjubu2_enhance] 다음 영상 전 대기 {self._sleep_seconds}초",
                    flush=True,
                )
                await asyncio.sleep(self._sleep_seconds)

        if batch_buffer:
            file_path = self._note_writer_port.append_notes(batch_buffer)
            print(
                f"[ddakjubu2_enhance] 마지막 배치 저장 batch={len(batch_buffer)} "
                f"cumulative={len(all_notes)}/{len(new_videos)} path={file_path}",
                flush=True,
            )

        print(
            f"[ddakjubu2_enhance] 파이프라인 종료: file_path={file_path}, "
            f"processed={len(all_notes)}, skipped={skipped}",
            flush=True,
        )

        items = [
            LearnedVideoItem(
                video_id=note.video_id,
                video_title=note.video_title,
                program_category=note.program_category,
                stock_count=len(note.stock_insights),
            )
            for note in all_notes
        ]

        return LearnDdakjubu2Response(
            file_path=file_path,
            processed_count=len(all_notes),
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
