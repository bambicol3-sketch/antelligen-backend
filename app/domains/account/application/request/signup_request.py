from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., min_length=5)
    watchlist: list[str] | None = Field(default=None, description="관심종목 코드 목록 (선택)")
