from fastapi import APIRouter, Depends, HTTPException, Response, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.utils.auth import session_store, cookie_sec
from app import models
from pydantic import BaseModel
import uuid
from datetime import datetime
import logging

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

# 로그인 요청 모델 추가
class LoginRequest(BaseModel):
    student_id: str

@router.get("/me")
async def get_current_user(
    session_id: str = Depends(cookie_sec),
    db: AsyncSession = Depends(get_db)
):
    """현재 로그인한 사용자 정보 조회"""
    try:
        if not session_id:
            raise HTTPException(
                status_code=401, 
                detail="로그인이 필요합니다"
            )
        
        # 세션에서 사용자 정보 조회
        session_data = await session_store.get_session(session_id)
        if not session_data:
            raise HTTPException(
                status_code=401,
                detail="세션이 만료되었습니다"
            )
        
        # DB에서 학생 정보 조회
        stmt = select(models.Student).where(models.Student.id == session_data["student_id"])
        result = await db.execute(stmt)
        student = result.scalar_one_or_none()
        
        if not student:
            raise HTTPException(
                status_code=404,
                detail="사용자를 찾을 수 없습니다"
            )
        
        return {
            "status": "success",
            "data": {
                "student_id": student.id,
                "created_at": student.created_at.isoformat() if student.created_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 정보 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login")
async def login(
    student_id: str = Form(None),
    nickname: str = Form(None),
    response: Response = None,
    db: AsyncSession = Depends(get_db)
):
    """로그인"""
    try:
        if not student_id and not nickname:
            raise HTTPException(
                status_code=400,
                detail="student_id 또는 nickname이 필요합니다"
            )

        # 학생 정보 확인 로직
        query = select(models.Student)
        if student_id:
            query = query.where(models.Student.id == student_id)
        elif nickname:
            query = query.where(models.Student.nickname == nickname)

        result = await db.execute(query)
        student = result.scalar_one_or_none()
        
        if not student:
            # 학생이 없으면 새로 생성
            student = models.Student(
                id=student_id if student_id else str(uuid.uuid4()),
                nickname=nickname if nickname else student_id
            )
            db.add(student)
            await db.commit()
            await db.refresh(student)
        
        # 세션 생성
        session_id = str(uuid.uuid4())
        await session_store.create_session(
            session_id=session_id,
            student_data={
                "student_id": student.id,
                "nickname": student.nickname,
                "created_at": datetime.now().isoformat()
            }
        )
        
        # 쿠키 설정
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            max_age=3600,
            samesite='lax'
        )
        
        return {
            "status": "success",
            "message": "로그인 성공",
            "data": {
                "student_id": student.id,
                "nickname": student.nickname,
                "created_at": student.created_at.isoformat() if student.created_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"로그인 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/logout")
async def logout(response: Response):
    """로그아웃"""
    response = JSONResponse(content={
        "status": "success",
        "message": "로그아웃 되었습니다"
    })
    response.delete_cookie(key="session_id")
    return response