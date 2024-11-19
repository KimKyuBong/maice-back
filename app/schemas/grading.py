from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from .base import ResponseBase, TimeStampedBase
from .criteria import DetailedScore, GradingCriteria

class GradingRequest(BaseModel):
    edited_text: Optional[str] = None
    grading_criteria: Optional[GradingCriteria] = None

    class Config:
        from_attributes = True

class GradingResponse(TimeStampedBase):
    id: int
    student_id: str
    problem_key: str
    submission_id: int
    extraction_id: int
    extracted_text: str
    total_score: float
    max_score: float
    feedback: str
    grading_number: int
    image_path: str
    detailed_scores: List[DetailedScore]

    class Config:
        from_attributes = True

class GradingListResponse(BaseModel):
    items: List[GradingResponse]
    total: int
    limit: int
    offset: int

    class Config:
        from_attributes = True

# Export these classes
__all__ = [
    'GradingResponse', 
    'GradingRequest',
    'GradingListResponse'
]