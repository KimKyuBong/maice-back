from app.services.base_service import BaseService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import logging
import os
from datetime import datetime
from app import models
from app.schemas import StudentSubmissionResponse
from fastapi import UploadFile
import aiofiles
from typing import Optional, Dict, List
from app.core.config import settings
from app.services.file.file_service import FileService

logger = logging.getLogger(__name__)

class SubmissionService(BaseService):

    def __init__(self):
        super().__init__(settings)
        self.file_service = FileService()

    async def create_submission(
        self,
        student_id: str,
        problem_key: str,
        file: UploadFile,
        db: AsyncSession
    ) -> Optional[models.StudentSubmission]:
        """새로운 제출물 생성"""
        try:
            # 파일 저장
            image_path = await self.file_service.save_file(student_id, problem_key, file)
            if not image_path:
                raise ValueError("Failed to save file")

            # 제출 정보 생성
            submission = models.StudentSubmission(
                student_id=student_id,
                problem_key=problem_key,
                file_name=file.filename,
                image_path=image_path,
                file_size=os.path.getsize(os.path.join(self.base_dir, "uploads", image_path)),
                mime_type=file.content_type
            )
            
            db.add(submission)
            await db.flush()
            
            return submission

        except Exception as e:
            logger.error(f"Error creating submission: {str(e)}")
            raise

    async def get_submissions(
        self,
        student_id: str,
        db: AsyncSession,
        problem_key: Optional[str] = None
    ) -> List[models.StudentSubmission]:
        """학생의 제출물 목록 조회"""
        try:
            query = select(models.StudentSubmission).filter_by(student_id=student_id)
            
            if problem_key:
                query = query.filter_by(problem_key=problem_key)
                
            result = await db.execute(query.order_by(models.StudentSubmission.created_at.desc()))
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error fetching submissions: {str(e)}")
            raise

    async def get_next_attempt_number(
        self,
        student_id: str,
        problem_key: str,
        db: AsyncSession
    ) -> int:
        """다음 시도 번호 조회"""
        try:
            result = await db.execute(
                select(func.max(models.Grading.grading_number))
                .filter_by(student_id=student_id, problem_key=problem_key)
            )
            max_number = result.scalar() or 0
            return max_number + 1

        except Exception as e:
            logger.error(f"Error getting next attempt number: {str(e)}")
            return 1