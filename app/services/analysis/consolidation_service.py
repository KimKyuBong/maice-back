from app.services.base_service import BaseService
import logging
import json
from typing import Dict, List

from app.services.assistant.assistant_service import AssistantService
from app.core.config import settings

logger = logging.getLogger(__name__)

class ConsolidationService(BaseService):
    def __init__(self):
        super().__init__(settings)

    async def consolidate_results(self, results: List[Dict]) -> Dict:
        """여러 OCR 결과를 하나로 통합"""
        if len(results) != 3:
            return self._create_error_response("Exactly 3 results are required for consolidation")

        thread = None
        try:
            thread = await self.client.beta.threads.create()
            
            # 결과 비교 요청 메시지 작성
            message_content = self._prepare_consolidation_message(results)
            
            # 메시지 전송
            await self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=[message_content]
            )

            # 실행 및 결과 처리
            run = await self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.consolidation_assistant_id
            )

            return await self._process_consolidation_result(thread.id, run.id)

        except Exception as e:
            logger.error(f"Consolidation failed: {str(e)}")
            return self._create_error_response(str(e))
        finally:
            if thread:
                try:
                    await self.client.beta.threads.delete(thread.id)
                except Exception as e:
                    logger.warning(f"Failed to delete consolidation thread: {e}")

    def _prepare_consolidation_message(self, results: List[Dict]) -> Dict:
        """통합을 위한 메시지 준비"""
        return {
            "type": "text",
            "text": f"""다음 3개의 수학 풀이 분석 결과를 비교하여 가장 정확한 하나의 결과로 합해주세요:

분석 1:
{json.dumps(results[0], ensure_ascii=False, indent=2)}

분석 2:
{json.dumps(results[1], ensure_ascii=False, indent=2)}

분석 3:
{json.dumps(results[2], ensure_ascii=False, indent=2)}

각 단계와 수식을 비교하여 가장 정확한 것을 선택하고, 오류가 있다면 수정해주세요.
결과는 반드시 JSON 형식으로 반환해주세요."""
        }

    async def _process_consolidation_result(self, thread_id: str, run_id: str) -> Dict:
        """통합 결과 처리"""
        try:
            # 실행 완료 대기
            run_status = await self._wait_for_run_completion(thread_id, run_id)
            if not run_status:
                return self._create_error_response("Consolidation run failed")

            # 결과 메시지 조회
            messages = await self.client.beta.threads.messages.list(
                thread_id=thread_id,
                order="desc",
                limit=1
            )

            if not messages.data:
                return self._create_error_response("No consolidation response received")

            # 결과 파싱
            response_text = messages.data[0].content[0].text.value
            consolidated_result = json.loads(response_text)
            
            return {
                "success": True,
                "content": consolidated_result
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse consolidation result: {e}")
            return self._create_error_response("Invalid consolidation result format")
        except Exception as e:
            logger.error(f"Error processing consolidation result: {e}")
            return self._create_error_response(str(e))