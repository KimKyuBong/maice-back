from redis.asyncio import Redis
from typing import Optional, Dict
import json
from app.core.config import settings

class RedisSessionStore:
    def __init__(self):
        self.redis = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )

    async def create_session(self, session_id: str, data: Dict, expire: int = 3600):
        """세션 생성"""
        await self.redis.setex(
            f"session:{session_id}",
            expire,
            json.dumps(data)
        )

    async def get_session(self, session_id: str) -> Optional[Dict]:
        """세션 조회"""
        data = await self.redis.get(f"session:{session_id}")
        return json.loads(data) if data else None

    async def delete_session(self, session_id: str):
        """세션 삭제"""
        await self.redis.delete(f"session:{session_id}")

    async def cleanup(self):
        """Redis 연결 정리"""
        await self.redis.close()

session_store = RedisSessionStore() 