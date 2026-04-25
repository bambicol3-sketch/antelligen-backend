from pydantic import BaseModel


class WatchlistStockItem(BaseModel):
    code: str
    name: str


class WatchlistResponse(BaseModel):
    stocks: list[WatchlistStockItem]


class WatchlistItemWithTheme(BaseModel):
    stock_code: str
    stock_name: str
    theme_name: str


class GetWatchlistResponse(BaseModel):
    stocks: list[WatchlistItemWithTheme]
