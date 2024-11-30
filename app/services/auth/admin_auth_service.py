from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import logging
from app import models
from app.core.security import create_access_token

logger = logging.getLogger(__name__)

class AdminAuthService:
    @staticmethod
    async def authenticate_admin(
        db: AsyncSession,
        username: str,
        password: str
    ) -> Optional[models.Admin]:
        """어드민 인증"""
        try:
            stmt = select(models.Admin).where(models.Admin.username == username)
            result = await db.execute(stmt)
            admin = result.scalar_one_or_none()

            if admin and admin.verify_password(password):
                return admin
            return None
            
        except Exception as e:
            logger.error(f"어드민 인증 중 오류 발생: {str(e)}")
            raise

    @staticmethod
    async def get_current_admin(
        db: AsyncSession,
        session_id: Optional[str]
    ) -> models.Admin:
        """현재 로그인한 어드민 조회"""
        if not session_id:
            raise HTTPException(
                status_code=401, 
                detail="관리자 로그인이 필요합니다"
            )
        
        session_data = await AuthService.get_session(session_id)
        if not session_data or not session_data.get("is_admin"):
            raise HTTPException(
                status_code=401,
                detail="관리자 권한이 없습니다"
            )
        
        admin = await AdminAuthService.get_admin_by_id(db, session_data["admin_id"])
        if not admin:
            await AuthService.delete_session(session_id)
            raise HTTPException(
                status_code=404,
                detail="관리자를 찾을 수 없습니다"
            )
        
        return admin 