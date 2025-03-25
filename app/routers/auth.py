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
from app.schemas.student import StudentUpdate, StudentResponse

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
    password: str

@router.get("/me", response_model=StudentResponse)
async def get_current_user(
    session_id: str = Depends(cookie_sec),
    db: AsyncSession = Depends(get_db)
):
    """현재 로그인한 사용자 정보 조회"""
    try:
        student = await AuthService.get_current_user(db, session_id)
        return student
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 정보 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login")
async def login(
    login_data: LoginRequest,
    response: Response = None,
    db: AsyncSession = Depends(get_db)
):
    """로그인"""
    try:
        student, session_id = await AuthService.login(
            db, 
            login_data.student_id, 
            login_data.password
        )
        
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
            "data": StudentResponse.from_orm(student)
        }

    except Exception as e:
        logger.error(f"로그인 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/logout")
async def logout(
    response: Response = None,
    session_id: str = Depends(cookie_sec)
):
    """로그아웃"""
    try:
        await AuthService.delete_session(session_id)
        response.delete_cookie(key="session_id")
        return {"status": "success", "message": "로그아웃 성공"}
    except Exception as e:
        logger.error(f"로그아웃 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/me", response_model=StudentResponse)
async def update_user(
    update_data: StudentUpdate,
    session_id: str = Depends(cookie_sec),
    db: AsyncSession = Depends(get_db)
):
    """사용자 정보 업데이트"""
    try:
        student = await AuthService.get_current_user(db, session_id)
        updated_student = await AuthService.update_student(
            db, 
            student.id, 
            update_data
        )
        return updated_student
    except Exception as e:
        logger.error(f"사용자 정보 업데이트 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/me")
async def delete_user(
    session_id: str = Depends(cookie_sec),
    db: AsyncSession = Depends(get_db)
):
    """사용자 삭제"""
    try:
        student = await AuthService.get_current_user(db, session_id)
        await AuthService.delete_student(db, student.id)
        return {"status": "success", "message": "계정이 삭제되었습니다"}
    except Exception as e:
        logger.error(f"사용자 삭제 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))