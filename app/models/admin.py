from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Admin(Base):
    __tablename__ = "admins"

    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        """비밀번호 해싱"""
        if not password:
            raise ValueError("암호는 필수입니다")
        self.password_hash = pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        """비밀번호 검증"""
        if not password or not self.password_hash:
            return False
        return pwd_context.verify(password, self.password_hash) 