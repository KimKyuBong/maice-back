import logging
import json
import asyncio
from typing import Dict
from app.schemas.analysis import TextExtractionResponse
from app.services.assistant.assistant_service import AssistantService
from app.services.grading.grading_assistant import GradingAssistant

logger = logging.getLogger(__name__)

class GradingProcessor:
    def __init__(self, grading_assistant: GradingAssistant):
        self.assistant = grading_assistant
        
    async def _process_run(self, thread_id: str, run_id: str, criteria: dict) -> Dict:
        """실행 결과 처리"""
        while True:
            run_status = await self.assistant.get_run_status(thread_id, run_id)
            logger.info(f"채점 실행 상태: {run_status.status}")
            
            if run_status.status == "requires_action":
                tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                for tool_call in tool_calls:
                    if tool_call.function.name == "process_grading":
                        try:
                            grading_args = json.loads(tool_call.function.arguments)
                            logger.info(f"채점 결과: {json.dumps(grading_args, ensure_ascii=False)}")
                            return grading_args
                        except json.JSONDecodeError as e:
                            logger.error(f"Function call 파싱 오류: {str(e)}")
                            raise
                
                await self.assistant.submit_tool_outputs(thread_id, run_id)
                
            elif run_status.status == "completed":
                messages = await self.assistant.get_messages(thread_id)
                for message in messages.data:
                    if message.role == "assistant":
                        # 기본 결과 구조 반환
                        return {
                            "total_score": 0,
                            "max_score": criteria.get("total_points", 100),
                            "feedback": "채점 결과를 생성할 수 없습니다.",
                            "detailed_scores": [
                                {
                                    "detailed_criteria_id": dc["id"],
                                    "score": 0,
                                    "feedback": "평가할 수 없습니다."
                                }
                                for dc in criteria["detailed_criteria"]
                            ]
                        }
                        
            elif run_status.status in ["failed", "cancelled", "expired"]:
                error_msg = f"채점 실패: {run_status.status}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
            await asyncio.sleep(1)

    async def process_grading(self, extraction: TextExtractionResponse, criteria: dict) -> Dict:
        """채점 수행 및 결과 반환"""
        try:
            logger.info(f"채점 시작 - OCR 텍스트: {extraction.extracted_text}")
            logger.info(f"채점 기준: {json.dumps(criteria, ensure_ascii=False)}")
            
            criteria_mapping = {
                dc["id"]: {
                    "item": dc["item"],
                    "points": dc["points"],
                    "description": dc["description"]
                }
                for dc in criteria["detailed_criteria"]
            }
            
            thread_id = await self.assistant.create_thread()
            try:
                await self.assistant.create_message(
                    thread_id=thread_id,
                    content=f"""
                    학생 답안:
                    {extraction.extracted_text}

                    채점 기준:
                    {json.dumps(criteria, ensure_ascii=False, indent=2)}

                    채점 기준 ID 매핑:
                    {json.dumps(criteria_mapping, ensure_ascii=False, indent=2)}

                    위 답안을 채점하고 process_grading 함수를 호출하여 결과를 반환해주세요.
                    각 세부 평가 항목별로 구체적인 피드백을 제공해주세요.
                    """
                )

                run_id = await self.assistant.create_run(thread_id)
                result = await self._process_run(thread_id, run_id, criteria)
                
                if not result:
                    raise ValueError("채점 결과가 생성되지 않았습니다.")
                    
                return result

            finally:
                await self.assistant.delete_thread(thread_id)

        except Exception as e:
            logger.error(f"채점 중 오류: {str(e)}")
            raise 