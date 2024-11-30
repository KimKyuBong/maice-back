from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from .base import ResponseBase

class DetailedCriteriaResponse(BaseModel):
    """채점 기준 상세 응답"""
    id: int
    item: str
    points: float
    description: str

    class Config:
        from_attributes = True

class DetailedScoreResponse(BaseModel):
    """채점 상세 점수 응답"""
    detailed_criteria_id: int
    score: float
    feedback: str
    detailed_criteria: DetailedCriteriaResponse

    class Config:
        from_attributes = True

class GradingData(BaseModel):
    """채점 결과 데이터"""
    id: int
    student_id: str
    problem_key: str
    total_score: float
    max_score: float
    feedback: str
    created_at: datetime
    detailed_scores: List[DetailedScoreResponse]
    extracted_text: Optional[str] = None
    image_data: Optional[str] = None
    image_path: Optional[str] = None

    class Config:
        from_attributes = True

class GradingListData(BaseModel):
    """채점 결과 목록 데이터"""
    items: List[GradingData]
    total: int
    limit: int
    offset: int

    class Config:
        from_attributes = True

class GradingSummary(ResponseBase[GradingData]):
    """채점 결과 요약"""
    pass

class GradingDetailResponse(ResponseBase[GradingData]):
    """채점 결과 상세 응답"""
    pass

class GradingListResponse(ResponseBase[GradingListData]):
    """채점 결과 목록 응답"""
    pass

class GradingRequest(BaseModel):
    """채점 요청"""
    edited_text: Optional[str] = None