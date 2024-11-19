from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # API 설정
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "MAICE"
    
    # SQLite 데이터베이스 설정
    SQLITE_DB: str = "sql_app.db"
    
    # OpenAI 설정
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_ORG_ID: Optional[str] = None
    
    # 추가 설정
    SECRET_KEY: str = "your-secret-key-here"  # 비밀 키
    ALGORITHM: str = "HS256"  # 알고리즘
    DEBUG: bool = True  # 디버그 모드
    
    # 경로 설정
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    UPLOAD_DIR: str = os.path.join(BASE_DIR, "uploads")
    
    # Redis 설정 추가
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    SESSION_EXPIRE: int = 3600  # 세션 만료 시간 (1시간)
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 설정 인스턴스 생성
settings = Settings()

# uploads 디렉토리 생성
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)