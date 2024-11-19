from .base import ResponseBase, TimeStampedBase
from .student import StudentBase, StudentCreate, StudentResponse
from .submission import (
    StudentSubmissionBase, 
    StudentSubmissionCreate, 
    StudentSubmissionResponse
)
from .analysis import (
    OCRResponse,
    TextExtraction,
    TextExtractionResponse,
    SolutionStep,
    Expression,
    ImageAnalysisResponse,
    ImageProcessingResponse,
    MultipleExtractionResult
)
from .criteria import (
    CriteriaInfo,
    DetailedScore,
    DetailedCriteriaBase,
    DetailedCriteriaCreate,
    DetailedCriteriaResponse,
    GradingCriteriaBase,
    GradingCriteriaCreate,
    GradingCriteriaResponse,
    GradingCriteria
)
from .grading import (
    GradingResponse,
    GradingRequest,
    GradingListResponse
)
from .evaluation import (
    StudentSolutions,
    SolutionDetail,
    RatingDetail,
    EvaluationResponse
)

# 순환 참조 해결
StudentResponse.update_forward_refs()
GradingResponse.update_forward_refs()

__all__ = [
    # Base schemas
    "ResponseBase",
    "TimeStampedBase",
    
    # Student schemas
    "StudentBase",
    "StudentCreate",
    "StudentResponse",
    
    # Submission schemas
    "StudentSubmissionBase",
    "StudentSubmissionCreate",
    "StudentSubmissionResponse",
    
    # Analysis & OCR schemas
    "OCRResponse",
    "TextExtraction",
    "TextExtractionResponse",
    "SolutionStep",
    "Expression",
    "ImageAnalysisResponse",
    "ImageProcessingResponse",
    "MultipleExtractionResult",
    
    # Criteria schemas
    "CriteriaInfo",
    "DetailedScore",
    "DetailedCriteriaBase",
    "DetailedCriteriaCreate",
    "DetailedCriteriaResponse",
    "GradingCriteriaBase",
    "GradingCriteriaCreate",
    "GradingCriteriaResponse",
    "GradingCriteria",
    
    # Grading schemas
    "GradingResponse",
    "GradingRequest",
    "GradingListResponse",
    
    # Evaluation schemas
    "StudentSolutions",
    "SolutionDetail",
    "RatingDetail",
    "EvaluationResponse"
]