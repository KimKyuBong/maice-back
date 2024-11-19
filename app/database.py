from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import QueuePool
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
import logging
from sqlalchemy import event
from sqlalchemy.engine import Engine
import asyncio
from fastapi import HTTPException

logger = logging.getLogger(__name__)

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./sql_app.db"

# SQLite 설정
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")  # 외래 키 제약 조건 활성화
    cursor.close()

# 엔진 설정
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=30,
    max_overflow=30,
    pool_timeout=30,
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args={"check_same_thread": False},  # SQLite 동시성 처리
    echo=False
)

# 세션 팩토리 생성
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

# 세마포어 및 연결 추적
_db_semaphore = asyncio.Semaphore(10)
_active_sessions: set[AsyncSession] = set()

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """비동기 세션 컨텍스트 매니저"""
    session: Optional[AsyncSession] = None
    try:
        async with _db_semaphore:
            session = async_session_maker()
            _active_sessions.add(session)
            logger.debug(f"Session created. Active sessions: {len(_active_sessions)}")
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {str(e)}", exc_info=True)
                if "database is locked" in str(e):
                    raise HTTPException(status_code=503, detail="Database is temporarily unavailable")
                raise
    finally:
        if session:
            await session.close()
            _active_sessions.remove(session)
            logger.debug(f"Session closed. Active sessions: {len(_active_sessions)}")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 의존성 주입용 데이터베이스 세션 제공자"""
    async with get_session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database operation error: {str(e)}", exc_info=True)
            raise

async def create_tables() -> None:
    """데이터베이스 테이블 생성/확인"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified successfully")
    except Exception as e:
        logger.error(f"Failed to verify database tables: {str(e)}", exc_info=True)
        raise

async def cleanup_database() -> None:
    """데이터베이스 연결 정리"""
    try:
        # 활성 세션 강제 종료
        for session in _active_sessions.copy():
            try:
                await session.close()
            except Exception as e:
                logger.warning(f"Error closing session: {e}")
        _active_sessions.clear()
        
        # 엔진 정리
        await engine.dispose()
        logger.info("Database connections cleaned up")
    except Exception as e:
        logger.error(f"Failed to cleanup database connections: {str(e)}", exc_info=True)
        raise