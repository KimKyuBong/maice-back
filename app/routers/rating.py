from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.rating import RatingCreate, RatingResponse, RatingStats
from app.services.rating.rating_service import RatingService
from typing import List

router = APIRouter(
    prefix="/ratings",
    tags=["ratings"]
)

@router.post("/", response_model=RatingResponse)
async def rate_solution(
    rating: RatingCreate,
    current_user_id: str,  # 인증 시스템에서 가져온 사용자 ID
    db: AsyncSession = Depends(get_db),
    rating_service: RatingService = Depends()
):
    """풀이 평가하기"""
    try:
        return await rating_service.create_rating(
            rater_id=current_user_id,
            rating_data=rating,
            db=db
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{grading_id}/stats", response_model=RatingStats)
async def get_rating_stats(
    grading_id: int,
    db: AsyncSession = Depends(get_db),
    rating_service: RatingService = Depends()
):
    """풀이 평가 통계 조회"""
    try:
        return await rating_service.get_solution_ratings(grading_id, db)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) 