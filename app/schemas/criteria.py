from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from .base import TimeStampedBase

class CriteriaInfo(BaseModel):
    """채점 기준 정보"""
    item: str
    description: str
    points: float

class DetailedScore(BaseModel):
    """세부 점수"""
    detailed_criteria_id: int
    score: float
    feedback: str
    criteria_info: CriteriaInfo

class DetailedCriteriaBase(BaseModel):
    """세부 채점 기준 기본"""
    item: str
    points: float
    description: str
    grading_criteria_id: int

class DetailedCriteriaCreate(DetailedCriteriaBase):
    pass

class DetailedCriteriaResponse(DetailedCriteriaBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class GradingCriteriaBase(BaseModel):
    """채점 기준 기본"""
    problem_key: str
    total_points: float
    correct_answer: str
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
    problem_key: str
    total_points: float
    detailed_criteria: List[CriteriaInfo]