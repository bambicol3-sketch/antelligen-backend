from pydantic import BaseModel


class CollectInvestorFlowResponse(BaseModel):
    target_date: str
    total_collected: int
    skipped_duplicates: int
