from fastapi import Depends, HTTPException
from fastapi.security import APIKeyCookie
from sqlalchemy import select
from app.core.session import MemorySessionStore
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app import models
from typing import Optional

cookie_sec = APIKeyCookie(name="session_id", auto_error=False)
session_store = MemorySessionStore()

async def get_current_user(
    session_id: Optional[str] = Depends(cookie_sec),
    db: AsyncSession = Depends(get_db)
) -> models.Student:
    """현재 로그인한 사용자 정보 조회"""
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
    
    return student 