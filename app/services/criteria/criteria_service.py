from app.models.criteria import GradingCriteria
from app.schemas.criteria import DetailedCriteriaCreate, GradingCriteriaCreate
from app.services.base_service import BaseService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, and_, update
from sqlalchemy.orm import selectinload, joinedload
import logging
from app import models
from typing import Optional, Dict, List
from app.core.config import settings
from fastapi import HTTPException
from app.database import engine  # 여기서 engine을 직접 import

logger = logging.getLogger(__name__)

class CriteriaService(BaseService):
    def __init__(self):
        """CriteriaService 초기화"""
        try:
            super().__init__(settings)
            self.engine = engine  # engine을 직접 할당
            logger.info("CriteriaService가 초기화되었습니다.")
        except Exception as e:
            logger.error(f"CriteriaService 초기화 실패: {str(e)}")
            raise
        
    async def initialize(self):
        """서비스 초기화 - 기본 채점 기준 등록"""
        db = None
        try:
            async with AsyncSession(self.engine) as db:
                # 기본 채점 기준 존재 여부 확인
                stmt = select(models.GradingCriteria).where(
                    models.GradingCriteria.problem_key == "default"
                )
                result = await db.execute(stmt)
                existing_criteria = result.unique().scalar_one_or_none()
                
                if not existing_criteria:
                    # 기본 채점 기준 생성
                    default_criteria = models.GradingCriteria(
                        problem_key="default",
                        total_points=100.0,
                        description="수열의 귀납적 정의와 수학적 귀납법"
                    )
                    db.add(default_criteria)
                    await db.flush()

                    # 기본 세부 기준 생성
                    detailed_criteria = [
                        models.DetailedCriteria(
                            grading_criteria_id=default_criteria.id,
                            item="수열의 귀납적 정의에 대한 설명(등차수열)",
                            points=10,
                            description="등차수열을 수열의 귀납적 정의를 이용해 올바르게 설명함"
                        ),
                        models.DetailedCriteria(
                            grading_criteria_id=default_criteria.id,
                            item="수열의 귀납적 정의에 대한 설명(등비수열)",
                            points=10,
                            description="등비수열을 수열의 귀납적 정의를 이용해 올바르게 설명함"
                        ),
                        models.DetailedCriteria(
                            grading_criteria_id=default_criteria.id,
                            item="수학적 귀납법의 뜻 설명",
                            points=10,
                            description="수학적 귀납법의 의미를 올바르게 설명함"
                        ),
                        models.DetailedCriteria(
                            grading_criteria_id=default_criteria.id,
                            item="귀납적으로 정의된 수열 문항(1)",
                            points=10,
                            description="귀납적으로 정의된 수열 문항에서 규칙을 올바르게 파악함"
                        ),
                        models.DetailedCriteria(
                            grading_criteria_id=default_criteria.id,
                            item="귀납적으로 정의된 수열 문항(2)",
                            points=15,
                            description="파악된 규칙을 이용하여 문제를 올바르게 해결함"
                        ),
                        models.DetailedCriteria(
                            grading_criteria_id=default_criteria.id,
                            item="수학적 귀납법 문항(1)",
                            points=10,
                            description="주어진 명제에 시작 부분을 대입하여 올바르게 증명함"
                        ),
                        models.DetailedCriteria(
                            grading_criteria_id=default_criteria.id,
                            item="수학적 귀납법 문항(2)",
                            points=15,
                            description="주어진 명제에의 연쇄적인 부분의 가정(k일때 성립가정)과 결론(k+1일때 성립)을 올바르게 작성함"
                        ),
                        models.DetailedCriteria(
                            grading_criteria_id=default_criteria.id,
                            item="수학적 귀납법 문항(3)",
                            points=10,
                            description="연쇄적인 부분의 증명을 수학적으로 올바르게 해냄"
                        ),
                        models.DetailedCriteria(
                            grading_criteria_id=default_criteria.id,
                            item="결론 작성",
                            points=10,
                            description="위에서 해결한 문항들의 결론을 올바르게 명시하여 작성함"
                        )
                    ]
                    
                    for criteria in detailed_criteria:
                        db.add(criteria)
                    
                    await db.commit()
                    logger.info("기본 채점 기준이 성공적으로 생성되었습니다.")
        except Exception as e:
            logger.error(f"기본 채점 기준 초기화 중 오류: {str(e)}")
            if db is not None:
                await db.rollback()
            raise

    async def get_criteria(self, criteria_id: int, db: AsyncSession):
        """특정 채점 기준 조회"""
        try:
            query = select(GradingCriteria).options(
                selectinload(GradingCriteria.detailed_criteria)
            ).where(GradingCriteria.id == criteria_id)
            
            result = await db.execute(query)
            criteria = result.scalar_one_or_none()
            
            if not criteria:
                raise HTTPException(status_code=404, detail="채점 기준을 찾을 수 없습니다.")
            
            return criteria
        except Exception as e:
            logger.error(f"채점 기준 조회 중 오류: {str(e)}")
            raise
            
    async def get_criteria_by_problem(self, problem_key: str, db: AsyncSession) -> dict:
        """문제 키에 해당하는 채점 기준 조회, 없으면 기본 채점 기준 반환"""
        try:
            # 1. 활성화된 채점 기준 매핑 조회
            stmt = select(models.GradingCriteria).options(
                joinedload(models.GradingCriteria.detailed_criteria)
            ).where(
                models.GradingCriteria.problem_key == problem_key
            )
            result = await db.execute(stmt)
            criteria = result.unique().scalar_one_or_none()

            # 2. 문제별 채점 기준이 없으면 기본 채점 기준 반환
            if not criteria:
                logger.info(f"문제별 채점 기준이 없어 기본 채점 기준을 사용합니다. (문제: {problem_key})")
                return await self.get_default_criteria(problem_key)

            # 3. 응답 형식으로 변환
            return {
                "problem_key": criteria.problem_key,
                "total_points": criteria.total_points,
                "detailed_criteria": [
                    {
                        "id": dc.id,
                        "item": dc.item,
                        "points": dc.points,
                        "description": dc.description
                    }
                    for dc in criteria.detailed_criteria
                ]
            }

        except Exception as e:
            logger.error(f"채점 기준 조회 실패: {str(e)}")
            raise

    async def create_criteria(
        self,
        problem_key: str,
        total_points: float,
        correct_answer: Optional[str],
        description: str,
        detailed_criteria: List[DetailedCriteriaCreate],
        db: AsyncSession
    ) -> models.GradingCriteria:
        """새로운 채점 기준 생성"""
        try:
            criteria = models.GradingCriteria(
                problem_key=problem_key,
                total_points=total_points,
                correct_answer=correct_answer,
                description=description
            )
            
            db.add(criteria)
            await db.flush()
            
            # 세부 기준 추가
            for idx, detail in enumerate(detailed_criteria):
                detailed = models.DetailedCriteria(
                    grading_criteria_id=criteria.id,
                    item=detail.item,
                    points=detail.points,
                    description=detail.description,
                    order_num=idx + 1
                )
                db.add(detailed)
            
            await db.commit()
            await db.refresh(criteria)
            
            return criteria
            
        except Exception as e:
            await db.rollback()
            logger.error(f"채점 기준 생성 중 오류: {str(e)}")
            raise

    async def assign_criteria_to_problem(
        self,
        problem_key: str,
        criteria_id: int,
        db: AsyncSession
    ):
        """문제에 채점 기준 할당"""
        try:
            # 기존 매핑 비활성화
            await db.execute(
                update(models.ProblemCriteriaMapping).where(
                    models.ProblemCriteriaMapping.problem_key == problem_key
                ).values(is_active=False)
            )
            
            # 새로운 매핑 생성
            mapping = models.ProblemCriteriaMapping(
                problem_key=problem_key,
                grading_criteria_id=criteria_id,
                is_active=True
            )
            
            db.add(mapping)
            await db.commit()
            
            return mapping
            
        except Exception as e:
            await db.rollback()
            logger.error(f"채점 기준 할당 중 오류: {str(e)}")
            raise

    async def list_criteria(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 10,
        created_by: Optional[str] = None
    ):
        """채점 기준 목록 조회"""
        try:
            query = select(GradingCriteria).options(
                selectinload(GradingCriteria.detailed_criteria)
            )
            
            if created_by:
                query = query.where(GradingCriteria.created_by == created_by)
                
            query = query.offset(skip).limit(limit)
            result = await db.execute(query)
            
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"채점 기준 목록 조회 중 오류: {str(e)}")
            raise