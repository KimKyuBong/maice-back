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
                "description": "Extract and structure mathematical solutions from images with precise LaTeX formatting and step-by-step breakdown.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Complete solution text with ALL mathematical expressions strictly wrapped in $$ symbols. Korean text should be preserved exactly as shown."
                        },
                        "steps": {
                            "type": "array",
                            "description": "Structured breakdown of solution steps",
                            "items": {
                                "type": "object",
                                "required": ["content", "expressions"],
                                "properties": {
                                    "content": {
                                        "type": "string",
                                        "description": "Step description in Korean with mathematical expressions wrapped in $$. Must maintain original Korean text structure."
                                    },
                                    "expressions": {
                                        "type": "array",
                                        "description": "Mathematical expressions found in this step",
                                        "items": {
                                            "type": "object",
                                            "required": ["latex"],
                                            "properties": {
                                                "latex": {
                                                    "type": "string",
                                                    "description": "Pure LaTeX expression (without $$ delimiters) using double backslashes for commands"
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "required": ["text", "steps"]
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

        CRITICAL RULES:
        1. ALL mathematical expressions MUST be wrapped in $$ symbols, NOT in \( \) or other delimiters
        2. Even single variables or numbers that are part of mathematical context must be wrapped in $$
        3. NEVER use \( \) for math expressions

        Examples of CORRECT formatting:
        - "$$n \geq 4$$인 자연수 $$n$$에 대하여"
        - "$$a_{n+1} = a_n + f(n)$$이다"
        - "$$a_4 = 2$$, $$a_5 = 5$$, $$a_6 = 9$$"

        Examples of INCORRECT formatting:
        - "\(n \geq 4\)인 자연수 n에 대하여"  ❌
        - "a_{n+1} = a_n + f(n)이다"  ❌
        - "\(a_4 = 2\)"  ❌

        WORKFLOW:
        1. Identify ALL mathematical expressions, including:
           - Equations and inequalities
           - Single variables (e.g., $$n$$, $$x$$)
           - Numbers in mathematical context
           - Function notations (e.g., $$f(n)$$)
        2. Wrap each identified expression in $$ symbols
        3. Preserve Korean text exactly as shown
        4. Structure the response in the required JSON format

        Remember: Every single mathematical symbol, variable, or expression MUST be wrapped in $$ symbols, no exceptions.
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