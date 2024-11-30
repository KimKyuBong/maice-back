from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings
import logging
from typing import AsyncGenerator
from fastapi import Depends

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=30,
    max_overflow=30,
    pool_timeout=30,
    pool_pre_ping=True,
    pool_recycle=1800,
    echo=False
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def init_db():
    """데이터베이스 초기화"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("데이터베이스 테이블 생성 완료")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 중 오류: {str(e)}")
        raise

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """비동기 세션 생성"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

# FastAPI dependency
get_db = get_session