from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.rating import SolutionRating
from app.schemas.rating import RatingCreate, RatingStats
from typing import List
import logging

logger = logging.getLogger(__name__)

class RatingService:
    async def create_rating(
        self,
        rater_id: str,
        rating_data: RatingCreate,
        db: AsyncSession
    ) -> SolutionRating:
        """새로운 평가 생성"""
        try:
            # 이전 평가 확인
            existing_rating = await self.get_user_rating(
                rater_id, 
                rating_data.grading_id, 
                db
            )
            
            if existing_rating:
                # 기존 평가 업데이트
                existing_rating.rating_score = rating_data.rating_score
                existing_rating.comment = rating_data.comment
                rating = existing_rating
            else:
                # 새 평가 생성
                rating = SolutionRating(
                    grading_id=rating_data.grading_id,
                    rater_id=rater_id,
                    rating_score=rating_data.rating_score,
                    comment=rating_data.comment
                )
                db.add(rating)
            
            await db.commit()
            await db.refresh(rating)
            return rating
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Rating creation failed: {str(e)}")
            raise

    async def get_solution_ratings(
        self,
        grading_id: int,
        db: AsyncSession
    ) -> RatingStats:
        """특정 풀이에 대한 평가 통계"""
        try:
            # 평균 점수와 총 평가 수 조회
            stats_query = select(
                func.avg(SolutionRating.rating_score).label("average"),
                func.count(SolutionRating.id).label("total")
            ).where(SolutionRating.grading_id == grading_id)
            
            result = await db.execute(stats_query)
            stats = result.first()
            
            # 점수 분포 조회
            distribution_query = select(
                SolutionRating.rating_score,
                func.count(SolutionRating.id)
            ).where(
                SolutionRating.grading_id == grading_id
            ).group_by(SolutionRating.rating_score)
            
            distribution_result = await db.execute(distribution_query)
            distribution = {int(score): count for score, count in distribution_result}
            
            return RatingStats(
                average_score=float(stats.average) if stats.average else 0.0,
                total_ratings=stats.total,
                rating_distribution=distribution
            )
            
        except Exception as e:
            logger.error(f"Failed to get rating stats: {str(e)}")
            raise 