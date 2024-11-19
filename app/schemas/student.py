from pydantic import BaseModel
from datetime import datetime
from typing import Dict, List, Optional
from .grading import GradingResponse

class StudentBase(BaseModel):
    id: str

class StudentCreate(StudentBase):
    pass

class StudentResponse(StudentBase):
    gradings: Optional[List[GradingResponse]] = None

    class Config:
        from_attributes = True

class StudentResults(BaseModel):
    results: Dict[str, List[GradingResponse]]

    class Config:
        from_attributes = True