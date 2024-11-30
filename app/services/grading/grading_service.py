import logging
from typing import Dict, Optional, List
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.base_service import BaseService
from app.services.assistant.assistant_service import AssistantService
from app.services.grading.grading_processor import GradingProcessor
from app.services.grading.grading_repository import GradingRepository
from app.services.grading.grading_assistant import GradingAssistant
from app.services.criteria.criteria_service import CriteriaService
from app.services.file.file_service import FileService
from app.core.config import settings
from app.schemas.analysis import TextExtraction, TextExtractionResponse
from app import models

logger = logging.getLogger(__name__)

class GradingService(BaseService):
    def __init__(self, repository: GradingRepository, assistant_service: AssistantService):
        super().__init__(settings)
        self.file_service = FileService()
        self.criteria_service = CriteriaService()
        self.assistant = GradingAssistant(assistant_service)
        self.processor = GradingProcessor(self.assistant)
        self.repository = repository

    async def create_grading(
        self,
        db: AsyncSession,
        student_id: str,
        problem_key: str,
        image_path: str,
        grading_data: dict,
        extraction: TextExtraction
    ) -> models.Grading:
        """채점 수행 및 결과 저장"""
        try:
            # 1. 채점 기준 조회
            criteria = await self.criteria_service.get_criteria_by_problem(problem_key, db)
            
            # 2. 채점 수행
            grading_result = await self.processor.process_grading(
                extraction=extraction,
                criteria=criteria
            )
            
            # 3. DB 저장
            grading = await self.repository.create_grading(
                db=db,
                student_id=student_id,
                problem_key=problem_key,
                image_path=image_path,
                grading_data=grading_result,
                extraction=extraction,
                criteria=criteria
            )
            
            # 4. 관계 데이터 로드를 위한 refresh
            await db.refresh(grading, ['detailed_scores'])
            
            return grading

        except Exception as e:
            logger.error(f"Error in create_grading: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"채점 처리 중 오류가 발생했습니다: {str(e)}"
            )

    async def get_grading(
        self,
        db: AsyncSession,
        grading_id: str
    ) -> Optional[models.Grading]:
        """채점 결과 조회"""
        try:
            return await self.repository.get_grading(db, grading_id)
        except Exception as e:
            logger.error(f"Error in get_grading: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"채점 결과 조회 중 오류가 발생했습니다: {str(e)}"
            )

    async def initialize(self):
        """서비스 초기화"""
        try:
            await self.assistant.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize GradingService: {e}")
            raise

    async def grade_solution(self, extraction: TextExtractionResponse, criteria: dict) -> Dict:
        """채점 수행 (프로세서로 위임)"""
        return await self.processor.process_grading(extraction, criteria)
    async def get_gradings(
        self,
        db: AsyncSession,
        student_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 10
    ) -> dict:
        """채점 이력 조회"""
        items = await self.repository.get_gradings(
            db=db,
            student_id=student_id,
            limit=limit,
            offset=skip
        )
        total = await self.repository.get_gradings_count(db, student_id)
        
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": skip
        }

    async def get_grading_detail(
        self,
        db: AsyncSession,
        grading_id: int
    ) -> Optional[models.Grading]:
        """채점 결과 상세 조회"""
        try:
            grading = await self.repository.get_grading_detail(db, grading_id)
            if not grading:
                raise HTTPException(
                    status_code=404,
                    detail=f"채점 ID {grading_id}에 해당하는 결과를 찾을 수 없습니다"
                )
            return grading
        except Exception as e:
            logger.error(f"Error in get_grading_detail: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"채점 결과 상세 조회 중 오류가 발생했습니다: {str(e)}"
            )
