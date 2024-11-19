from pathlib import Path
from fastapi import UploadFile
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

async def save_uploaded_file(
    file: UploadFile,
    student_id: str,
    problem_type: str,
    upload_dir: Path
) -> str:
    """업로드된 파일을 저장하고 상대 경로를 반환"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        file_extension = Path(file.filename).suffix.lower()
        unique_filename = f"{timestamp}_{unique_id}{file_extension}"
        
        relative_path = str(Path(student_id) / problem_type / unique_filename)
        full_path = upload_dir / relative_path
        
        full_path.parent.mkdir(parents=True, exist_ok=True)
        content = await file.read()
        
        with open(full_path, "wb") as buffer:
            buffer.write(content)
            
        return relative_path
        
    except Exception as e:
        logger.error(f"File save error: {str(e)}")
        raise 