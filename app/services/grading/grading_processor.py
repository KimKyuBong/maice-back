import logging
import json
import asyncio
from typing import Dict
from app.schemas.analysis import TextExtraction
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

    async def process_grading(self, extraction: TextExtraction, criteria: dict) -> Dict:
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
                    You are a mathematics grading expert. Please grade the following student's answer according to the given criteria,
                    and make sure to return the results using the process_grading function.
                    IMPORTANT: Please provide all feedback messages in Korean.

                    [Student's Answer]
                    {extraction.extracted_text}

                    [Grading Criteria]
                    Total Points: {criteria['total_points']} points
                    {criteria.get('description', '')}
                    Correct Answer: {criteria.get('correct_answer', 'Not provided')}

                    [Detailed Grading Criteria]
                    {json.dumps(criteria_mapping, ensure_ascii=False, indent=2)}

                    Please consider the following when grading:
                    1. Partial points can be awarded for each detailed criterion
                    2. Provide specific feedback in Korean (strengths and areas for improvement)
                    3. Evaluate the solution process and logical reasoning
                    4. Assess mathematical accuracy and clarity of expression

                    Key Instructions:
                    - Analyze each step of the student's solution
                    - Consider both the process and the final answer
                    - Award points based on demonstrated understanding
                    - Provide constructive and specific feedback in Korean
                    - Include suggestions for improvement where needed

                    You MUST use the process_grading function to return the results with:
                    - total_score: The actual points earned
                    - max_score: The total possible points
                    - feedback: Overall evaluation with specific comments (in Korean)
                    - detailed_scores: Array of scores and feedback for each criterion (feedback in Korean)

                    Remember: All feedback messages must be written in Korean for better understanding by Korean students and teachers.
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