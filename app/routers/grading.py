from fastapi import APIRouter, Depends, HTTPException, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload, joinedload
from typing import List, Optional
import logging
from app.database import get_db
from app import models
from app.schemas import (
    GradingListResponse, 
    GradingSummary,
    GradingDetailResponse,  # 상세 조회용 응답 스키마 추가
    GradingListData
)
from app.services.grading.grading_service import GradingService
from app.services.assistant.assistant_service import AssistantService  # 추가
from pathlib import Path
import base64
from app.core.config import settings  # 상단에 import 추가
from app.services.grading.grading_repository import GradingRepository
from app.services.auth.auth_service import AuthService  # AuthService 추가

router = APIRouter(prefix="/gradings", tags=["gradings"])
logger = logging.getLogger(__name__)

# 서비스 인스턴스 생성
grading_repository = GradingRepository()  # 리포지토리 인스턴스 생성
assistant_service = AssistantService()
grading_service = GradingService(
    repository=grading_repository,
    assistant_service=assistant_service
)

@router.get("/list", response_model=GradingListResponse)
async def get_gradings(
    session_id: Optional[str] = Cookie(None),
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """채점 이력 조회"""
    try:
        # 현재 로그인한 사용자 검증
        current_student = await AuthService.get_current_user(db, session_id)
        
        logger.info("=== 채점 이력 조회 시작 ===")
        logger.info(f"학생 ID: {current_student.id}, Limit: {limit}, Offset: {skip}")
        
        result = await grading_service.get_gradings(
            db=db,
            student_id=current_student.id,  # 세션에서 가져온 학생 ID 사용
            skip=skip,
            limit=limit
        )
        
        return GradingListResponse(
            success=True,
            message="채점 이력 조회 성공",
            data=GradingListData(**result)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"채점 이력 조회 중 오류 발생: {str(e)}")
        return GradingListResponse(
            success=False,
            message="채점 이력 조회 실패",
            error=str(e),
            data=GradingListData(
                items=[],
                total=0,
                limit=limit,
                offset=skip
            )
        )

@router.get("/{grading_id}", response_model=GradingDetailResponse)
async def get_grading_detail(
    grading_id: int,
    session_id: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db)
):
    """채점 결과 상세 조회"""
    try:
        # 현재 로그인한 사용자 검증
        current_student = await AuthService.get_current_user(db, session_id)
        
        logger.info(f"=== 채점 결과 상세 조회 시작 ===")
        logger.info(f"채점 ID: {grading_id}, 요청 학생 ID: {current_student.id}")

        grading = await grading_service.get_grading_detail(db, grading_id)
        
        # 채점 결과가 존재하지 않는 경우
        if not grading:
            raise HTTPException(
                status_code=404,
                detail="채점 결과를 찾을 수 없습니다"
            )
        
        # 채점 결과의 소유자 확인
        if grading.student_id != current_student.id:
            raise HTTPException(
                status_code=403,
                detail="다른 학생의 채점 결과를 조회할 수 없습니다"
            )
        
        # 이미지 파일 읽기
        image_data = None
        if grading.image_path:
            try:
                image_path = Path(settings.UPLOAD_DIR) / grading.image_path
                logger.info(f"이미지 경로: {image_path}")
                
                if image_path.exists():
                    with open(image_path, "rb") as f:
                        image_data = base64.b64encode(f.read()).decode()
                        logger.info("이미지 데이터 로드 성공")
                else:
                    logger.warning(f"이미지 파일을 찾을 수 없습니다: {image_path}")
            except Exception as e:
                logger.error(f"이미지 로딩 중 오류 발생: {str(e)}")

        # 응답 데이터 구성
        grading_data = {
            "id": grading.id,
            "student_id": grading.student_id,
            "problem_key": grading.problem_key,
            "total_score": grading.total_score,
            "max_score": grading.max_score,
            "feedback": grading.feedback,
            "created_at": grading.created_at,
            "detailed_scores": grading.detailed_scores,
            "extracted_text": grading.extracted_text,
            "image_data": image_data,
            "image_path": grading.image_path
        }
        
        return GradingDetailResponse(
            success=True,
            message="채점 결과 조회 성공",
            data=grading_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"채점 결과 조회 중 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"채점 결과 조회 중 오류가 발생했습니다: {str(e)}"
        )