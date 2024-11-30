from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Text, UUID
from sqlalchemy.orm import relationship, foreign
from datetime import datetime
from ..database import Base
from sqlalchemy.sql import func
import uuid

class DetailedScore(Base):
    __tablename__ = "detailed_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    grading_id = Column(Integer, ForeignKey("gradings.id", ondelete="CASCADE"))
    detailed_criteria_id = Column(Integer, ForeignKey("detailed_criteria.id", ondelete="CASCADE"))
    score = Column(Float, nullable=False)
    feedback = Column(String)
    
    detailed_criteria = relationship("DetailedCriteria", back_populates="detailed_scores")
    grading = relationship("Grading", back_populates="detailed_scores")

    def to_dict(self):
        if not self.detailed_criteria:  # detailed_criteria가 없는 경우 처리
            raise ValueError(f"DetailedCriteria not found for DetailedScore {self.id}")
        
        return {
            "id": self.id,
            "score": self.score,
            "feedback": self.feedback,
            "detailed_criteria_id": self.detailed_criteria_id,
            "detailed_criteria": {
                "id": self.detailed_criteria.id,
                "item": self.detailed_criteria.item,
                "points": self.detailed_criteria.points,
                "description": self.detailed_criteria.description
            }
        }

class Grading(Base):
    __tablename__ = "gradings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    problem_key = Column(String, ForeignKey("grading_criteria.problem_key", ondelete="CASCADE"), nullable=False)
    submission_id = Column(Integer, ForeignKey("student_submissions.id", ondelete="CASCADE"), nullable=False)
    extraction_id = Column(Integer, ForeignKey("text_extractions.id", ondelete="CASCADE"), nullable=False)
    extracted_text = Column(Text, nullable=False)
    solution_steps = Column(JSON, nullable=True)
    latex_expressions = Column(JSON, nullable=True)
    total_score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    feedback = Column(Text)
    grading_number = Column(Integer, nullable=False)
    image_path = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    student = relationship("Student", back_populates="gradings")
    submission = relationship("StudentSubmission", back_populates="gradings")
    extraction = relationship("TextExtraction", back_populates="gradings")
    detailed_scores = relationship("DetailedScore", back_populates="grading", cascade="all, delete-orphan")
    grading_criteria = relationship("GradingCriteria", back_populates="gradings")
    ratings = relationship("SolutionRating", back_populates="grading", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "problem_key": self.problem_key,
            "submission_id": self.submission_id,
            "extraction_id": self.extraction_id,
            "extracted_text": self.extracted_text,
            "solution_steps": self.solution_steps,
            "total_score": self.total_score,
            "max_score": self.max_score,
            "feedback": self.feedback,
            "grading_number": self.grading_number,
            "image_path": self.image_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "detailed_scores": [score.to_dict() for score in self.detailed_scores]
        }