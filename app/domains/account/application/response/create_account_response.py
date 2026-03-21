from typing import Optional

from pydantic import BaseModel


class CreateAccountResponse(BaseModel):
    account_id: int
    nickname: Optional[str]
    email: str
    user_token: str
