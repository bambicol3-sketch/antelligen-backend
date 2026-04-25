from dataclasses import dataclass

MAIN_THEMES: list[str] = [
    # 국내
    "IT", "바이오", "반도체", "2차전지", "금융", "방산", "에너지", "소비재",
    "자동차", "조선", "화학", "철강", "건설", "엔터",
    # 해외
    "미국 빅테크", "미국 반도체", "미국 금융", "미국 바이오", "미국 전기차·에너지",
    "미국 소비재·유통", "중국·홍콩",
]


@dataclass(frozen=True)
class ThemeName:
    value: str

    def is_main(self) -> bool:
        return self.value in MAIN_THEMES
