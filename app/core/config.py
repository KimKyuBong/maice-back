from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache
from pathlib import Path

# 기본 디렉토리 설정
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # 기본 경로 설정
    BASE_DIR: Path = BASE_DIR
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    
    # OpenAI 설정
    OPENAI_API_KEY: str

    # 보안 설정
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    # 디버그 설정
    DEBUG: bool = True

    # Redis 설정
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_PREFIX: str = "maice:"
    
    # 세션 설정
    SESSION_EXPIRE_HOURS: int = 24
    COOKIE_SECURE: bool = False
    
    # Redis 상세 설정
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_SSL: bool = False

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "maice_user"
    POSTGRES_PASSWORD: str = "maice_password"
    POSTGRES_DB: str = "maice_db"
    POSTGRES_PORT: str = "5432"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"
        case_sensitive = True
        
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str):
            if field_name in ["BASE_DIR", "UPLOAD_DIR"]:
                return Path(raw_val)
            return raw_val

@lru_cache()
def get_settings():
    settings = Settings()
    # 업로드 디렉토리 생성
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return settings

settings = get_settings()