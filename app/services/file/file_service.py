from fastapi import UploadFile
import aiofiles
import os
import logging
from datetime import datetime
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class FileService:
    def __init__(self):
        self.base_dir = settings.BASE_DIR

    async def save_file(
        self,
        student_id: str,
        problem_key: str,
        file: UploadFile
    ) -> Optional[str]:
        """파일 저장 및 경로 반환"""
        try:
            # 저장 경로 생성
            save_dir = os.path.join(self.base_dir, "uploads", student_id, problem_key)
            os.makedirs(save_dir, exist_ok=True)

            # 파일명 생성 (타임스탬프 포함)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{file.filename}"
            file_path = os.path.join(save_dir, filename)

            # 파일 저장
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)

            # DB 저장용 상대 경로 반환
            return os.path.join(student_id, problem_key, filename)

        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            return None

    async def delete_file(self, file_path: str) -> bool:
        """파일 삭제"""
        try:
            full_path = os.path.join(self.base_dir, "uploads", file_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"File deleted: {full_path}")
                return True
            else:
                logger.warning(f"File not found: {full_path}")
                return False
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return False
