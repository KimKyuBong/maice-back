from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app import models
from app.routers.criteria import get_grading_criteria
from app.services.analysis.ocr_service import OCRService
from app.services.grading.grading_service import GradingService
from app.database import get_db
from app.dependencies import get_ocr_service, get_grading_service, Services, get_services
from app.schemas.evaluation import EvaluationResponse, GradingData, GradingResponse
from app.models import Grading
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime
import uuid
import os
from app.core.config import settings
from app.routers.submission import OCRResponse, process_single_grading
from app.models import Student, StudentSubmission, TextExtraction
import logging
import json
from sqlalchemy.exc import IntegrityError
from app.services.assistant.assistant_service import AssistantService
from app.utils.file_utils import save_uploaded_file

router = APIRouter(
    prefix="/evaluation",
    tags=["evaluation"]
)

logger = logging.getLogger(__name__)

@router.post("/submit", response_model=EvaluationResponse)
async def submit_solution(
    student_id: str = Form(...),
    solution_image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services)
) -> Dict[str, Any]:
    try:
        # OCR 서비스와 채점 서비스 가져오기
        ocr_service: OCRService = services.ocr_service
        grading_service: GradingService = services.grading_service
        
        # 1. 파일 저장
        relative_path = await save_uploaded_file(
            file=solution_image,
            student_id=student_id,
            upload_dir=Path(settings.UPLOAD_DIR)
        )
        full_path = Path(settings.UPLOAD_DIR) / relative_path

        # 2. DB 작업
        submission = StudentSubmission(
            student_id=student_id,
            file_name=solution_image.filename,
            image_path=str(relative_path),
            file_size=os.path.getsize(full_path),
            mime_type=solution_image.content_type
        )
        db.add(submission)
        await db.flush()

        # 3. OCR 분석
        ocr_result = await ocr_service.analyze_image(
            student_id=student_id,
            image_path=str(full_path),
            submission_id=submission.id,
            db=db
        )

        # 4. 채점
        grading = await grading_service.create_grading(
            student_id=student_id,
            image_path=relative_path,
            extraction=ocr_result,
            db=db
        )

        await db.commit()

        # 5. 응답 데이터 구성
        detailed_scores = [
            {
                "detailed_criteria_id": score.detailed_criteria_id,
                "detailed_criteria": {
                    "item": score.detailed_criteria.item,
                    "points": score.detailed_criteria.points,
                    "description": score.detailed_criteria.description
                },
                "score": score.score,
                "feedback": score.feedback
            }
            for score in grading.detailed_scores
        ]
        
        return EvaluationResponse(
            student_id=student_id,
            image_path=relative_path,
            extracted_text=ocr_result.extracted_text,
            extraction_number=ocr_result.extraction_number,
            grading_result=GradingResponse(
                total_score=grading.total_score,
                max_score=grading.max_score,
                feedback=grading.feedback,
                detailed_scores=detailed_scores
            )
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"제출 처리 중 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"제출 처리 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/{student_id}/history")
async def get_evaluation_history(
    student_id: str,
    db: AsyncSession = Depends(get_db)
):
    """학생의 전체 제출 이력 조회"""
    try:
        # 학생의 모든 채점 결과 조회
        query = select(Grading).where(
            Grading.student_id == student_id
        ).order_by(Grading.created_at.desc())
        
        result = await db.execute(query)
        gradings = result.scalars().all()
        
        return {
            "success": True,
            "submissions": [
                {
                    "problem_key": grading.problem_key,
                    "submitted_at": grading.created_at.isoformat(),
                    "score": grading.total_score,
                    "max_score": grading.max_score,
                    "feedback": grading.feedback,
                    "extracted_text": grading.extracted_text
                }
                for grading in gradings
            ]
        }
    except Exception as e:
        logger.error(f"이력 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{student_id}/problem/{problem_key}")
async def get_problem_evaluations(
    student_id: str,
    problem_key: str,
    db: AsyncSession = Depends(get_db)
):
    """특정 문제에 대한 학생의 제출 이력 조회"""
    try:
        # 특정 문제에 대한 채점 결과 조회
        query = select(Grading).where(
            Grading.student_id == student_id,
            Grading.problem_key == problem_key
        ).order_by(Grading.created_at.desc())
        
        result = await db.execute(query)
        gradings = result.scalars().all()
        
        return {
            "success": True,
            "problem_key": problem_key,
            "submissions": [
                {
                    "submitted_at": grading.created_at.isoformat(),
                    "score": grading.total_score,
                    "max_score": grading.max_score,
                    "feedback": grading.feedback,
                    "extracted_text": grading.extracted_text,
                    "image_path": grading.image_path
                }
                for grading in gradings
            ]
        }
    except Exception as e:
        logger.error(f"문제별 이력 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{student_id}/latest")
async def get_latest_evaluations(
    student_id: str,
    db: AsyncSession = Depends(get_db)
):
    """학생의 각 문제별 최신 제출 결과 조회"""
    try:
        # 서브쿼리로 각 문제별 최신 채점 결과 ID 조회
        latest_ids_subquery = (
            select(
                Grading.problem_key,
                func.max(Grading.created_at).label('max_created_at')
            )
            .where(Grading.student_id == student_id)
            .group_by(Grading.problem_key)
            .subquery()
        )

        # 최신 채점 결과 조회
        query = (
            select(Grading)
            .join(
                latest_ids_subquery,
                and_(
                    Grading.problem_key == latest_ids_subquery.c.problem_key,
                    Grading.created_at == latest_ids_subquery.c.max_created_at
                )
            )
            .where(Grading.student_id == student_id)
        )

        result = await db.execute(query)
        gradings = result.scalars().all()
        
        return {
            "success": True,
            "latest_submissions": [
                {
                    "problem_key": grading.problem_key,
                    "submitted_at": grading.created_at.isoformat(),
                    "score": grading.total_score,
                    "max_score": grading.max_score,
                    "feedback": grading.feedback,
                    "extracted_text": grading.extracted_text,
                    "image_path": grading.image_path
                }
                for grading in gradings
            ]
        }
    except Exception as e:
        logger.error(f"최신 결과 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

