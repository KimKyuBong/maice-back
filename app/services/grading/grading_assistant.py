import logging
from app.services.assistant.assistant_service import AssistantService
from typing import Dict

logger = logging.getLogger(__name__)

class GradingAssistant:
    def __init__(self, assistant_service: AssistantService):
        self.assistant_service = assistant_service
        self.client = self.assistant_service.client
        self.assistant = None
        self.tools = [{
            "type": "function",
            "function": {
                "name": "process_grading",
                "description": "학생의 수학 답안을 채점하고 세부 기준별 점수와 피드백을 생성",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "total_score": {
                            "type": "number",
                            "description": "학생이 획득한 총점"
                        },
                        "max_score": {
                            "type": "number",
                            "description": "문제의 총 배점"
                        },
                        "feedback": {
                            "type": "string",
                            "description": "전체적인 채점 피드 (구체적인 개선점과 잘한 점 포함)"
                        },
                        "detailed_scores": {
                            "type": "array",
                            "description": "세부 채점 기준별 평가 결과",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "detailed_criteria_id": {
                                        "type": "integer",
                                        "description": "세부 채점 기준 ID"
                                    },
                                    "score": {
                                        "type": "number",
                                        "description": "해당 기준에서 획득한 점수"
                                    },
                                    "feedback": {
                                        "type": "string",
                                        "description": "해당 기준에 대한 구체적인 피드백"
                                    }
                                },
                                "required": ["detailed_criteria_id", "score", "feedback"]
                            }
                        }
                    },
                    "required": ["total_score", "max_score", "feedback", "detailed_scores"]
                }
            }
        }]

    async def initialize(self) -> None:
        """Grading Assistant 초기화"""
        try:
            self.assistant = await self.assistant_service.create_assistant(
                name="Grading Assistant",
                description="수학 문제 답안을 채점하는 어시스턴트입니다",
                model="gpt-4o-mini",
                temperature=0.3,
                tools=self.tools,
                instructions="""
                You are a math grading assistant that evaluates student solutions.
                
                Follow these guidelines strictly:
                1. Grade according to the provided criteria exactly
                2. Be consistent in scoring similar answers
                3. Provide specific, constructive feedback
                4. Maintain objectivity in evaluation
                5. Consider partial credit when appropriate
                6. Check mathematical accuracy carefully
                7. must be in Korean language
                
                Always justify your scoring with clear explanations.
                """
            )
            logger.info(f"Grading Assistant initialized with ID: {self.assistant.id}")
        except Exception as e:
            logger.error(f"Failed to initialize Grading assistant: {e}")
            raise

    async def create_thread(self) -> str:
        """새로운 스레드 생성"""
        thread = await self.client.beta.threads.create()
        return thread.id

    async def delete_thread(self, thread_id: str) -> None:
        """스레드 삭제"""
        try:
            await self.client.beta.threads.delete(thread_id)
            logger.info(f"Deleted thread: {thread_id}")
        except Exception as e:
            logger.error(f"Failed to delete thread {thread_id}: {e}")

    async def create_message(self, thread_id: str, content: str) -> str:
        """메시지 생성"""
        message = await self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=content
        )
        return message.id

    async def create_run(self, thread_id: str) -> str:
        """실행 생성"""
        if not self.assistant:
            await self.initialize()
        run = await self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=self.assistant.id
        )
        return run.id

    async def get_run_status(self, thread_id: str, run_id: str) -> Dict:
        """실행 상태 조회"""
        return await self.client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id
        )

    async def get_messages(self, thread_id: str):
        """메시지 목록 조회"""
        return await self.client.beta.threads.messages.list(
            thread_id=thread_id
        )

    async def submit_tool_outputs(self, thread_id: str, run_id: str, outputs: list = None):
        """도구 출력 제출"""
        await self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread_id,
            run_id=run_id,
            tool_outputs=outputs or []
        ) 