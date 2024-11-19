from datetime import datetime, timedelta
import json
from typing import Dict, Optional

class MemorySessionStore:
    def __init__(self):
        self._sessions: Dict[str, dict] = {}
        self._expiry: Dict[str, datetime] = {}
    
    async def create_session(self, session_id: str, student_data: dict, expire: int = 3600):
        """세션 생성"""
        self._sessions[session_id] = student_data
        self._expiry[session_id] = datetime.now() + timedelta(seconds=expire)
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """세션 조회"""
        if session_id not in self._sessions:
            return None
            
        if datetime.now() > self._expiry[session_id]:
            await self.delete_session(session_id)
            return None
            
        return self._sessions[session_id]
    
    async def delete_session(self, session_id: str):
        """세션 삭제"""
        self._sessions.pop(session_id, None)
        self._expiry.pop(session_id, None) 