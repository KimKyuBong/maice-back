from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class GradingCriteria(Base):
    __tablename__ = "grading_criteria"

    id = Column(Integer, primary_key=True, index=True)
    problem_key = Column(String, nullable=False, index=True, unique=True)
    total_points = Column(Float, nullable=False)
    correct_answer = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    
    detailed_criteria = relationship("DetailedCriteria", back_populates="grading_criteria", cascade="all, delete-orphan", lazy="joined")
    gradings = relationship("Grading", back_populates="grading_criteria", cascade="all, delete-orphan", lazy="select")

    def to_dict(self):
        return {
            "id": self.id,
            "problem_key": self.problem_key,
            "total_points": self.total_points,
            "correct_answer": self.correct_answer,
            "description": self.description,
            "detailed_criteria": [dc.to_dict() for dc in self.detailed_criteria]
        }

class DetailedCriteria(Base):
    __tablename__ = "detailed_criteria"

    id = Column(Integer, primary_key=True, index=True)
    grading_criteria_id = Column(Integer, ForeignKey("grading_criteria.id", ondelete="CASCADE"), nullable=False)
    item = Column(String, nullable=False)
    points = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    
    grading_criteria = relationship("GradingCriteria", back_populates="detailed_criteria", lazy="joined")
    detailed_scores = relationship("DetailedScore", back_populates="detailed_criteria", cascade="all, delete-orphan", lazy="select")

    def to_dict(self):
        return {
            "id": self.id,
            "item": self.item,
            "points": self.points,
            "description": self.description
        } 