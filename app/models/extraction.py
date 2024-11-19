from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import json
from ..database import Base

class TextExtraction(Base):
    __tablename__ = "text_extractions"

    id = Column(Integer, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    problem_key = Column(String, nullable=False)
    submission_id = Column(Integer, ForeignKey("student_submissions.id"), nullable=False)
    extraction_number = Column(Integer, nullable=False)
    extracted_text = Column(Text, nullable=False)
    image_path = Column(String, nullable=False)
    solution_steps = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('student_id', 'problem_key', 'extraction_number',
                        name='uix_student_problem_extraction'),
    )

    # Relationships
    student = relationship("Student", back_populates="text_extractions")
    gradings = relationship("Grading", back_populates="extraction")
    submission = relationship("StudentSubmission", back_populates="text_extractions")

    @property
    def solution_steps_json(self):
        return json.loads(self.solution_steps) if self.solution_steps else []

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "problem_key": self.problem_key,
            "submission_id": self.submission_id,
            "extraction_number": self.extraction_number,
            "extracted_text": self.extracted_text,
            "image_path": self.image_path,
            "solution_steps": json.dumps(self.solution_steps_json, ensure_ascii=False),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }