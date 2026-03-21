from pydantic import BaseModel


class CreateAccountRequest(BaseModel):
    nickname: str
    email: str
