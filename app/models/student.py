from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(String, primary_key=True)
    nickname = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    gradings = relationship("Grading", back_populates="student")
    submissions = relationship("StudentSubmission", back_populates="student")
    text_extractions = relationship("TextExtraction", back_populates="student")
    given_ratings = relationship("SolutionRating", back_populates="rater") 