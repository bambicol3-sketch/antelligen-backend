from pydantic import BaseModel, Field


class AddWatchlistStockRequest(BaseModel):
    stock_code: str = Field(..., min_length=1, description="추가할 종목 코드")
