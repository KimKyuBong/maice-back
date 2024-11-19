from typing import Optional, Dict, Union
import os
import logging
from app.core.config import settings
from openai import AsyncOpenAI
from app.schemas.analysis import ImageAnalysisResponse, TextExtraction, TextExtractionResponse, MultipleExtractionResult, SolutionStep, Expression
from datetime import datetime
import json
from app.models import TextExtraction

logger = logging.getLogger(__name__)

class OCRUtils:
    def __init__(self, client: AsyncOpenAI):
        self.client = client
        self.upload_dir = settings.UPLOAD_DIR

    @staticmethod
    def get_full_path(relative_path: str) -> str:
        """전체 경로 반환"""
        if not relative_path:
            return ""
        return os.path.join(settings.UPLOAD_DIR, relative_path.lstrip('/'))

    async def cleanup_resources(self, file_id: Optional[str], thread_id: Optional[str]):
        """리소스 정리"""
        try:
            if thread_id:
                await self.client.beta.threads.delete(thread_id)
                logger.info(f"Deleted thread: {thread_id}")
            if file_id:
                await self.client.files.delete(file_id)
                logger.info(f"Deleted file: {file_id}")
        except Exception as cleanup_error:
            logger.error(f"Cleanup error: {cleanup_error}")

    def format_response(self, raw_result: TextExtraction) -> TextExtractionResponse:
        """TextExtraction 모델을 TextExtractionResponse로 변환"""
        logger.info(f"TextExtractionResponse 생성 시작 - raw_result.id: {raw_result.id}")
        
        try:
            response = TextExtractionResponse(
                id=raw_result.id,
                student_id=raw_result.student_id,
                problem_key=raw_result.problem_key,
                extracted_text=raw_result.extracted_text,
                image_path=raw_result.image_path,
                extraction_number=raw_result.extraction_number,
                solution_steps=json.loads(raw_result.solution_steps) if raw_result.solution_steps else [],
                submission_id=raw_result.submission_id
            )
            return response
        except Exception as e:
            logger.error(f"TextExtractionResponse 생성 중 오류: {str(e)}")
            raise

    def validate_ocr_result(self, ocr_result: Dict) -> bool:
        """OCR 결과 유효성 검사"""
        try:
            if not isinstance(ocr_result, dict):
                logger.error("OCR result is not a dictionary")
                return False
            
            if "text" not in ocr_result:
                logger.error("OCR result missing 'text' field")
                return False
            
            if not isinstance(ocr_result.get("text"), str):
                logger.error("OCR result 'text' field is not a string")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return False

    def clean_step_data(self, step: Dict) -> Dict:
        """단계별 데이터 정제"""
        try:
            cleaned_step = {
                "step_number": int(step.get("step_number", 0)),
                "content": str(step.get("content", "")),
                "expressions": []
            }
            
            expressions = step.get("expressions", [])
            if isinstance(expressions, list):
                cleaned_expressions = []
                for expr in expressions:
                    if isinstance(expr, dict) and "latex" in expr:
                        cleaned_expressions.append({"latex": str(expr["latex"])})
                cleaned_step["expressions"] = cleaned_expressions
            
            return cleaned_step
        except Exception as e:
            logger.error(f"Error cleaning step data: {e}")
            return {
                "step_number": 0,
                "content": "",
                "expressions": []
            }