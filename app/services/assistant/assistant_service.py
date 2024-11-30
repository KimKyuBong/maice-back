from typing import Dict, List, Optional, Any
import logging
from openai import AsyncOpenAI
import os
from app.services.base_service import BaseService
from app.core.config import settings
import asyncio

logger = logging.getLogger(__name__)

class AssistantService(BaseService):
    def __init__(self):
        super().__init__(settings)
        self.client = None
        self.ocr_assistant = None
        self.grading_assistant = None
        self._assistants = {}  # 캐시

    async def initialize(self):
        """서비스 초기화"""
        try:
            self.client = self._initialize_client()
            logger.info("AssistantService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AssistantService: {e}")
            raise

    def _initialize_client(self) -> AsyncOpenAI:
        """OpenAI 클라이언트 초기화"""
        try:
            client = AsyncOpenAI(
                api_key=self.settings.OPENAI_API_KEY,
                max_retries=3,
                timeout=60.0,
            )
            logger.info("OpenAI client initialized successfully")
            return client
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise

    async def create_assistant(
        self,
        name: str,
        description: str,
        model: str,
        instructions: str,
        tools: list,
        temperature: float = 0,
    ) -> Any:
        """어시스턴트 생성 또는 업데이트"""
        try:
            # 기존 어시스턴트 찾기
            assistants = await self.client.beta.assistants.list()
            existing_assistant = next(
                (a for a in assistants.data if a.name == name), 
                None
            )

            # 설정값들
            assistant_params = {
                "name": name,
                "description": description,
                "model": model,
                "instructions": instructions,
                "tools": tools,
                "temperature": temperature
            }

            if existing_assistant:
                logger.info(f"Updating existing assistant: {existing_assistant.id}")
                # 기존 어시스턴트 업데이트
                assistant = await self.client.beta.assistants.update(
                    existing_assistant.id,
                    **assistant_params
                )
            else:
                logger.info("Creating new assistant")
                # 새 어시스턴트 생성
                assistant = await self.client.beta.assistants.create(
                    **assistant_params
                )

            logger.info(f"Assistant {'updated' if existing_assistant else 'created'}: {assistant.id}")
            return assistant

        except Exception as e:
            logger.error(f"Failed to create/update assistant: {e}")
            raise

    async def delete_assistant(self, assistant_id: str):
        """Assistant 삭제"""
        try:
            await self.client.beta.assistants.delete(assistant_id)
            logger.info(f"Deleted assistant: {assistant_id}")
        except Exception as e:
            logger.error(f"Failed to delete assistant: {str(e)}")
            raise

    def get_client(self) -> AsyncOpenAI:
        """OpenAI 클라이언트 반환"""
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")
        return self.client

    async def create_thread_and_run(self, assistant_id: str, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assistant API를 통해 스레드 생성 및 실행"""
        try:
            if not self.client:
                raise RuntimeError("OpenAI client not initialized")

            # 스레드 생성
            thread = await self.client.beta.threads.create()
            logger.info(f"Created thread: {thread.id}")

            # 메시지 추가
            await asyncio.gather(
                *[
                    self.client.beta.threads.messages.create(
                        thread_id=thread.id,
                        role=message["role"],
                        content=message["content"]
                    ) for message in messages
                ]
            )
            logger.info(f"Added messages to thread: {thread.id}")

            # 실행
            run = await self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant_id
            )
            logger.info(f"Started run: {run.id}")

            # 실행 완료 대기
            while True:
                run_status = await self.client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
                if run_status.status == 'completed':
                    logger.info(f"Run completed: {run.id}")
                    break
                elif run_status.status in ['failed', 'cancelled', 'expired']:
                    error_msg = f"Run failed with status: {run_status.status}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                await asyncio.sleep(0.5)  # 대기 시간을 줄여서 더 자주 상태를 확인

            # 결과 메시지 가져오기
            messages = await self.client.beta.threads.messages.list(
                thread_id=thread.id
            )
            
            # 마지막 assistant 메시지 반환
            for message in messages.data:
                if message.role == "assistant":
                    response_content = message.content[0].text.value
                    logger.info(f"Got assistant response: {response_content[:100]}...")  # 로그는 앞부분만
                    return {"content": response_content}

            raise ValueError("No assistant response found")

        except Exception as e:
            logger.error(f"Error in create_thread_and_run: {str(e)}")
            raise
        finally:
            # 스레드 정리 (선택적)
            try:
                if thread and run_status.status == 'completed':
                    await self.client.beta.threads.delete(thread.id)
                    logger.info(f"Deleted thread: {thread.id}")
            except Exception as e:
                logger.warning(f"Failed to delete thread: {str(e)}")

    async def get_or_create_assistant(self, assistant_id: str = None):
        """Assistant 가져오기 또는 생성 (캐시 활용)"""
        if assistant_id in self._assistants:
            return self._assistants[assistant_id]
            
        # 새로운 Assistant 생성 또는 가져오기
        assistant = await self._create_or_get_assistant(assistant_id)
        self._assistants[assistant.id] = assistant
        return assistant
