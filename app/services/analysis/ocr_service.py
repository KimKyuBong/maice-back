from app import models
from app.services.base_service import BaseService
import logging
from typing import Optional
from app.services.assistant.assistant_service import AssistantService
from app.core.config import settings
from app.schemas.analysis import ImageAnalysisResponse, TextExtractionResponse
from sqlalchemy.ext.asyncio import AsyncSession
from .ocr_assistant import OCRAssistant
from .ocr_processor import OCRProcessor
from .ocr_storage import OCRStorage
from .ocr_utils import OCRUtils
from app.models import TextExtraction
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy import and_
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
import json
import asyncio
from functools import lru_cache
import time
from async_timeout import timeout
import os

logger = logging.getLogger(__name__)

class OCRService(BaseService):
    def __init__(self, assistant_service: AssistantService):
        super().__init__(settings)
        self.assistant_service = assistant_service
        self.utils = OCRUtils(self.client)
        self.processor = OCRProcessor(utils=self.utils)
        self.storage = OCRStorage(utils=self.utils)
        self.assistant = None
        self._cache = {}  # 간단한 인메모리 캐시
        logger.info("Initializing OCR Service...")

    async def initialize(self):
        """OCR 서비스 초기화"""
        if self.assistant is not None:
            return  # 이미 초기화되어 있으면 스킵
            
        try:
            self.assistant = OCRAssistant(self.assistant_service)
            await self.assistant.initialize()
            logger.info(f"OCR Assistant initialized successfully")
        except Exception as e:
            logger.error(f"OCR Assistant initialization failed: {e}")
            raise

    def _get_cache_key(self, image_path: str) -> str:
        return f"ocr:{image_path}"

    async def _get_cached_result(self, image_path: str) -> Optional[dict]:
        cache_key = self._get_cache_key(image_path)
        return self._cache.get(cache_key)

    async def _set_cached_result(self, image_path: str, result: dict, ttl: int = 3600):
        cache_key = self._get_cache_key(image_path)
        self._cache[cache_key] = {
            'result': result,
            'expires_at': time.time() + ttl
        }

    async def analyze_image(
        self,
        student_id: str,
        image_path: str,
        submission_id: int,
        problem_key: str,
        db: AsyncSession
    ) -> TextExtraction:
        try:
            start_time = time.time()
            
            # OCR 분석 수행
            result = await self.processor.process_image(
                image_path=image_path,
                assistant=self.assistant,
                student_id=student_id,
                problem_key=problem_key
            )
            
            logger.info(f"OCR 분석 완료: {time.time() - start_time:.2f}초 소요")

            # OCR 결과 저장 (extraction 객체 직접 반환)
            extraction = await self.storage.save_result(
                ocr_result=result,
                student_id=student_id,
                problem_key=problem_key,
                image_path=image_path,
                submission_id=submission_id,
                db=db
            )
            
            logger.info(f"OCR 결과 저장 완료 - ID: {extraction.id}")
            return extraction

        except Exception as e:
            logger.error(f"OCR 분석 중 오류 발생: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
