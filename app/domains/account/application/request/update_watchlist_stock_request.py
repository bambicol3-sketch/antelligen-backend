from pydantic import BaseModel, Field


class UpdateWatchlistStockRequest(BaseModel):
    new_stock_code: str = Field(..., min_length=1, description="교체할 새 종목 코드")
