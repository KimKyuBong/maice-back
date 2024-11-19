from fastapi import APIRouter, Depends, HTTPException, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
import logging
from typing import Any, List, Dict
from app.database import get_db
from app.schemas import GradingCriteriaCreate, GradingCriteriaResponse
from app.services.grading.criteria_service import CriteriaService
from app import models
import json

router = APIRouter(prefix="/criteria", tags=["criteria"])
logger = logging.getLogger(__name__)

# CriteriaService 초기화
criteria_service = CriteriaService()

@router.post("/", response_model=GradingCriteriaResponse)
async def create_grading_criteria(
    criteria: GradingCriteriaCreate,
    db: AsyncSession = Depends(get_db)
):
    """채점 기준 생성 엔드포인트"""
    try:
        logger.info(f"Received criteria data: {criteria.dict()}")
        
        # 채점 기준 생성
        criteria_obj = await criteria_service.create_criteria(
            problem_key=criteria.problem_key,
            total_points=criteria.total_points,
            correct_answer=criteria.correct_answer,
            detailed_criteria=criteria.detailed_criteria,
            db=db
        )
        
        return criteria_obj
        
    except Exception as e:
        error_msg = f"채점 기준 등록/업데이트 중 오류 발생: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/{problem_key}", response_model=GradingCriteriaResponse)
async def get_grading_criteria(
    problem_key: str,
    db: AsyncSession = Depends(get_db)
):
    """채점 기준 조회"""
    try:
        # 데이터베이스에서 평가 기준 조회
        query = select(models.GradingCriteria).where(
            models.GradingCriteria.problem_key == problem_key
        )
        result = await db.execute(query)
        criteria = result.scalar_one_or_none()
        
        if not criteria:
            # 기본 수학 풀이 평가 기준
            return {
                "total_points": 10,
                "correct_answer": "",
                "detailed_criteria": [
                    {
                        "item": "문제 이해",
                        "points": 2,
                        "description": "문제를 정확히 이해하고 필요한 정보를 파악"
                    },
                    {
                        "item": "풀이 과정",
                        "points": 4,
                        "description": "논리적이고 단계적인 풀이 과정 전개"
                    },
                    {
                        "item": "계산 정확도",
                        "points": 2,
                        "description": "수치 계산의 정확성"
                    },
                    {
                        "item": "답안 표현",
                        "points": 2,
                        "description": "답안의 명확한 표현과 단위 표기"
                    }
                ]
            }
        
        return criteria
        
    except Exception as e:
        logger.error(f"채점 기준 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
