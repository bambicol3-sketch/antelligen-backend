from dataclasses import dataclass
from typing import Optional


@dataclass
class TempTokenData:
    kakao_access_token: str
    nickname: Optional[str]
    email: Optional[str]
