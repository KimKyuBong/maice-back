from pydantic import BaseModel
from datetime import datetime
from typing import Dict, List, Optional
from .grading import GradingSummary
from .base import ResponseBase

class StudentBase(BaseModel):
    id: str

class StudentCreate(StudentBase):
    pass

class StudentResponse(StudentBase):
    gradings: Optional[List[GradingSummary]] = None

    class Config:
        from_attributes = True

class StudentResults(BaseModel):
    results: Dict[str, List[GradingSummary]]

    class Config:
        from_attributes = True

class StudentListResponse(ResponseBase[List[StudentResponse]]):
    """학생 목록 응답"""
    pass

class StudentDetailResponse(ResponseBase[StudentResponse]):
    """학생 상세 응답"""
    pass