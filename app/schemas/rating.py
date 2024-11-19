from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class RatingCreate(BaseModel):
    grading_id: int
    rating_score: float = Field(..., ge=1, le=5)  # 1-5 사이 점수
    comment: Optional[str] = None

class RatingResponse(BaseModel):
    id: int
    grading_id: int
    rater_id: str
    rating_score: float
    comment: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class RatingStats(BaseModel):
    average_score: float
    total_ratings: int
    rating_distribution: dict[int, int]  # {점수: 개수} 