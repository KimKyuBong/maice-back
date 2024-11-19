from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, joinedload
from typing import List, Optional
import logging
import json

from app.database import get_db
from app.models import Student, Grading, DetailedScore, DetailedCriteria
from app.schemas import GradingResponse, GradingListResponse
from app.utils.auth import get_current_user

router = APIRouter(prefix="/gradings", tags=["gradings"])
logger = logging.getLogger(__name__)

@router.get("", response_model=GradingListResponse)
async def get_gradings(
    limit: int = 10,
    offset: int = 0,
    student_id: Optional[str] = None,
    problem_key: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """채점 결과 목록 조회"""
    try:
        logger.info(f"채점 결과 목록 조회 - 학생: {student_id}, 문제: {problem_key}")
        
        # Eager loading으로 관련 데이터를 함께 조회
        stmt = select(Grading).options(
            joinedload(Grading.detailed_scores).joinedload(DetailedScore.detailed_criteria)
        )
        
        if student_id:
            stmt = stmt.where(Grading.student_id == student_id)
        if problem_key:
            stmt = stmt.where(Grading.problem_key == problem_key)
            
        stmt = stmt.offset(offset).limit(limit)
        result = await db.execute(stmt)
        gradings = result.unique().scalars().all()
        
        responses = []
        for grading in gradings:
            # 모델을 dict로 변환하여 필요한 필드들을 포함
            grading_dict = {
                "id": grading.id,
                "student_id": grading.student_id,
                "problem_key": grading.problem_key,
                "submission_id": grading.submission_id,
                "extraction_id": grading.extraction_id,
                "extracted_text": grading.extracted_text,
                "solution_steps": grading.solution_steps or "",  # None인 경우 빈 문자열로
                "total_score": grading.total_score,
                "max_score": grading.max_score,
                "feedback": grading.feedback,
                "grading_number": grading.grading_number,
                "image_path": grading.image_path,
                "created_at": grading.created_at,
                "detailed_scores": [
                    {
                        "id": score.id,
                        "score": score.score,
                        "feedback": score.feedback,
                        "detailed_criteria_id": score.detailed_criteria_id,
                        "criteria_info": {
                            "item": score.detailed_criteria.item,
                            "points": score.detailed_criteria.points,
                            "description": score.detailed_criteria.description
                        }
                    }
                    for score in grading.detailed_scores
                ]
            }
            responses.append(GradingResponse(**grading_dict))
            
        return responses
        
    except Exception as e:
        logger.error(f"채점 결과 목록 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))