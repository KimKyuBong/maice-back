from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from .base import TimeStampedBase, ResponseBase

class CriteriaInfo(BaseModel):
    """채점 기준 정보"""
    id: int
    item: str
    description: str
    points: float
    created_at: datetime

    class Config:
        from_attributes = True

class DetailedCriteriaBase(BaseModel):
    """세부 채점 기준 기본"""
    item: str
    points: float
    description: str
    grading_criteria_id: int

class DetailedCriteriaResponse(DetailedCriteriaBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class DetailedScore(BaseModel):
    """세부 점수"""
    id: int
    detailed_criteria_id: int
    score: float
    feedback: str
    detailed_criteria: Optional[CriteriaInfo] = None
    created_at: datetime

    class Config:
        from_attributes = True

class DetailedCriteriaCreate(DetailedCriteriaBase):
    pass

class GradingCriteriaBase(BaseModel):
    """채점 기준 기본"""
    problem_key: str
    total_points: float
    correct_answer: Optional[str] = None
    description: str

class GradingCriteriaCreate(GradingCriteriaBase):
    detailed_criteria: List[DetailedCriteriaCreate]

class GradingCriteriaResponse(GradingCriteriaBase):
    id: int
    created_at: datetime
    detailed_criteria: List[DetailedCriteriaResponse]

    class Config:
        from_attributes = True

class GradingCriteria(BaseModel):
    """채점 기준"""
    id: int
    problem_key: str
    total_points: float
    detailed_criteria: List[CriteriaInfo]
    created_at: datetime

    class Config:
        from_attributes = True

class GradingCriteriaUpdate(BaseModel):
    """채점 기준 업데이트 스키마"""
    problem_key: str
    total_points: float
    correct_answer: Optional[str] = None
    description: str
    detailed_criteria: List[DetailedCriteriaCreate]

class GradingCriteriaClone(BaseModel):
    """채점 기준 복제 스키마"""
    new_name: str
    created_by: str

class CriteriaBase(BaseModel):
    problem_key: Optional[str] = None
    title: str
    description: Optional[str] = None
    max_score: int
    is_default: bool = False
    
    class Config:
        from_attributes = True

class CriteriaCreate(CriteriaBase):
    pass

class CriteriaUpdate(CriteriaBase):
    pass

class CriteriaResponse(ResponseBase[GradingCriteria]):
    """채점 기준 응답"""
    pass

class GradingCriteriaListResponse(ResponseBase[List[GradingCriteriaResponse]]):
    """채점 기준 목록 응답"""
    pass

class GradingCriteriaDetailResponse(ResponseBase[GradingCriteriaResponse]):
    """채점 기준 상세 응답"""
    pass

class DetailedCriteriaListResponse(ResponseBase[List[DetailedCriteriaResponse]]):
    """세부 채점 기준 목록 응답"""
    pass