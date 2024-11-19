from pydantic import BaseModel
from .base import ResponseBase

class TextExtractionBase(BaseModel):
    student_id: str
    problem_key: str
    extracted_text: str
    submission_id: int

class OCRResponse(ResponseBase):
    submission_id: int
    extracted_text: str 