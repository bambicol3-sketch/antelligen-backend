from collections import Counter


class NounExtractor:

    @staticmethod
    def count_frequencies(nouns: list[str]) -> list[tuple[str, int]]:
        if not nouns:
            return []
        return Counter(nouns).most_common()
