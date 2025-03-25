from pydantic import BaseModel, EmailStr, constr
from datetime import datetime
from typing import Dict, List, Optional
from .grading import GradingSummary
from .base import ResponseBase

class StudentBase(BaseModel):
    id: str
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    is_active: bool = True

class StudentCreate(StudentBase):
    password: constr(min_length=8, max_length=100)

class StudentUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    password: Optional[constr(min_length=8, max_length=100)] = None
    is_active: Optional[bool] = None

class StudentResponse(StudentBase):
    created_at: datetime
    last_login: Optional[datetime] = None

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