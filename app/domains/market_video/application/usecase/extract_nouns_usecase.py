from app.domains.market_video.application.port.out.morpheme_analyzer_port import MorphemeAnalyzerPort
from app.domains.market_video.application.port.out.video_comment_repository_port import VideoCommentRepositoryPort
from app.domains.market_video.application.response.noun_frequency_response import (
    NounFrequencyItem,
    NounFrequencyResponse,
)
from app.domains.market_video.domain.service.noun_extractor import NounExtractor


class ExtractNounsUseCase:
    def __init__(
        self,
        video_comment_repository: VideoCommentRepositoryPort,
        morpheme_analyzer: MorphemeAnalyzerPort,
    ):
        self._repository = video_comment_repository
        self._analyzer = morpheme_analyzer

    async def execute(self, top_n: int = 30) -> NounFrequencyResponse:
        comments = await self._repository.find_all()

        if not comments:
            return NounFrequencyResponse(total_unique_nouns=0, selected_count=0, items=[])

        all_nouns: list[str] = []
        for comment in comments:
            nouns = self._analyzer.extract_nouns(comment.content)
            all_nouns.extend(nouns)

        frequencies = NounExtractor.count_frequencies(all_nouns)
        all_items = [NounFrequencyItem(noun=noun, count=count) for noun, count in frequencies]
        top_items = all_items[:top_n]

        return NounFrequencyResponse(
            total_unique_nouns=len(all_items),
            selected_count=len(top_items),
            items=top_items,
        )
