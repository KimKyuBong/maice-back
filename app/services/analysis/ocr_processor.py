import logging
import asyncio
from typing import Optional, Dict, List, Any
from app.services.analysis.ocr_assistant import OCRAssistant
from app.services.analysis.ocr_utils import OCRUtils
import json
import re
import cv2
import numpy as np
from PIL import Image
import io
import os
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
        self.max_image_size = 2048
        self.quality = 85
        self.upload_dir = Path(settings.UPLOAD_DIR)

    async def preprocess_image(self, image_path: str) -> str:
        """이미지 전처리"""
        try:
            logger.info(f"Starting image preprocessing for: {image_path}")
            
            # 전체 경로 구성
            full_path = self.upload_dir / image_path
            logger.info(f"Full path constructed: {full_path}")
            
            if not os.path.exists(full_path):
                raise ValueError(f"Image file not found: {full_path}")

            # 이미지 로드
            image = cv2.imread(str(full_path))
            if image is None:
                raise ValueError(f"Failed to load image: {full_path}")
            logger.info(f"Image loaded successfully. Original size: {image.shape}")

            # 전처리된 이미지를 저장할 경로 생성
            processed_dir = full_path.parent / "processed"
            processed_dir.mkdir(parents=True, exist_ok=True)
            processed_path = processed_dir / f"{full_path.stem}_processed{full_path.suffix}"
            logger.info(f"Processing directory created: {processed_dir}")

            # 초기 크기 조정
            height, width = image.shape[:2]
            if max(height, width) > self.max_image_size:
                scale = self.max_image_size / max(height, width)
                new_width = int(width * scale)
                new_height = int(height * scale)
                image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
                logger.info(f"Image resized to: {new_width}x{new_height}")

            # 이미지 전처리 단계별 로깅
            logger.info("Starting image processing steps...")
            
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            logger.info("Converted to grayscale")
            
            denoised = cv2.fastNlMeansDenoising(gray, h=10)
            logger.info("Denoising completed")
            
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(denoised)
            logger.info("CLAHE enhancement applied")
            
            _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            logger.info("Otsu's thresholding completed")

            # 저장
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.quality]
            cv2.imwrite(str(processed_path), binary, encode_param)
            
            file_size = os.path.getsize(processed_path) / 1024  # KB로 변환
            logger.info(f"Processed image saved. Size: {file_size:.2f}KB, Quality: {self.quality}")
            logger.info(f"Final processed path: {processed_path}")

            return str(processed_path)

        except Exception as e:
            logger.error(f"Image preprocessing error: {str(e)}")
            raise

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
            # 이미지 전처리
            processed_path = await self.preprocess_image(image_path)
            logger.info(f"Image preprocessed and saved to: {processed_path}")
            
            # OCR Assistant를 사용하여 이미지 분석
            logger.info(f"Uploading processed file: {processed_path}")
            result = await assistant.analyze_image(processed_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise

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