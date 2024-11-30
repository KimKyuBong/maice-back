from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import ResponseBase, TimeStampedBase

# OCR 관련 응답
class OCRResponse(ResponseBase[Dict[str, Any]]):
    """OCR 분석 응답"""
    pass

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
    submission_id: int

    class Config:
        from_attributes = True

class TextExtractionResponse(ResponseBase[Dict[str, Any]]):
    """텍스트 추출 응답"""
    pass

class MultipleExtractionResult(ResponseBase[Dict[str, Any]]):
    """다중 추출 결과"""
    results: List[Dict[str, Any]]
    gradings: List[Dict[str, Any]]
    count: int

class ImageAnalysisResponse(ResponseBase[Dict[str, Any]]):
    """이미지 분석 응답"""
    pass

class ImageProcessingResponse(ResponseBase[Dict[str, Any]]):
    """이미지 처리 응답"""
    pass