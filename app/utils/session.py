import redis.asyncio as redis
from typing import Optional, Dict
import json
from datetime import timedelta
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisSessionStore:
    def __init__(self):
        self.redis = redis.from_url(
            settings.REDIS_URL, 
            encoding="utf-8", 
            decode_responses=True
        )
        self.prefix = settings.REDIS_PREFIX
        self.expire_time = timedelta(hours=settings.SESSION_EXPIRE_HOURS)

    async def create_session(self, session_id: str, data: Dict) -> None:
        """세션 생성"""
        try:
            key = f"{self.prefix}session:{session_id}"
            await self.redis.setex(
                key,
                int(self.expire_time.total_seconds()),
                json.dumps(data)
            )
        except Exception as e:
            logger.error(f"세션 생성 중 오류 발생: {str(e)}")
            raise

    async def get_session(self, session_id: str) -> Optional[Dict]:
        """세션 조회"""
        try:
            key = f"{self.prefix}session:{session_id}"
            data = await self.redis.get(key)
            if data:
                # 세션 접근시마다 만료 시간 갱신
                await self.redis.expire(
                    key, 
                    int(self.expire_time.total_seconds())
                )
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"세션 조회 중 오류 발생: {str(e)}")
            raise

    async def delete_session(self, session_id: str) -> None:
        """세션 삭제"""
        try:
            key = f"{self.prefix}session:{session_id}"
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"세션 삭제 중 오류 발생: {str(e)}")
            raise

    async def cleanup(self) -> None:
        """연결 종료"""
        await self.redis.close()

# 싱글톤 인스턴스 생성
session_store = RedisSessionStore() 