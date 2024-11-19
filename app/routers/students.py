import mimetypes
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Dict
import logging
from app.database import get_db
from app.schemas import StudentResponse, GradingResponse, StudentSolutions, SolutionDetail
from app import models
from collections import defaultdict
import json
import base64
from pathlib import Path
from app.core.config import settings
from app.utils.auth import get_current_user  # auth 모듈에서 현재 사용자 가져오기

router = APIRouter(prefix="/students", tags=["students"])
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[StudentResponse])
async def get_students(db: AsyncSession = Depends(get_db)):
    try:
        logger.info("학생 목록 조회 시작")
        
        # 기본 학생 정보만 조회하도록 수정
        result = await db.execute(
            select(models.Student)
            .options(selectinload(models.Student.gradings))
            .order_by(models.Student.id)
        )
        students = result.scalars().all()
        
        student_responses = []
        for student in students:
            # 간단한 요약 정보만 포함
            student_dict = {
                "id": student.id,
                "created_at": student.created_at.isoformat(),
                "gradings_count": len(student.gradings),  # 채점 수만 포함
                "latest_grading": None
            }
            
            # 가장 최근 채점 정보만 포함 (있는 경우)
            if student.gradings:
                latest = max(student.gradings, key=lambda g: g.created_at)
                student_dict["latest_grading"] = {
                    "problem_key": latest.problem_key,
                    "total_score": latest.total_score,
                    "created_at": latest.created_at.isoformat()
                }
            
            student_responses.append(student_dict)
            
        logger.info(f"학생 목록 조회 완료: {len(student_responses)}명")
        return student_responses
        
    except Exception as e:
        logger.error(f"학생 목록 조회 중 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="학생 목록을 불러오는 중 오류가 발생했습니다."
        )
    

@router.get("/{student_id}/results")
async def get_student_results(
    student_id: str,
    db: AsyncSession = Depends(get_db)
):
    """학생별 채점 결과 조회"""
    try:
        logger.info(f"학생 채점 결과 조회 시작 - 학생 ID: {student_id}")
        
        # 학생 존재 여부 확인
        student_query = select(models.Student).filter_by(id=student_id)
        result = await db.execute(student_query)
        student = result.scalar_one_or_none()
        
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # 채점 결과 조회
        query = (
            select(models.Grading)
            .options(
                selectinload(models.Grading.detailed_scores)
                .selectinload(models.DetailedScore.detailed_criteria),
                selectinload(models.Grading.grading_criteria)
                .selectinload(models.GradingCriteria.detailed_criteria)
            )
            .filter(models.Grading.student_id == student_id)
            .order_by(models.Grading.problem_key, models.Grading.created_at.desc())
        )
        
        result = await db.execute(query)
        gradings = result.scalars().all()
        
        # 결과 그룹화 및 변환
        grouped_results = defaultdict(list)
        
        for grading in gradings:
            # submission 객체 먼저 생성
            submission_dict = {
                "id": grading.id,
                "student_id": grading.student_id,
                "problem_key": grading.problem_key,
                "image_path": grading.image_path,
                "created_at": grading.created_at.isoformat(),
                "image_data": None,
                "mime_type": None,
                "file_size": 0
            }

            # 이미지 처리
            if grading.image_path:
                image_path = Path(settings.UPLOAD_DIR) / grading.image_path
                if image_path.exists():
                    try:
                        with open(image_path, "rb") as f:
                            image_data = base64.b64encode(f.read()).decode('utf-8')
                            submission_dict.update({
                                "image_data": image_data,
                                "mime_type": mimetypes.guess_type(str(image_path))[0],
                                "file_size": image_path.stat().st_size
                            })
                    except Exception as e:
                        logger.error(f"이미지 로드 실패 - {grading.image_path}: {str(e)}")

            # grading_dict 생성 (submission 포함)
            grading_dict = {
                "id": grading.id,
                "student_id": grading.student_id,
                "problem_key": grading.problem_key,
                "extracted_text": grading.extracted_text,
                "total_score": grading.total_score,
                "max_score": grading.max_score,
                "feedback": grading.feedback,
                "grading_number": grading.grading_number,
                "created_at": grading.created_at.isoformat(),
                "grading_criteria": {  # 전체 채점 기준 정보 추가
                    "id": grading.grading_criteria.id,
                    "problem_key": grading.grading_criteria.problem_key,
                    "total_points": grading.grading_criteria.total_points,
                    "correct_answer": grading.grading_criteria.correct_answer,
                    "detailed_criteria": [
                        {
                            "id": dc.id,
                            "item": dc.item,
                            "points": dc.points,
                            "description": dc.description
                        }
                        for dc in grading.grading_criteria.detailed_criteria
                    ] if grading.grading_criteria else [],
                } if grading.grading_criteria else None,
                "detailed_scores": [
                    {
                        "id": score.id,
                        "detailed_criteria_id": score.detailed_criteria_id,
                        "score": score.score,
                        "feedback": score.feedback,
                        "detailed_criteria": {  # 세부 채점 기준 정보
                            "id": score.detailed_criteria.id,
                            "item": score.detailed_criteria.item,
                            "points": score.detailed_criteria.points,
                            "description": score.detailed_criteria.description
                        } if score.detailed_criteria else None
}
                    for score in grading.detailed_scores
                ],
                "submission": submission_dict  # 미리 생성한 submission 객체 할당
            }
            
            grouped_results[grading.problem_key].append(grading_dict)
        
        logger.info(f"학생 채점 결과 조회 완료 - 문제 수: {len(grouped_results)}")
        return grouped_results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"학생 채점 결과 조회 중 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/me/results")
async def get_my_results(
    current_user: models.Student = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """로그인한 학생의 채점 결과 조회"""
    return await get_student_results(current_user.id, db)

@router.get("/me/solutions")
async def get_my_solutions(
    current_user: models.Student = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """로그인한 학생의 풀이 및 평가 내역 조회"""
    return await get_student_solutions(current_user.id, db)

# 관리자용 특정 학생 조회 엔드포인트
@router.get("/{student_id}/solutions", response_model=StudentSolutions)
async def get_student_solutions(
    student_id: str,
    current_user: models.Student = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """특정 학생의 풀이 및 평가 내역 조회 (관리자 전용)"""
    # 권한 체크
    if not current_user.is_admin and current_user.id != student_id:
        raise HTTPException(
            status_code=403,
            detail="다른 학생의 풀이를 조회할 권한이 없습니다."
        )
    
    try:
        # 학생의 모든 채점 결과 조회 (평가 정보 포함)
        query = (
            select(models.Grading)
            .options(
                selectinload(models.Grading.ratings)
            )
            .where(models.Grading.student_id == student_id)
            .order_by(models.Grading.created_at.desc())
        )
        
        result = await db.execute(query)
        gradings = result.scalars().all()
        
        solutions = []
        for grading in gradings:
            ratings = grading.ratings
            total_ratings = len(ratings)
            avg_rating = (
                sum(r.rating_score for r in ratings) / total_ratings 
                if total_ratings > 0 else None
            )
            
            # 이미지 데이터 처리
            image_data = None
            mime_type = None
            file_size = 0
            if grading.image_path:
                image_path = Path(settings.UPLOAD_DIR) / grading.image_path
                if image_path.exists():
                    try:
                        with open(image_path, "rb") as f:
                            image_data = base64.b64encode(f.read()).decode('utf-8')
                            mime_type = mimetypes.guess_type(str(image_path))[0]
                            file_size = image_path.stat().st_size
                    except Exception as e:
                        logger.error(f"이미지 로드 실패: {str(e)}")
            
            solutions.append(SolutionDetail(
                grading_id=grading.id,
                problem_key=grading.problem_key,
                submitted_at=grading.created_at,
                score=grading.total_score,
                max_score=grading.max_score,
                feedback=grading.feedback,
                extracted_text=grading.extracted_text,
                image_path=grading.image_path,
                image_data=image_data,
                mime_type=mime_type,
                file_size=file_size,
                ratings=[{
                    "rater_id": r.rater_id,
                    "score": r.rating_score,
                    "comment": r.comment,
                    "created_at": r.created_at,
                    "is_my_rating": r.rater_id == current_user.id  # 내가 작성한 평가 여부
                } for r in ratings],
                average_rating=avg_rating,
                total_ratings=total_ratings
            ))
        
        return StudentSolutions(
            student_id=student_id,
            solutions=solutions
        )
            
    except Exception as e:
        logger.error(f"학생 풀이 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))