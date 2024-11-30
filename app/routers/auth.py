from fastapi import APIRouter, Depends, HTTPException, Response, Form
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyCookie
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app import models
from pydantic import BaseModel
import logging
from app.services.auth.auth_service import AuthService
from app.core.config import settings
from passlib.context import CryptContext

# 쿠키 설정
cookie_sec = APIKeyCookie(name="session_id", auto_error=False)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

# bcrypt 버전 경고 무시하도록 설정 변경
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # 라운드 수 명시적 설정
)

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
        student = await AuthService.get_current_user(db, session_id)
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
    student_id: str = Form(...),
    password: str = Form(...),
    response: Response = None,
    db: AsyncSession = Depends(get_db)
):
    """로그인"""
    try:
        student, session_id = await AuthService.login(db, student_id, password)
        
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            max_age=settings.SESSION_EXPIRE_HOURS * 3600,
            samesite='lax',
            secure=settings.COOKIE_SECURE
        )
        
        return {
            "status": "success",
            "message": "로그인 성공",
            "data": {
                "student_id": student.id,
                "created_at": student.created_at.isoformat() if student.created_at else None
            }
        }

    except Exception as e:
        logger.error(f"로그인 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/logout")
async def logout(
    session_id: str = Depends(cookie_sec),
    response: Response = None
):
    """로그아웃"""
    try:
        if session_id:
            await AuthService.delete_session(session_id)
        
        response = JSONResponse(content={
            "status": "success",
            "message": "로그아웃 되었습니다"
        })
        response.delete_cookie(key="session_id")
        return response
        
    except Exception as e:
        logger.error(f"로그아웃 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))