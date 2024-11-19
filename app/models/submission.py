from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

class StudentSubmission(Base):
    __tablename__ = "student_submissions"

    id = Column(Integer, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    problem_key = Column(String, nullable=False)
    file_name = Column(String)
    image_path = Column(String, nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    student = relationship("Student", back_populates="submissions")
    text_extractions = relationship("TextExtraction", back_populates="submission")
    gradings = relationship("Grading", back_populates="submission")