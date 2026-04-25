from pydantic import BaseModel


class WatchlistStockItem(BaseModel):
    code: str
    name: str


class SignupResponse(BaseModel):
    account_id: int
    email: str
    nickname: str
    watchlist: list[WatchlistStockItem]
