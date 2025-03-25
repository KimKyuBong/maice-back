from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app import models
from typing import Optional, Dict
import uuid
import logging
from datetime import datetime
from fastapi import HTTPException
from app.utils.session import session_store  # Redis 세션 스토어 추가
from app.schemas.student import StudentUpdate

logger = logging.getLogger(__name__)

MAX_LOGIN_ATTEMPTS = 5

class AuthService:
    @staticmethod
    async def authenticate_student(
        db: AsyncSession,
        student_id: str,
        password: str
    ) -> Optional[models.Student]:
        """학생 인증"""
        try:
            stmt = select(models.Student).where(models.Student.id == student_id)
            result = await db.execute(stmt)
            student = result.scalar_one_or_none()

            if not student:
                return None

            if not student.is_active:
                raise HTTPException(
                    status_code=403,
                    detail="비활성화된 계정입니다"
                )

            if student.login_attempts >= MAX_LOGIN_ATTEMPTS:
                raise HTTPException(
                    status_code=403,
                    detail="로그인 시도 횟수를 초과했습니다"
                )

            if student.verify_password(password):
                student.reset_login_attempts()
                student.update_last_login()
                await db.commit()
                return student
            
            student.increment_login_attempts()
            await db.commit()
            return None
            
        except Exception as e:
            logger.error(f"학생 인증 중 오류 발생: {str(e)}")
            raise

    @staticmethod
    async def create_student(
        db: AsyncSession,
        student_id: str,
        password: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
    ) -> models.Student:
        """새 학생 생성"""
        try:
            student = models.Student(
                id=student_id,
                email=email,
                name=name
            )
            student.set_password(password)
            
            db.add(student)
            await db.commit()
            await db.refresh(student)
            
            return student
            
        except Exception as e:
            await db.rollback()
            logger.error(f"학생 생성 중 오류 발생: {str(e)}")
            raise

    @staticmethod
    async def get_student_by_id(
        db: AsyncSession,
        student_id: str
    ) -> Optional[models.Student]:
        """학생 ID로 조회"""
        try:
            stmt = select(models.Student).where(models.Student.id == student_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"학생 조회 중 오류 발생: {str(e)}")
            raise

    @staticmethod
    async def create_session(student: models.Student) -> tuple[str, Dict]:
        """세션 생성"""
        try:
            session_id = str(uuid.uuid4())
            session_data = {
                "student_id": student.id,
                "created_at": datetime.now().isoformat()
            }
            
            await session_store.create_session(
                session_id=session_id,
                data=session_data
            )
            
            return session_id, session_data
            
        except Exception as e:
            logger.error(f"세션 생성 중 오류 발생: {str(e)}")
            raise

    @staticmethod
    async def get_session(session_id: str) -> Optional[Dict]:
        """세션 조회"""
        try:
            return await session_store.get_session(session_id)
        except Exception as e:
            logger.error(f"세션 조회 중 오류 발생: {str(e)}")
            raise

    @staticmethod
    async def delete_session(session_id: str) -> None:
        """세션 삭제 (로그아웃)"""
        try:
            await session_store.delete_session(session_id)
        except Exception as e:
            logger.error(f"세션 삭제 중 오류 발생: {str(e)}")
            raise

    @staticmethod
    async def get_current_user(
        db: AsyncSession,
        session_id: Optional[str]
    ) -> models.Student:
        """현재 로그인한 사용자 조회"""
        if not session_id:
            raise HTTPException(
                status_code=401, 
                detail="로그인이 필요합니다"
            )
        
        # Redis에서 세션 정보 조회
        session_data = await AuthService.get_session(session_id)
        if not session_data:
            raise HTTPException(
                status_code=401,
                detail="세션이 만료되었습니다"
            )
        
        # DB에서 학생 정보 조회
        student = await AuthService.get_student_by_id(db, session_data["student_id"])
        if not student:
            # 세션은 있지만 학생 정보가 없는 경우 세션도 삭제
            await AuthService.delete_session(session_id)
            raise HTTPException(
                status_code=404,
                detail="사용자를 찾을 수 없습니다"
            )
        
        return student

    @staticmethod
    async def login(
        db: AsyncSession,
        student_id: str,
        password: str,
    ) -> tuple[models.Student, str]:
        """로그인 처리"""
        try:
            # 학생 인증 또는 생성
            student = await AuthService.authenticate_student(db, student_id, password)
            if not student:
                student = await AuthService.create_student(
                    db=db,
                    student_id=student_id,
                    password=password
                )
            
            # Redis 세션 생성
            session_id, _ = await AuthService.create_session(student)
            
            return student, session_id
            
        except Exception as e:
            logger.error(f"로그인 처리 중 오류 발생: {str(e)}")
            raise

    @staticmethod
    async def update_student(
        db: AsyncSession,
        student_id: str,
        update_data: StudentUpdate
    ) -> models.Student:
        """학생 정보 업데이트"""
        try:
            student = await AuthService.get_student_by_id(db, student_id)
            if not student:
                raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다")

            update_dict = update_data.dict(exclude_unset=True)
            if "password" in update_dict:
                student.set_password(update_dict.pop("password"))

            for key, value in update_dict.items():
                setattr(student, key, value)

            await db.commit()
            await db.refresh(student)
            return student

        except Exception as e:
            await db.rollback()
            logger.error(f"학생 정보 업데이트 중 오류 발생: {str(e)}")
            raise

    @staticmethod
    async def delete_student(
        db: AsyncSession,
        student_id: str
    ) -> bool:
        """학생 삭제"""
        try:
            student = await AuthService.get_student_by_id(db, student_id)
            if not student:
                raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다")

            await db.delete(student)
            await db.commit()
            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"학생 삭제 중 오류 발생: {str(e)}")
            raise 