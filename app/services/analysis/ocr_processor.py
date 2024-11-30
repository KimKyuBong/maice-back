import logging
import asyncio
from typing import Optional, Dict, List, Any
from app.services.analysis.ocr_assistant import OCRAssistant
from app.services.analysis.ocr_utils import OCRUtils
import json
import re
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)

class OCRProcessor:
    def __init__(self, utils: OCRUtils):
        self._thread_semaphore = asyncio.Semaphore(10)
        self._batch_size = 5
        self._batch_queue = asyncio.Queue()
        self.utils = utils
        self.client = utils.client
        self.upload_dir = Path(settings.UPLOAD_DIR)

    async def process_image(
        self,
        image_path: str,
        assistant: OCRAssistant,
        student_id: str,
        problem_key: str
    ) -> Dict[str, Any]:
        """
        이미지를 처리하고 OCR 분석을 수행합니다.
        """
        try:
            # 전체 경로 구성
            full_path = self.upload_dir / image_path
            if not full_path.exists():
                raise ValueError(f"Image file not found: {full_path}")
            
            # OCR Assistant를 사용하여 이미지 분석
            logger.info(f"Analyzing image: {full_path}")
            result = await assistant.analyze_image(str(full_path))
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise

    def _convert_to_latex_format(self, text: str) -> str:
        """일반 텍스트를 LaTeX 형식으로 변환"""
        # 줄바꿈으로 분리
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            # 이미 $$ 로 감싸진 경우 건너뛰기
            if '$$' in line:
                formatted_lines.append(line)
                continue
            
            # 수식으로 판단되는 라인을 $$ 로 감싸기
            if any(char in line for char in '+-*/=√∫∑∏'):
                formatted_lines.append(f'$${line.strip()}$$')
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)

    def _parse_steps(self, content: str) -> List[Dict]:
        """OCR 결과를 단계별로 파싱"""
        try:
            steps = []
            current_step = {"step_number": 1, "content": "", "expressions": []}
            
            lines = content.split('\n')
            for line in lines:
                if '$$' in line:
                    # 수식 추출
                    expressions = re.findall(r'\$\$(.*?)\$\$', line)
                    for expr in expressions:
                        current_step["expressions"].append({"latex": expr.strip()})
                    # 수식을 제외한 텍스트 처리
                    text = re.sub(r'\$\$.*?\$\$', '', line).strip()
                    if text:
                        current_step["content"] += text + "\n"
                else:
                    current_step["content"] += line + "\n"
                    
            current_step["content"] = current_step["content"].strip()
            steps.append(current_step)
            
            return steps
            
        except Exception as e:
            logger.error(f"Error parsing steps: {e}")
            return []

    async def process_batch(self, items: list):
        """배치 처리"""
        results = []
        for item in items:
            try:
                result = await self.process_image(**item)
                results.append(result)
            except Exception as e:
                logger.error(f"Batch processing error: {str(e)}")
                continue
        return results