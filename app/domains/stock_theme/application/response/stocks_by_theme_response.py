from pydantic import BaseModel


class ThemeStockItem(BaseModel):
    code: str
    name: str
    theme_name: str


class ThemeGroupResponse(BaseModel):
    theme_name: str
    stocks: list[ThemeStockItem]


class StocksByThemeGroupedResponse(BaseModel):
    themes: list[ThemeGroupResponse]


class StocksByThemeListResponse(BaseModel):
    theme_name: str
    total: int
    stocks: list[ThemeStockItem]
