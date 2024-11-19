from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class SolutionRating(Base):
    __tablename__ = "solution_ratings"

    id = Column(Integer, primary_key=True, index=True)
    grading_id = Column(Integer, ForeignKey("gradings.id"), nullable=False)
    rater_id = Column(String, ForeignKey("students.id"), nullable=False)
    rating_score = Column(Float, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    grading = relationship("Grading", back_populates="ratings")
    rater = relationship("Student", back_populates="given_ratings")