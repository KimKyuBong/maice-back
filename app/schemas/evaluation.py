from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from .base import ResponseBase

class DetailedCriteria(BaseModel):
    id: int
    item: str
    points: float
    description: str

class DetailedScore(BaseModel):
    detailed_criteria_id: int
    score: float
    feedback: str

class Submission(BaseModel):
    id: int
    student_id: str
    problem_key: str
    image_path: str
    created_at: datetime

class GradingResponse(BaseModel):
    total_score: float
    max_score: float
    feedback: str
    detailed_scores: List[DetailedScore]

class GradingData(BaseModel):
    id: int
    submission_id: int
    student_id: str
    problem_key: str
    extracted_text: str
    total_score: float
    max_score: float
    feedback: str
    grading_number: int
    image_path: str
    created_at: datetime
    detailed_scores: List[DetailedScore]
    submission: Submission

class SolutionDetail(BaseModel):
    """풀이 상세 정보"""
    id: int
    problem_key: str
    solution_text: str
    created_at: datetime

    class Config:
        from_attributes = True

class RatingDetail(BaseModel):
    """평가 상세 정보"""
    id: int
    rating: int
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class StudentSolutions(BaseModel):
    """학생 풀이 정보"""
    student_id: str
    solutions: List[SolutionDetail]
    ratings: Optional[List[RatingDetail]] = None

    class Config:
        from_attributes = True

class EvaluationListResponse(ResponseBase[List[StudentSolutions]]):
    """평가 목록 응답"""
    pass

class EvaluationResponse(ResponseBase[StudentSolutions]):
    """평가 응답"""
    pass

class RatingDetail(BaseModel):
    rating: int
    comment: str
  