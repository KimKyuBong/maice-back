import logging
import asyncio
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select, func
from app.models import TextExtraction
from app.schemas.analysis import ImageAnalysisResponse, TextExtractionResponse
from app.services.analysis.ocr_utils import OCRUtils
import json
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class OCRStorage:
    def __init__(self, utils: OCRUtils):
        self._db_semaphore = asyncio.Semaphore(10)
        self.utils = utils

    async def save_result(
        self,
        ocr_result: Dict,
        student_id: str,
        problem_key: str,
        image_path: str,
        submission_id: int,
        db: AsyncSession
    ) -> TextExtraction:
        """OCR 결과 저장"""
        try:
            # 다음 extraction_number 가져오기
            next_number = await self._get_next_extraction_number(
                db, student_id, problem_key
            )
            logger.info(f"다음 extraction_number: {next_number}")

            # TextExtraction 생성
            extraction = TextExtraction(
                student_id=student_id,
                problem_key=problem_key,
                extraction_number=next_number,
                extracted_text=ocr_result["text"],
                image_path=image_path,
                solution_steps=json.dumps(ocr_result.get("solution_steps", []), ensure_ascii=False),
                submission_id=submission_id
            )

            db.add(extraction)
            await db.flush()
            await db.refresh(extraction)
            logger.info(f"TextExtraction 저장 완료 - ID: {extraction.id}")
            
            return extraction

        except Exception as e:
            logger.error(f"Error saving OCR result: {str(e)}")
            raise

    async def _get_next_extraction_number(self, db: AsyncSession, student_id: str, problem_key: str) -> int:
        """최신 extraction_number 조회"""
        stmt = select(func.coalesce(func.max(TextExtraction.extraction_number), 0)).where(
            and_(
                TextExtraction.student_id == student_id,
                TextExtraction.problem_key == problem_key
            )
        )
        result = await db.execute(stmt)
        return result.scalar() + 1