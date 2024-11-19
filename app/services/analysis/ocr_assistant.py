import asyncio
import logging
import time
import json
from typing import Optional, List, Dict, Any
from openai import AsyncOpenAI
from app.services.assistant.assistant_service import AssistantService

logger = logging.getLogger(__name__)

class OCRAssistant:
    def __init__(self, assistant_service: AssistantService):
        self.assistant_service = assistant_service
        self.client = assistant_service.get_client()
        self.assistant = None
        self.tools = self._configure_tools()

    def _configure_tools(self) -> List[Dict]:
        """OCR tools configuration"""
        return [{
            "type": "function",
            "function": {
                "name": "process_math_image",
                "description": "Extract text and mathematical expressions from Korean math solution images. All mathematical expressions MUST be wrapped in $$ symbols and use escaped backslashes (\\\\) for LaTeX commands.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Extracted Korean text where ALL mathematical expressions MUST be wrapped in $$ symbols. LaTeX commands must use double backslashes. Example: '방정식 $$\\\\frac{x^2 + 2x + 1}{2} = 0$$을 풀면...'"
                        },
                        "steps": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "content": {
                                        "type": "string",
                                        "description": "Step description in Korean. Mathematical expressions MUST be wrapped in $$ and use double backslashes for LaTeX. Example: '$$\\\\sqrt{x^2}$$ 계산'"
                                    },
                                    "expressions": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "latex": {
                                                    "type": "string",
                                                    "description": "Complete LaTeX expression using double backslashes (without $$ symbols). Example: '\\\\frac{1}{2}\\\\sqrt{x}'"
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "required": ["text"]
                }
            }
        }]

    async def initialize(self):
        """Assistant initialization"""
        try:
            self.assistant = await self.assistant_service.create_assistant(
                name="OCR Assistant",
                description="Extract text and mathematical expressions from Korean math solution images",
                model="gpt-4o-mini",
                temperature=0.2,
                tools=self.tools,
                instructions=self._get_instructions()
            )
            if not self.assistant:
                raise ValueError("Failed to create OCR assistant")
            logger.info(f"OCR Assistant initialized with ID: {self.assistant.id}")
        except Exception as e:
            logger.error(f"Failed to initialize OCR assistant: {e}")
            raise

    def _get_instructions(self) -> str:
        """Assistant instructions"""
        return """
        You are a specialized OCR assistant for Korean math solutions. Your primary task is to extract and structure content from math solution images.

        WORKFLOW:
        1. Carefully analyze the image content
        2. Extract all Korean text and mathematical expressions
        3. Structure the response in the required JSON format
        4. ALWAYS respond in Korean for text content

        RESPONSE FORMAT RULES:
        1. Mathematical Expressions:
           - Must be wrapped in $$ symbols
           - Use proper LaTeX with double backslashes
           - Example: $$\\frac{1}{2}$$, $$x + y = 5$$
           - Keep expressions in their original mathematical form

        2. Korean Text:
           - Extract all visible Korean text
           - Maintain original Korean language and meaning
           - Do not use LaTeX text commands
           - Place text naturally around equations

        3. JSON Structure:
           {
               "text": "Complete Korean text with embedded equations in $$",
               "steps": [
                   {
                       "content": "Step description in Korean with equations in $$",
                       "expressions": [
                           {"latex": "Pure LaTeX without $$"},
                           {"latex": "Pure LaTeX without $$"}
                       ]
                   }
               ]
           }

        IMPORTANT:
        - ALL text content must be in Korean
        - Only mathematical expressions should use LaTeX
        - Maintain the exact structure of the JSON format
        - Ensure all mathematical expressions are properly formatted
        - Preserve the original meaning and context of the solution

        """

    def validate_ocr_result(self, result: Dict) -> bool:
        """OCR 결과 검증"""
        if not isinstance(result, dict):
            return False
        
        if "text" not in result or not isinstance(result["text"], str):
            return False
        
        if "steps" in result and not isinstance(result["steps"], list):
            return False
        
        for step in result.get("steps", []):
            if not isinstance(step, dict):
                return False
            if "content" not in step or not isinstance(step["content"], str):
                return False
            if "expressions" in step:
                if not isinstance(step["expressions"], list):
                    return False
                for expr in step["expressions"]:
                    if not isinstance(expr, dict) or "latex" not in expr:
                        return False
        
        return True

    async def wait_for_completion(self, thread_id: str, run_id: str) -> Dict[str, Any]:
        try:
            while True:
                run_status = await self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run_id
                )
                logger.info(f"Run status: {run_status.status}")

                if run_status.status == "requires_action":
                    tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                    
                    for tool_call in tool_calls:
                        if tool_call.function.name == "process_math_image":
                            try:
                                args = json.loads(tool_call.function.arguments)
                                logger.info(f"Function call arguments: {args}")
                                # 바로 arguments 반환
                                return args
                            except json.JSONDecodeError as e:
                                logger.error(f"Invalid function arguments: {e}")
                                raise ValueError("Invalid function arguments")

                elif run_status.status in ["failed", "expired", "cancelled"]:
                    error_msg = f"Run failed with status: {run_status.status}"
                    if hasattr(run_status, 'last_error'):
                        error_msg += f", Error: {run_status.last_error}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error in wait_for_completion: {str(e)}")
            raise

    async def analyze_image(self, image_path: str) -> Dict[str, Any]:
        file_id = None
        thread_id = None
        try:
            # 1. 파일 업로드와 스레드 생성을 병렬로 처리
            upload_task = asyncio.create_task(self.client.files.create(
                file=open(image_path, "rb"),
                purpose="assistants"
            ))
            thread_task = asyncio.create_task(self.client.beta.threads.create())
            
            file, thread = await asyncio.gather(upload_task, thread_task)
            file_id = file.id
            thread_id = thread.id
            
            # 2. 메시지 생성
            await self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=[{
                    "type": "image_file",
                    "image_file": {
                        "file_id": file_id,
                        "detail": "high"
                    }
                }]
            )
            
            # 3. run 생성
            run = await self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant.id
            )
            
            # 4. 결과 대기 및 처리
            result = await self.wait_for_completion(thread_id, run.id)
            return result

        finally:
            # 리소스 정리
            try:
                if file_id:
                    await self.client.files.delete(file_id)
                if thread_id:
                    await self.client.beta.threads.delete(thread_id)
            except Exception as cleanup_error:
                logger.warning(f"Resource cleanup error: {cleanup_error}")

    async def _wait_for_run_completion(self, thread_id: str, run_id: str) -> str:
        while True:
            run = await self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )
            if run.status in ['completed', 'failed', 'requires_action']:
                return run.status
            await asyncio.sleep(0.5)  # 1초 -> 0.5초로 감소