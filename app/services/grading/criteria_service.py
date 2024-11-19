from app.models.criteria import GradingCriteria
from app.schemas.criteria import DetailedCriteriaCreate
from app.services.base_service import BaseService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
import logging
from app import models
from typing import Optional, Dict, List
from app.core.config import settings

logger = logging.getLogger(__name__)

class CriteriaService(BaseService):
    def __init__(self):
        super().__init__(settings)
        self._criteria_cache = {}
        
    async def get_criteria(self, problem_key: str, db: AsyncSession):
        """문제 유형별 평가 기준 조회"""
        try:
            query = select(GradingCriteria).where(
                GradingCriteria.problem_key == problem_key
            )
            result = await db.execute(query)
            criteria = result.scalar_one_or_none()
            
            if not criteria:
                # 기본 평가 기준 반환
                return {
                    "problem_key": problem_key,
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
            logger.error(f"채점 기준 조회 중 오류: {str(e)}")
            # 에러 발생 시에도 기본 평가 기준 반환
            return {
                "problem_key": problem_key,
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

    async def create_criteria(self, 
                            problem_key: str, 
                            total_points: float,
                            correct_answer: str,
                            detailed_criteria: List[DetailedCriteriaCreate],
                            db: AsyncSession) -> models.GradingCriteria:
        """새로운 채점 기준 생성"""
        try:
            # 기존 채점 기준 확인
            existing = await db.execute(
                select(models.GradingCriteria)
                .filter(models.GradingCriteria.problem_key == problem_key)
            )
            if existing.scalar_one_or_none():
                # 이미 존재하는 경우 업데이트
                return await self.update_criteria(
                    problem_key=problem_key,
                    updates={
                        "total_points": total_points,
                        "correct_answer": correct_answer,
                        "detailed_criteria": [
                            {
                                "item": d.item,
                                "points": d.points,
                                "description": d.description
                            } for d in detailed_criteria
                        ]
                    },
                    db=db
                )
            
            # 새로운 채점 기준 생성
            criteria = models.GradingCriteria(
                problem_key=problem_key,
                total_points=total_points,
                correct_answer=correct_answer
            )
            
            db.add(criteria)
            await db.flush()
            
            # 세부 기준 추가
            for detail in detailed_criteria:
                detailed = models.DetailedCriteria(
                    grading_criteria_id=criteria.id,
                    item=detail.item,
                    points=detail.points,
                    description=detail.description
                )
                db.add(detailed)
            
            await db.commit()
            
            # 관계 데이터를 명시적으로 로드
            stmt = select(models.GradingCriteria).options(
                selectinload(models.GradingCriteria.detailed_criteria)
            ).filter_by(id=criteria.id)
            result = await db.execute(stmt)
            return result.scalar_one()
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating grading criteria: {str(e)}")
            raise

    async def update_criteria(self,
                            problem_key: str,
                            updates: Dict,
                            db: AsyncSession) -> models.GradingCriteria:
        """채점 기준 업데이트"""
        try:
            # 기존 채점 기준 조회
            criteria = await self.get_criteria(problem_key, db)
            
            # 기본 정보 업데이트
            criteria.total_points = updates["total_points"]
            criteria.correct_answer = updates["correct_answer"]
            
            # 기존 세부 기준 삭제
            await db.execute(
                delete(models.DetailedCriteria).where(
                    models.DetailedCriteria.grading_criteria_id == criteria.id
                )
            )
            
            # 새로운 세부 기준 추가
            for detail in updates["detailed_criteria"]:
                detailed = models.DetailedCriteria(
                    grading_criteria_id=criteria.id,
                    item=detail["item"],
                    points=detail["points"],
                    description=detail["description"]
                )
                db.add(detailed)
            
            await db.commit()
            await db.refresh(criteria)
            
            return criteria
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating grading criteria: {str(e)}")
            raise