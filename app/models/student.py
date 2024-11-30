from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Student(Base):
    __tablename__ = "students"

    id = Column(String, primary_key=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    gradings = relationship("Grading", back_populates="student")
    submissions = relationship("StudentSubmission", back_populates="student")
    text_extractions = relationship("TextExtraction", back_populates="student")
    given_ratings = relationship("SolutionRating", back_populates="rater")

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