from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any, List
from .base import TimeStampedBase, ResponseBase

class StudentSubmissionBase(TimeStampedBase):
    student_id: str
    problem_key: str
    file_name: str
    image_path: str
    file_size: int
    mime_type: str

class StudentSubmissionCreate(StudentSubmissionBase):
    pass

class StudentSubmissionResponse(StudentSubmissionBase):
    id: int

    class Config:
        from_attributes = True

class SubmissionResponse(ResponseBase):
    """제출 처리 결과 응답"""
    success: bool
    message: str
    data: Optional[Dict[str, List[Any]]] = None  # extractions와 gradings를 포함하는 딕셔너리

    class Config:
        from_attributes = True