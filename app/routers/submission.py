from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
import asyncio
import os

from app import models
from app.database import get_db, get_session
from app.dependencies import get_ocr_service, get_grading_service
from app.models.student import Student
from app.services.analysis.ocr_service import OCRService
from app.services.grading.grading_service import GradingService
from app.utils.file_utils import save_uploaded_file
from app.core.config import settings

# 스키마 import 정리
from app.schemas.base import ResponseBase
from app.schemas.submission import (
    StudentSubmissionBase,
    StudentSubmissionCreate,
    StudentSubmissionResponse,
    SubmissionResponse
)
from app.schemas.analysis import (
    OCRResponse,
    TextExtraction,
    TextExtractionResponse
)
from app.schemas.grading import (
    GradingSummary,
    GradingRequest,
    GradingData,
    DetailedScoreResponse,
    GradingListResponse,
    DetailedCriteriaResponse
)
from app.schemas.criteria import (
    CriteriaInfo,
    DetailedScore
)

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/submission",
    tags=["submission"]
)

async def process_single_grading(
    student_id: str,
    problem_key: str,
    file_path: str,
    ocr_service: OCRService,
    grading_service: GradingService,
    attempt_number: int,
    grading_criteria: dict,
    db: AsyncSession
) -> tuple:
    try:
        async with db.begin():
            # 1. Submission 먼저 생성 (id 자동 생성)
            submission = models.StudentSubmission(
                student_id=student_id,
                problem_key=problem_key,
                image_path=file_path
            )
            db.add(submission)
            await db.flush()  # submission.id 생성됨
            
            # 2. OCR 분석 (extraction 생성, id 자동 생성)
            ocr_response = await ocr_service.analyze_image(
                image_path=file_path,
                student_id=student_id,
                problem_key=problem_key,
                submission_id=submission.id,  # 생성된 submission.id 전달
                db=db
            )
            
            # 3. 채 수행 (grading 생성, id 자동 생성)
            grading = await grading_service.create_grading(
                student_id=student_id,
                problem_key=problem_key,
                image_path=file_path,
                extraction=ocr_response,
                submission_id=submission.id,  # 생성된 submission.id 전달
                grading_criteria=grading_criteria,
                db=db
            )
            
            await db.commit()
            return [ocr_response], [grading] if grading else []
            
    except Exception as e:
        logger.error(f"처리 시도 {attempt_number} 실패: {str(e)}")
        await db.rollback()
        return [], []

@router.post("/", response_model=List[SubmissionResponse])
async def create_submission(
    student_id: str = Form(...),
    problem_key: str = Form(...),
    files: List[UploadFile] = File(...),
    ocr_service: OCRService = Depends(get_ocr_service),
    grading_service: GradingService = Depends(get_grading_service),
    db: AsyncSession = Depends(get_db)
):
    """여러 문항을 동시에 처리"""
    try:
        logger.info(f"=== 제출 처리 시작 ===")
        logger.info(f"학생 ID: {student_id}, 문항: {problem_key}")

        # 학생 확인/생성
        student = await db.get(Student, student_id)
        if not student:
            logger.info(f"새로운 학생 생성: {student_id}")
            student = Student(id=student_id)
            db.add(student)
            await db.commit()

        responses = []
        for file in files:
            problem_key = f"문항{len(responses) + 1}"
            
            # file_utils를 사용한 파일 저장
            relative_path = await save_uploaded_file(
                file=file,
                student_id=student_id,
                problem_key=problem_key,
                upload_dir=Path(settings.UPLOAD_DIR)
            )
            logger.info(f"파일 저장 완료: {relative_path}")

            # 각 파일마다 새로운 DB 세션 사용
            async with get_session() as task_db:
                result = await process_single_grading(
                    student_id=student_id,
                    problem_key=problem_key,
                    file_path=relative_path,
                    ocr_service=ocr_service,
                    grading_service=grading_service,
                    attempt_number=1,
                    grading_criteria={},
                    db=task_db
                )
                responses.append(result)
        return responses

    except Exception as e:
        logger.error(f"제출 처리 중 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch", response_model=List[SubmissionResponse])
async def create_batch_submission(
    student_id: str = Form(...),
    files: List[UploadFile] = File(...),
    ocr_service: OCRService = Depends(get_ocr_service),
    grading_service: GradingService = Depends(get_grading_service),
    db: AsyncSession = Depends(get_db)
):
    """여러 문항을 동시에 처리"""
    try:
        logger.info(f"=== 학생 {student_id}의 일괄 제출 처리 시작 ===")
        
        # 1. Assistant 초기화
        await ocr_service.initialize()
        await grading_service.initialize()
        
        # 2. 학생 확인/생성
        student = await db.get(Student, student_id)
        if not student:
            logger.info(f"새로운 학생 생성: {student_id}")
            student = Student(id=student_id)
            db.add(student)
            await db.commit()
            await db.refresh(student)
        
        all_tasks = []
        responses = []

        # 각 파일에 대해 문항 번호 부여
        for index, file in enumerate(files, start=1):
            problem_key = f"문항{index}"
            logger.info(f"처리 중: {problem_key} - {file.filename}")
            
            # file_utils를 사용한 파일 저장
            relative_path = await save_uploaded_file(
                file=file,
                student_id=student_id,
                problem_key=problem_key,
                upload_dir=Path(settings.UPLOAD_DIR)
            )

            # 새로운 DB 세션 생성
            async with get_session() as task_db:
                task = process_single_grading(
                    student_id=student_id,
                    problem_key=problem_key,
                    file_path=relative_path,
                    ocr_service=ocr_service,
                    grading_service=grading_service,
                    attempt_number=1,
                    grading_criteria={},
                    db=task_db
                )
                all_tasks.append((problem_key, task))

        # 모든 태스크 동시 실행
        all_results = await asyncio.gather(*(task for _, task in all_tasks), return_exceptions=True)

        # 결과 정리
        for (problem_key, _), result in zip(all_tasks, all_results):
            if isinstance(result, Exception):
                logger.error(f"{problem_key} 처리 중 오류 발생: {str(result)}")
                responses.append(SubmissionResponse(
                    success=False,
                    message=f"{problem_key} 처리 패",
                    data={"extractions": [], "gradings": []}
                ))
            else:
                extractions, gradings = result
                responses.append(SubmissionResponse(
                    success=True,
                    message=f"{problem_key} 처리 완료",
                    data={
                        "extractions": extractions,
                        "gradings": gradings
                    }
                ))
                logger.info(f"{problem_key} 처리 결과 - 추출: {len(extractions)}개, 채점: {len(gradings)}개")

        return responses

    except Exception as e:
        logger.error(f"일괄 제출 처리 중 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def get_ocr_result(submission_id: int, db: AsyncSession) -> Optional[TextExtraction]:
    """OCR 결과 조회"""
    stmt = select(TextExtraction).where(TextExtraction.submission_id == submission_id)
    result = await db.execute(stmt)
    extraction = result.scalar_one_or_none()
    if not extraction:
        raise HTTPException(status_code=404, detail="OCR 결과를 찾을 수 없습니다.")
    return extraction

@router.post("/ocr", response_model=OCRResponse)
async def extract_text(
    solution_image: UploadFile = File(...),
    student_id: str = Form(...),
    problem_key: str = Form(...),
    db: AsyncSession = Depends(get_db),
    ocr_service: OCRService = Depends(get_ocr_service)
) -> OCRResponse:
    """이미지에서 텍스트 추출"""
    try:
        logger.info(f"OCR 요청 시작 - 학생: {student_id}, 문제: {problem_key}")
        
        # 1. 파일 저장
        relative_path = await save_uploaded_file(
            file=solution_image,
            student_id=student_id,
            problem_key=problem_key,
            upload_dir=Path(settings.UPLOAD_DIR)
        )
        full_path = os.path.join(settings.UPLOAD_DIR, relative_path)
        
        # 2. Submission 생성
        submission = models.StudentSubmission(
            student_id=student_id,
            problem_key=problem_key,
            file_name=solution_image.filename,
            image_path=str(relative_path),
            file_size=os.path.getsize(full_path),
            mime_type=solution_image.content_type
        )
        db.add(submission)
        await db.flush()
        logger.info(f"Submission 생성 완료 - ID: {submission.id}")

        # 3. OCR 분석
        extraction = await ocr_service.analyze_image(
            student_id=student_id,
            image_path=str(relative_path),
            problem_key=problem_key,
            submission_id=submission.id,
            db=db
        )
        
        await db.commit()
        logger.info(f"OCR 처리 완료 - Submission ID: {submission.id}")
        
        return OCRResponse(
            success=True,
            message="텍스트 추출 성공",
            data={
                "submission_id": submission.id,
                "extracted_text": extraction.extracted_text,
                "problem_key": problem_key,
                "student_id": student_id
            }
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"OCR 처리 중 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/grade/{submission_id}", response_model=GradingSummary)
async def process_grading(
    submission_id: int,
    request: GradingRequest,
    db: AsyncSession = Depends(get_db),
    ocr_service: OCRService = Depends(get_ocr_service),
    grading_service: GradingService = Depends(get_grading_service)
) -> GradingSummary:
    try:
        async with db.begin():
            # Submission 조회
            stmt = select(models.StudentSubmission).where(
                models.StudentSubmission.id == submission_id
            )
            result = await db.execute(stmt)
            submission = result.scalar_one_or_none()
            
            if not submission:
                logger.error(f"Submission을 찾을 수 없음 (ID: {submission_id})")
                raise HTTPException(
                    status_code=404, 
                    detail=f"제출물을 찾을 수 없습니다. (ID: {submission_id})"
                )

            # OCR 결과 조회
            stmt = select(models.TextExtraction).where(
                models.TextExtraction.submission_id == submission_id
            )
            result = await db.execute(stmt)
            ocr_result = result.scalar_one_or_none()
            
            if not ocr_result:
                logger.error(f"OCR 결과를 찾을 수 없음 (Submission ID: {submission_id})")
                raise HTTPException(
                    status_code=404, 
                    detail=f"OCR 결과를 찾을 수 없습니다. (Submission ID: {submission_id})"
                )

            if request.edited_text:
                ocr_result.extracted_text = request.edited_text
                db.add(ocr_result)

            # 채점 수행
            grading = await grading_service.create_grading(
                db=db,
                student_id=ocr_result.student_id,
                problem_key=ocr_result.problem_key,
                image_path=ocr_result.image_path,
                grading_data={},
                extraction=ocr_result
            )
            
            # 관계 데이터를 명시적으로 로드
            stmt = select(models.Grading).options(
                joinedload(models.Grading.detailed_scores)
                .joinedload(models.DetailedScore.detailed_criteria)
            ).where(models.Grading.id == grading.id)
            
            result = await db.execute(stmt)
            grading = result.unique().scalar_one()
            
            # 응답 데이터 구성
            detailed_scores = [
                DetailedScoreResponse(
                    detailed_criteria_id=score.detailed_criteria_id,
                    score=score.score,
                    feedback=score.feedback,
                    detailed_criteria=DetailedCriteriaResponse(
                        id=score.detailed_criteria.id,
                        item=score.detailed_criteria.item,
                        points=score.detailed_criteria.points,
                        description=score.detailed_criteria.description
                    )
                )
                for score in grading.detailed_scores
            ]

            return GradingSummary(
                success=True,
                message="채점이 완료되었습니다",
                data=GradingData(
                    id=grading.id,
                    student_id=grading.student_id,
                    problem_key=grading.problem_key,
                    total_score=grading.total_score,
                    max_score=grading.max_score,
                    feedback=grading.feedback,
                    created_at=grading.created_at,
                    detailed_scores=detailed_scores
                )
            )
            
            await db.commit()
            return response

    except Exception as e:
        logger.error(f"채점 중 오류 발생: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"채점 처리 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/gradings")
async def get_gradings(
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    try:
        logger.info(f"=== 채점 이력 조회 시작 ===")
        logger.info(f"Limit: {limit}, Offset: {offset}")

        # 채점 결과 조회
        stmt = (
            select(models.Grading)
            .options(
                joinedload(models.Grading.detailed_scores)
                .joinedload(models.DetailedScore.detailed_criteria)
            )
            .order_by(models.Grading.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        
        result = await db.execute(stmt)
        gradings = result.unique().scalars().all()
        
        # 전체 개수 조회
        total_count = await db.scalar(
            select(func.count()).select_from(models.Grading)
        )
        
        logger.info(f"조회된 채점 결과: {len(gradings)}개")
        
        # SQLAlchemy 모델을 Pydantic 모델로 변환
        grading_responses = []
        for grading in gradings:
            grading_dict = {
                "id": grading.id,
                "student_id": grading.student_id,
                "problem_key": grading.problem_key,
                "submission_id": grading.submission_id,
                "extraction_id": grading.extraction_id,
                "extracted_text": grading.extracted_text,
                "total_score": grading.total_score,
                "max_score": grading.max_score,
                "feedback": grading.feedback,
                "grading_number": grading.grading_number,
                "image_path": grading.image_path,
                "created_at": grading.created_at,
                "detailed_scores": [
                    {
                        "detailed_criteria_id": score.detailed_criteria_id,
                        "score": score.score,
                        "feedback": score.feedback,
                        "detailed_criteria": {
                            "item": score.detailed_criteria.item,
                            "description": score.detailed_criteria.description,
                            "points": score.detailed_criteria.points
                        }
                    }
                    for score in grading.detailed_scores
                ]
            }
            grading_responses.append(GradingSummary(**grading_dict))
        
        return GradingListResponse(
            items=grading_responses,
            total=total_count,
            limit=limit,
            offset=offset
        )

    except Exception as e:
        logger.error(f"채점 이력 조회 중 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"채점 이력 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/gradings/{grading_id}")
async def get_grading_detail(
    grading_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        logger.info(f"=== 채점 결과 상세 조회 시작 ===")
        logger.info(f"채점 ID: {grading_id}")

        # 채점 결과 조회
        stmt = (
            select(models.Grading)
            .options(
                joinedload(models.Grading.detailed_scores)
                .joinedload(models.DetailedScore.detailed_criteria)
            )
            .where(models.Grading.id == grading_id)
        )
        
        result = await db.execute(stmt)
        grading = result.unique().scalar_one_or_none()
        
        if not grading:
            logger.error(f"채점 결과를 찾을 수 없음 (ID: {grading_id})")
            raise HTTPException(
                status_code=404,
                detail=f"채점 결과를 찾을 수 없습니다. (ID: {grading_id})"
            )
        
        # SQLAlchemy 모델을 Pydantic 모델로 변환
        grading_dict = {
            "id": grading.id,
            "student_id": grading.student_id,
            "problem_key": grading.problem_key,
            "submission_id": grading.submission_id,
            "extraction_id": grading.extraction_id,
            "extracted_text": grading.extracted_text,
            "total_score": grading.total_score,
            "max_score": grading.max_score,
            "feedback": grading.feedback,
            "grading_number": grading.grading_number,
            "image_path": grading.image_path,
            "created_at": grading.created_at,
            "detailed_scores": [
                {
                    "detailed_criteria_id": score.detailed_criteria_id,
                    "score": score.score,
                    "feedback": score.feedback,
                    "detailed_criteria": {
                        "item": score.detailed_criteria.item,
                        "description": score.detailed_criteria.description,
                        "points": score.detailed_criteria.points
                    }
                }
                for score in grading.detailed_scores
            ]
        }
        
        return GradingSummary(
            success=True,
            message="채점 결과 조회 성공",
            data=grading_dict
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"채점 결과 조회 중 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"채점 결과 조회 중 오류가 발생했습니다: {str(e)}"
        )