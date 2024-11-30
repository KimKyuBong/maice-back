from pydantic import BaseModel
from typing import Optional, Any, Generic, TypeVar
from datetime import datetime

T = TypeVar('T')

class ResponseBase(BaseModel, Generic[T]):
    """기본 응답 스키마"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[T] = None

class TimeStampedBase(BaseModel):
    """시간 정보를 포함하는 기본 스키마"""
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True 