from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import ResponseBase, TimeStampedBase

# 기본 OCR 응답
class OCRResponse(ResponseBase):
    submission_id: int
    extracted_text: str
    message: str

    class Config:
        from_attributes = True

# 텍스트 추출 관련
class SolutionStep(BaseModel):
    step_number: int
    content: str
    expressions: List[Dict[str, str]] = []

class Expression(BaseModel):
    latex: str

class TextExtraction(TimeStampedBase):
    id: int
    student_id: str
    problem_key: str
    extraction_number: int
    extracted_text: str
    image_path: str
    solution_steps: str

    class Config:
        from_attributes = True

class TextExtractionResponse(BaseModel):
    id: int
    extracted_text: str
    solution_steps: Optional[List[Dict]] = []
    student_id: str
    problem_key: str
    image_path: str
    extraction_number: int
    submission_id: int

    class Config:
        from_attributes = True

# 분석 결과 응답
class MultipleExtractionResult(BaseModel):
    results: List[TextExtractionResponse]
    gradings: List[Dict[str, Any]]  # GradingResponse 타입 대신 Dict 사용하여 순환 참조 방지
    count: int

class ImageAnalysisResponse(ResponseBase):
    content: Optional[MultipleExtractionResult] = None

class ImageProcessingResponse(ResponseBase):
    data: Optional[Dict[str, Any]] = None