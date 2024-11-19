from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class DetailedCriteria(BaseModel):
    id: int
    item: str
    points: float
    description: str

class DetailedScore(BaseModel):
    detailed_criteria_id: int
    score: float
    feedback: str

class Submission(BaseModel):
    id: int
    student_id: str
    problem_key: str
    image_path: str
    created_at: datetime

class GradingResponse(BaseModel):
    total_score: float
    max_score: float
    feedback: str
    detailed_scores: List[DetailedScore]

class GradingData(BaseModel):
    id: int
    submission_id: int
    student_id: str
    problem_key: str
    extracted_text: str
    total_score: float
    max_score: float
    feedback: str
    grading_number: int
    image_path: str
    created_at: datetime
    detailed_scores: List[DetailedScore]
    submission: Submission

class EvaluationResponse(BaseModel):
    student_id: str
    problem_key: str
    image_path: str
    extracted_text: str
    extraction_number: int
    grading_result: GradingResponse

class SolutionDetail(BaseModel):
    submitted_at: datetime
    score: float
    max_score: float
    feedback: str
    extracted_text: str
    image_path: Optional[str] = None

class StudentSolutions(BaseModel):
    problem_key: str
    submissions: List[SolutionDetail]

class RatingDetail(BaseModel):
    rating: int
    comment: str

class DetailedCriteriaInfo(BaseModel):
    item: str
    points: float
    description: str

class DetailedScoreResponse(BaseModel):
    detailed_criteria_id: int
    criteria_info: DetailedCriteriaInfo
    score: float
    feedback: str

class GradingResponse(BaseModel):
    total_score: float
    max_score: float
    feedback: str
    detailed_scores: List[DetailedScoreResponse]

class EvaluationResponse(BaseModel):
    student_id: str
    problem_key: str
    image_path: str
    extracted_text: str
    extraction_number: int
    grading_result: GradingResponse

class SolutionDetail(BaseModel):
    submitted_at: datetime
    score: float
    max_score: float
    feedback: str
    extracted_text: str
    image_path: Optional[str] = None

class StudentSolutions(BaseModel):
    problem_key: str
    submissions: List[SolutionDetail]

class RatingDetail(BaseModel):
    rating: int
    comment: str
  