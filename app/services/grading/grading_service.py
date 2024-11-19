import logging
from typing import Dict, Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.base_service import BaseService
from app.services.assistant.assistant_service import AssistantService
from app.services.grading.grading_processor import GradingProcessor
from app.services.grading.grading_repository import GradingRepository
from app.services.grading.grading_assistant import GradingAssistant
from app.services.grading.criteria_service import CriteriaService
from app.services.file.file_service import FileService
from app.core.config import settings
from app.schemas.analysis import TextExtractionResponse
from app import models

logger = logging.getLogger(__name__)

class GradingService(BaseService):
    def __init__(self, assistant_service: AssistantService):
        super().__init__(settings)
        self.file_service = FileService()
        self.criteria_service = CriteriaService()
        self.assistant = GradingAssistant(assistant_service)
        self.processor = GradingProcessor(self.assistant)
        self.repository = GradingRepository()

    def get_default_criteria(self, problem_key: str) -> dict:
        """기본 채점 기준 반환"""
        return {
            "problem_key": problem_key,
            "total_points": 100,
            "detailed_criteria": [
                {
                    "id": 1,
                    "item": "문제 이해",
                    "points": 20,
                    "description": "문제를 정확히 이해하고 필요한 정보를 파악"
                },
                {
                    "id": 2,
                    "item": "풀이 과정",
                    "points": 40,
                    "description": "논리적이고 단계적인 풀이 과정 전개"
                },
                {
                    "id": 3,
                    "item": "계산 정확도",
                    "points": 20,
                    "description": "수치 계산의 정확성"
                },
                {
                    "id": 4,
                    "item": "답안 표현",
                    "points": 20,
                    "description": "답안의 명확한 표현과 단위 표기"
                }
            ]
        }

    async def create_grading(
        self,
        db: AsyncSession,
        student_id: str,
        problem_key: str,
        image_path: str,
        grading_data: dict,
        extraction: TextExtractionResponse,
        criteria: dict = None
    ) -> dict:
        """채점 수행 및 결과 저장"""
        try:
            logger.info(f"채점 프로세스 시작 - student_id: {student_id}, problem_key: {problem_key}")
            
            # 1. 학생 존재 여부 확인
            student = await db.get(models.Student, student_id)
            if not student:
                raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")

            # 2. 채점 기준 확인
            if criteria is None or not criteria:
                criteria = self.get_default_criteria(problem_key)
                logger.info("기본 채점 기준 사용")

            # 3. TextExtraction 존재 여부 확인
            text_extraction = await db.get(models.TextExtraction, extraction.id)
            if not text_extraction:
                raise HTTPException(status_code=404, detail="OCR 결과를 찾을 수 없습니다.")

            # 4. 채점 수행
            grading_result = await self.processor.process_grading(
                extraction=extraction,
                criteria=criteria
            )
            logger.info(f"채점 완료 - 총점: {grading_result['total_score']}/{grading_result['max_score']}")

            # 5. DB 저장
            logger.info("채점 결과 DB 저장 시작")
            grading = await self.repository.create_grading(
                db=db,
                student_id=student_id,
                problem_key=problem_key,
                image_path=image_path,
                grading_data=grading_result,
                extraction=extraction,
                criteria=criteria  # 기본 채점 기준 전달
            )
            logger.info(f"채점 결과 DB 저장 완료 - grading_id: {grading['id']}")
            
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