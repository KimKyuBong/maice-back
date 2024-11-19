import fitz  # PyMuPDF
import io
import base64
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv
import os

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def pdf_to_images(pdf_path):
    # PDF를 이미지로 변환
    doc = fitz.open(pdf_path)
    images = []
    for page in doc:
        pix = page.get_pixmap()
        img_data = pix.tobytes("png")
        images.append(img_data)
    return images


def image_to_json(image_data):
    try:
        img_str = base64.b64encode(image_data).decode()
        logger.info("이미지 인코딩 완료")

        prompt = """
        이 이미지는 수학 채점 기준을 포함하고 있습니다. 다음 형식으로 JSON을 생성해주세요.
        정답내용에는 수식의 모든 내용이 들어가 있어야 합니다. 여러줄로 되어있는 수식도 하나의 문자열로 다 합쳐주세요.
        왼쪽의 문항번호에 맞게 아래 내용을 작성하세요
        마크다운 형식(```json)을 포함하지 말고 순수한 JSON 형식으로만 응답해주세요:
        {
            "문항1": {
                "배점": 5,
                "정답": "정답 내용",
                "유의사항": ["유의사항1", "유의사항2"]
            }
        }
        """

        logger.info("API 요청 시작")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "순수한 JSON 형식으로만 응답하세요. 마크다운이나 다른 형식을 포함하지 마세요."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_str}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=4000
        )

        response_content = response.choices[0].message.content.strip()
        # 마크다운 형식 제거
        if response_content.startswith('```'):
            response_content = response_content.split('```')[1]
            if response_content.startswith('json'):
                response_content = response_content[4:]

        logger.info(f"정제된 응답 내용: {response_content[:200]}...")

        result = json.loads(response_content.strip())
        logger.info("JSON 파싱 성공")
        return result

    except Exception as e:
        logger.error(f"이미지 처리 중 오류 발생: {str(e)}", exc_info=True)
        return {}


def extract_json_from_pdf(pdf_path):
    images = pdf_to_images(pdf_path)
    full_json = {}

    # 모든 페이지의 결과를 하나의 JSON으로 병합
    for i, image_data in enumerate(images, 1):
        logger.info(f"\n=== 페이지 {i} 처리 시작 ===")
        page_json = image_to_json(image_data)
        logger.info(
            f"페이지 {i} JSON 결과: {json.dumps(page_json, ensure_ascii=False)[:200]}...")

        # 각 페이지의 문항들을 full_json에 병합
        for question_key, question_data in page_json.items():
            full_json[question_key] = question_data

        logger.info(f"현재까지 병합된 전체 문항 수: {len(full_json)}")

    logger.info(f"\n=== 최종 결과 ===\n문항 수: {len(full_json)}")
    logger.info(f"포함된 문항 번호: {list(full_json.keys())}")

    return full_json


def save_to_json(data, json_path='grading_criteria.json'):
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logger.info(f"\n저장된 JSON 파일 경로: {json_path}")
    logger.info(f"저장된 문항 수: {len(data)}")


if __name__ == "__main__":
    # PDF에서 JSON 추출 및 저장
    pdf_path = 'check.pdf'
    json_data = extract_json_from_pdf(pdf_path)
    save_to_json(json_data)
