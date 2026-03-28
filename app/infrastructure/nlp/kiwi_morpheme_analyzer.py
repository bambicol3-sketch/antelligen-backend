from functools import lru_cache

from kiwipiepy import Kiwi

from app.domains.market_video.application.port.out.morpheme_analyzer_port import MorphemeAnalyzerPort

NOUN_TAGS = {"NNG", "NNP"}
MIN_NOUN_LENGTH = 2
STOPWORDS = {
    "것", "수", "때", "등", "및", "이", "그", "저", "들",
    "년", "월", "일", "때문", "통해", "위해", "대한", "관련",
    "이후", "이전", "현재", "가장", "매우", "정도", "경우",
    "사람", "우리", "지금", "오늘", "내일", "어제",
}


class KiwiMorphemeAnalyzer(MorphemeAnalyzerPort):
    def __init__(self):
        self._kiwi = Kiwi()

    def extract_nouns(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        tokens = self._kiwi.tokenize(text)
        return [
            token.form
            for token in tokens
            if token.tag in NOUN_TAGS
            and len(token.form) >= MIN_NOUN_LENGTH
            and token.form not in STOPWORDS
        ]


@lru_cache(maxsize=1)
def get_morpheme_analyzer() -> KiwiMorphemeAnalyzer:
    return KiwiMorphemeAnalyzer()
