from fastapi import APIRouter, Depends, HTTPException, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
import logging
from typing import Any, List, Dict
from app.database import get_db
from app.schemas import (
    GradingCriteriaCreate, 
    GradingCriteriaResponse,
    GradingCriteriaUpdate,
    GradingCriteriaClone,
    CriteriaResponse,
    GradingCriteriaListResponse
)
from app.services.criteria.criteria_service import CriteriaService
from app import models
import json
from datetime import datetime

router = APIRouter(prefix="/criteria", tags=["criteria"])
logger = logging.getLogger(__name__)

criteria_service = CriteriaService()

@router.post("/", response_model=GradingCriteriaResponse)
async def create_grading_criteria(
    criteria: GradingCriteriaCreate,
    db: AsyncSession = Depends(get_db)
):
    """채점 기준 생성"""
    try:
        logger.info(f"Received criteria data: {criteria.dict()}")
        criteria_obj = await criteria_service.create_criteria(
            problem_key=criteria.problem_key,
            total_points=criteria.total_points,
            correct_answer=criteria.correct_answer,
            detailed_criteria=criteria.detailed_criteria,
            db=db
        )
        return criteria_obj
    except Exception as e:
        error_msg = f"채점 기준 등록 중 오류 발생: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/problem/{problem_key}", response_model=GradingCriteriaResponse)
async def get_grading_criteria(
    problem_key: str,
    db: AsyncSession = Depends(get_db)
):
    """채점 기준 조회"""
    try:
        criteria = await criteria_service.get_criteria_by_problem(problem_key, db)
        if not criteria:
            return GradingCriteriaResponse(
                id=0,
                problem_key=problem_key,
                total_points=10,
                correct_answer=None,
                description="기본 채점 기준",
                created_at=datetime.utcnow(),
                detailed_criteria=[
                    {
                        "id": 0,
                        "item": "문제 이해",
                        "points": 2,
                        "description": "문제를 정확히 이해하고 필요한 정보를 파악",
                        "grading_criteria_id": 0,
                        "created_at": datetime.utcnow()
                    }
                ]
            )
        return criteria
    except Exception as e:
        logger.error(f"채점 기준 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list", response_model=GradingCriteriaListResponse)
async def list_grading_criteria(
    skip: int = 0,
    limit: int = 10,
    created_by: str = None,
    db: AsyncSession = Depends(get_db)
):
    """채점 기준 목록 조회"""
    try:
        criteria_list = await criteria_service.list_criteria(
            db=db,
            skip=skip,
            limit=limit,
            created_by=created_by
        )
        return GradingCriteriaListResponse(
            success=True,
            message="채점 기준 목록 조회 성공",
            data=criteria_list
        )
    except Exception as e:
        logger.error(f"채점 기준 목록 조회 중 오류: {str(e)}")
        return GradingCriteriaListResponse(
            success=False,
            message="채점 기준 목록 조회 실패",
            error=str(e)
        )

@router.put("/{criteria_id}", response_model=GradingCriteriaResponse)
async def update_grading_criteria(
    criteria_id: int,
    criteria_update: GradingCriteriaUpdate,
    db: AsyncSession = Depends(get_db)
):
    """채점 기준 업데이트"""
    try:
        updated = await criteria_service.update_criteria(
            criteria_id=criteria_id,
            problem_key=criteria_update.problem_key,
            total_points=criteria_update.total_points,
            correct_answer=criteria_update.correct_answer,
            description=criteria_update.description,
            detailed_criteria=criteria_update.detailed_criteria,
            db=db
        )
        return updated
    except Exception as e:
        logger.error(f"채점 기준 업데이트 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{criteria_id}")
async def delete_grading_criteria(
    criteria_id: int,
    db: AsyncSession = Depends(get_db)
):
    """채점 기준 삭제"""
    try:
        await criteria_service.delete_criteria(criteria_id, db)
        return {"message": "채점 기준이 성공적으로 삭제되었습니다."}
    except Exception as e:
        logger.error(f"채점 기준 삭제 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{criteria_id}/clone", response_model=GradingCriteriaResponse)
async def clone_grading_criteria(
    criteria_id: int,
    clone_data: GradingCriteriaClone,
    db: AsyncSession = Depends(get_db)
):
    """채점 기준 복제"""
    try:
        cloned = await criteria_service.clone_criteria(
            criteria_id=criteria_id,
            new_name=clone_data.new_name,
            created_by=clone_data.created_by,
            db=db
        )
        return cloned
    except Exception as e:
        logger.error(f"채점 기준 복제 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{criteria_id}/assign/{problem_key}")
async def assign_criteria_to_problem(
    criteria_id: int,
    problem_key: str,
    db: AsyncSession = Depends(get_db)
):
    """문제에 채점 기준 할당"""
    try:
        mapping = await criteria_service.assign_criteria_to_problem(
            problem_key=problem_key,
            criteria_id=criteria_id,
            db=db
        )
        return {"message": f"채점 기준이 문제 {problem_key}에 성공적으로 할당되었습니다."}
    except Exception as e:
        logger.error(f"채점 기준 할당 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/default", response_model=CriteriaResponse)
async def get_default_criteria(
    db: AsyncSession = Depends(get_db)
):
    """기본 채점 기준 조회"""
    try:
        # 기본 채점 기준 조회
        stmt = select(models.GradingCriteria).where(
            models.GradingCriteria.problem_key == "default"
        )
        result = await db.execute(stmt)
        criteria = result.scalar_one_or_none()
        
        if not criteria:
            raise HTTPException(
                status_code=404,
                detail="기본 채점 기준을 찾을 수 없습니다."
            )
            
        return CriteriaResponse(
            success=True,
            message="기본 채점 기준 조회 성공",
            data=criteria
        )
        
    except Exception as e:
        logger.error(f"기본 채점 기준 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
