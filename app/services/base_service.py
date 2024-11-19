from openai import AsyncOpenAI
import os
import logging
from typing import Optional, Dict, Any
from app.core.config import Settings

logger = logging.getLogger(__name__)

class BaseService:
    def __init__(self, settings: Settings):
        self.settings = settings
        if not self.settings.OPENAI_API_KEY:
            logger.error("OPENAI_API_KEY not found in settings")
            raise ValueError("OPENAI_API_KEY not found in settings")
            
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is not set")
            
            self.client = AsyncOpenAI(api_key=api_key)
            self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
        except Exception as e:
            logger.error(f"Failed to initialize BaseService: {e}")
            raise

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        logger.error(f"Error: {error_message}")
        return {
            "success": False,
            "error": error_message
        }

    async def _delete_file_safely(self, file_id: Optional[str]) -> bool:
        if not file_id:
            return True
            
        try:
            await self.client.files.delete(file_id)
            logger.info(f"Successfully deleted file: {file_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete file {file_id}: {e}")
            return False

    def _get_full_path(self, relative_path: str) -> str:
        """상대 경로를 절대 경로로 변환"""
        return os.path.join(self.base_dir, "uploads", relative_path)