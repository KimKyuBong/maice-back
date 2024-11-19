from .students import router as student_router
from .submission import router as submission_router
from .grading import router as grading_router
from .criteria import router as criteria_router
from .auth import router as auth_router
from .evaluation import router as evaluation_router

__all__ = [
    'student_router',
    'submission_router',
    'grading_router',
    'criteria_router',
    'auth_router',
    'evaluation_router'
]