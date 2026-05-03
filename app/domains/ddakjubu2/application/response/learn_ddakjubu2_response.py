from typing import List

from pydantic import BaseModel


class LearnedVideoItem(BaseModel):
    video_id: str
    video_title: str
    program_category: str
    stock_count: int


class LearnDdakjubu2Response(BaseModel):
    file_path: str
    processed_count: int
    skipped_duplicate_count: int
    videos: List[LearnedVideoItem]
