from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
import logging
import os
from pathlib import Path
from app.database import create_tables, engine, Base
from app.routers import (
    student_router,
    submission_router,
    grading_router,
    criteria_router,
    auth_router,
    evaluation_router
)
from contextlib import asynccontextmanager
from app.core.config import settings
from app.services.assistant.assistant_service import AssistantService
from app.dependencies import init_app

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 기본 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "back/uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# .env 파일 로드
load_dotenv()

async def init_db():
    """데이터베이스 초기화"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("데이터베이스 테이블 생성 완료")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 중 오류: {str(e)}")
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행되는 이벤트 핸들러"""
    try:
        await init_db()
        await init_app(app)
        logger.info("Application startup completed")
        yield
    finally:
        logger.info("Application shutdown")

# FastAPI 앱 설정
app = FastAPI(
    title="MAICE API",
    description="Math AI Correction Engine API",
    version="1.0.0",
    lifespan=lifespan,
    trailing_slash=False
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경에서는 모든 origin 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 초기화 함수 정의
def init_routers(app: FastAPI):
    """라우터 초기화"""
    app.include_router(auth_router, prefix="/api")
    app.include_router(student_router, prefix="/api")
    app.include_router(submission_router, prefix="/api")
    app.include_router(grading_router, prefix="/api")
    app.include_router(criteria_router, prefix="/api")
    app.include_router(evaluation_router, prefix="/api")

# 라우터 초기화 함수 호출
init_routers(app)

# 헬스체크 엔드포인트
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 개발 환경에서 자동 리로드 활성화
        reload_dirs=["app"]
    )