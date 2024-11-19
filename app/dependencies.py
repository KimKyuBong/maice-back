import logging
from typing import Optional
from fastapi import FastAPI, Depends
from app.services.assistant.assistant_service import AssistantService
from app.services.analysis.ocr_service import OCRService
from app.services.grading.grading_service import GradingService
from app.services.file.file_service import FileService
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

logger = logging.getLogger(__name__)

# 설정 로깅
logger.info(f"OPENAI_API_KEY exists: {bool(settings.OPENAI_API_KEY)}")

class Services:
    def __init__(self):
        self.assistant_service: Optional[AssistantService] = None
        self.ocr_service: Optional[OCRService] = None
        self.grading_service: Optional[GradingService] = None

services = Services()

async def init_services():
    """서비스 초기화"""
    try:
        logger.info("Initializing AssistantService...")
        services.assistant_service = AssistantService()
        await services.assistant_service.initialize()
        logger.info("AssistantService initialized successfully")

        logger.info("Initializing OCRService...")
        services.ocr_service = OCRService(services.assistant_service)
        await services.ocr_service.initialize()
        logger.info("OCR Service initialized successfully")

        logger.info("Initializing GradingService...")
        services.grading_service = GradingService(services.assistant_service)
        await services.grading_service.initialize()
        logger.info("GradingService initialized successfully")

    except Exception as e:
        logger.error(f"Error initializing services: {e}")
        raise

async def get_services() -> Services:
    """서비스 인스턴스 반환"""
    return services

async def get_assistant_service() -> AssistantService:
    """AssistantService 싱글톤 인스턴스 반환"""
    if services.assistant_service is None:
        raise RuntimeError("Services not initialized")
    return services.assistant_service

async def get_file_service():
    return FileService()

def get_ocr_service(services: Services = Depends(get_services)) -> OCRService:
    return services.ocr_service

def get_grading_service(services: Services = Depends(get_services)) -> GradingService:
    return services.grading_service

async def get_db_session():
    async with AsyncSession() as session:
        yield session

async def init_app(app: FastAPI):
    """앱 초기화"""
    try:
        await init_services()
        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Service initialization failed: {str(e)}")
        raise

