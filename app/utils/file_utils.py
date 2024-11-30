from pathlib import Path
from fastapi import UploadFile
from datetime import datetime
import uuid
import logging
import os

logger = logging.getLogger(__name__)

async def save_uploaded_file(
    file: UploadFile,
    student_id: str,
    problem_key: str,
    upload_dir: Path
) -> str:
    """파일 저장 및 상대 경로 반환"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        file_extension = os.path.splitext(file.filename)[1].lower()
        unique_filename = f"{timestamp}_{unique_id}{file_extension}"
        
        # 상대 경로 구성 (student_id/problem_key 폴더 아래에 저장)
        relative_path = str(Path(student_id) / problem_key / unique_filename)
        
        # 전체 경로 구성
        full_path = upload_dir / relative_path
        
        # 디렉토리 생성
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 파일 저장
        content = await file.read()
        with open(full_path, "wb") as buffer:
            buffer.write(content)
            
        return relative_path

    except Exception as e:
        logger.error(f"파일 저장 중 오류: {str(e)}")
        raise 