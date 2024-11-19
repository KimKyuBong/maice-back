import logging
import asyncio
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app import models
from app.schemas.analysis import TextExtractionResponse
from sqlalchemy.orm import joinedload, selectinload
import json

logger = logging.getLogger(__name__)

class GradingRepository:
    def __init__(self):
        self._db_semaphore = asyncio.Semaphore(5)

    async def _get_next_grading_number(
        self, 
        db: AsyncSession, 
        student_id: str, 
        problem_key: str
    ) -> int:
        """다음 채점 번호 조회"""
        result = await db.execute(
            select(func.max(models.Grading.grading_number))
            .filter_by(student_id=student_id, problem_key=problem_key)
        )
        current_number = result.scalar() or 0
        return current_number + 1

    async def verify_references(
        self, 
        db: AsyncSession, 
        student_id: str,
        problem_key: str,
        submission_id: int, 
        extraction_id: int
    ) -> dict:
        try:
            # 1. GradingCriteria 확인 및 생성 - eager loading 사용
            criteria_stmt = select(models.GradingCriteria).options(
                joinedload(models.GradingCriteria.detailed_criteria)
            ).where(
                models.GradingCriteria.problem_key == problem_key
            )
            logger.info(f"Executing criteria query for problem_key: {problem_key}")
            criteria_result = await db.execute(criteria_stmt)
            criteria = criteria_result.unique().scalar_one_or_none()
            
            logger.info(f"Found criteria: {criteria}")
            
            if not criteria:
                logger.info(f"Creating default criteria for problem_key '{problem_key}'")
                criteria = models.GradingCriteria(
                    problem_key=problem_key,
                    total_points=100.0,
                    correct_answer="",
                    description="기본 채점 기준"
                )
                db.add(criteria)
                await db.flush()
                
                detailed_criteria = [
                    models.DetailedCriteria(
                        grading_criteria_id=criteria.id,
                        item="문제 이해",
                        points=30,
                        description="문제의 정확한 이해와 해석"
                    ),
                    models.DetailedCriteria(
                        grading_criteria_id=criteria.id,
                        item="풀이 과정",
                        points=40,
                        description="논리적인 풀이 과정 전개"
                    ),
                    models.DetailedCriteria(
                        grading_criteria_id=criteria.id,
                        item="계산 정확성",
                        points=20,
                        description="수치 계산의 정확성"
                    ),
                    models.DetailedCriteria(
                        grading_criteria_id=criteria.id,
                        item="답안 표현",
                        points=10,
                        description="답안의 명확한 표현"
                    )
                ]
                db.add_all(detailed_criteria)
                await db.flush()
                
                # Refresh with eager loading
                await db.refresh(criteria, ['detailed_criteria'])
                
                # Re-query to ensure all relationships are loaded
                criteria_stmt = select(models.GradingCriteria).options(
                    joinedload(models.GradingCriteria.detailed_criteria)
                ).where(
                    models.GradingCriteria.id == criteria.id
                )
                result = await db.execute(criteria_stmt)
                criteria = result.unique().scalar_one()

            # 2. 나머지 참조 검증 - eager loading 사용
            submission_stmt = select(models.StudentSubmission).options(
                selectinload(models.StudentSubmission.gradings)
            ).where(
                models.StudentSubmission.id == submission_id
            )
            extraction_stmt = select(models.TextExtraction).options(
                selectinload(models.TextExtraction.gradings)
            ).where(
                models.TextExtraction.id == extraction_id
            )
            
            submission = await db.execute(submission_stmt)
            extraction = await db.execute(extraction_stmt)
            
            submission_result = submission.unique().scalar_one_or_none()
            extraction_result = extraction.unique().scalar_one_or_none()
            
            return {
                "submission_exists": submission_result is not None,
                "extraction_exists": extraction_result is not None,
                "submission_details": submission_result.__dict__ if submission_result else None,
                "extraction_details": extraction_result.__dict__ if extraction_result else None,
                "criteria": criteria.to_dict() if criteria else None
            }
            
        except Exception as e:
            logger.error(f"Error in verify_references: {str(e)}")
            raise

    async def create_grading(
        self,
        db: AsyncSession,
        student_id: str,
        problem_key: str,
        image_path: str,
        grading_data: dict,
        extraction: TextExtractionResponse,
        criteria: dict = None
    ) -> models.Grading:
        try:
            # 1. 참조 무결성 검증
            refs = await self.verify_references(
                db, 
                student_id=student_id,
                problem_key=problem_key,
                submission_id=extraction.submission_id,
                extraction_id=extraction.id
            )
            
            logger.info(f"Reference verification results: {refs}")
            
            if not refs["submission_exists"]:
                raise ValueError(f"Submission {extraction.submission_id} does not exist")
            if not refs["extraction_exists"]:
                raise ValueError(f"TextExtraction {extraction.id} does not exist")
            
            if (refs["extraction_details"]["submission_id"] != 
                refs["submission_details"]["id"]):
                raise ValueError(
                    f"Extraction {extraction.id} references submission "
                    f"{refs['extraction_details']['submission_id']} but expected "
                    f"{refs['submission_details']['id']}"
                )

            # 2. 다음 채점 번호 가져오기
            next_number = await self._get_next_grading_number(db, student_id, problem_key)
            
            # 3. Grading 객체 생성
            grading = models.Grading(
                student_id=student_id,
                problem_key=problem_key,
                submission_id=refs["submission_details"]["id"],
                extraction_id=refs["extraction_details"]["id"],
                extracted_text=extraction.extracted_text,
                solution_steps=json.dumps(grading_data.get("solution_steps", []), ensure_ascii=False),
                total_score=grading_data["total_score"],
                max_score=grading_data["max_score"],
                feedback=grading_data["feedback"],
                grading_number=next_number,
                image_path=image_path
            )

            try:
                db.add(grading)
                await db.flush()
            except Exception as e:
                logger.error(f"Failed to create grading: {str(e)}")
                raise

            # 4. 세부 점수 저장
            for score_data in grading_data.get("detailed_scores", []):
                detailed_score = models.DetailedScore(
                    grading_id=grading.id,
                    detailed_criteria_id=score_data["detailed_criteria_id"],
                    score=score_data["score"],
                    feedback=score_data["feedback"]
                )
                db.add(detailed_score)

            await db.flush()
            
            # Eager loading으로 관계 데이터 다시 조회
            stmt = select(models.Grading).options(
                joinedload(models.Grading.detailed_scores).joinedload(models.DetailedScore.detailed_criteria)
            ).where(models.Grading.id == grading.id)
            
            result = await db.execute(stmt)
            grading = result.unique().scalar_one()
            
            # 모든 관계가 로드되었는지 확인
            for score in grading.detailed_scores:
                if not score.detailed_criteria:
                    raise ValueError(f"DetailedCriteria not loaded for DetailedScore {score.id}")
            
            # 응답 데이터 구성
            response_data = {
                "id": grading.id,
                "student_id": grading.student_id,
                "problem_key": grading.problem_key,
                "submission_id": grading.submission_id,
                "extraction_id": grading.extraction_id,
                "extracted_text": grading.extracted_text,
                "solution_steps": grading.solution_steps or "",
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
            
            return response_data

        except Exception as e:
            logger.error(f"채점 결과 저장 중 오류: {str(e)}")
            raise

    async def get_grading(
        self, 
        db: AsyncSession, 
        grading_id: int
    ) -> Optional[models.Grading]:
        """채점 결과 조회"""
        stmt = select(models.Grading).options(
            joinedload(models.Grading.detailed_scores)
            .joinedload(models.DetailedScore.detailed_criteria)
        ).where(models.Grading.id == grading_id)
        
        result = await db.execute(stmt)
        return result.unique().scalar_one_or_none() 