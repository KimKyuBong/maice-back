from asyncio.log import logger
import aiohttp
import asyncio
import json
import os
from typing import Dict, Any, List, Tuple
from pathlib import Path
import re


class GradingAPITester:
    def __init__(self, base_url: str = "http://localhost:8000/api"):
        self.base_url = base_url.rstrip('/')
        self.criteria = self.load_grading_criteria()
        
    def load_grading_criteria(self, path: str = 'grading_criteria.json') -> Dict:
        """채점 기준 로드"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading grading criteria: {e}")
            return {}
        
    async def submit_solution(self, image_path: str, problem_key: str, student_id: str) -> Dict[str, Any]:
        """학생 답안 이미지 제출 및 채점 요청"""
        url = f"{self.base_url}/submission/"
        
        if not os.path.exists(image_path):
            return {"error": f"Image file not found: {image_path}"}
            
        async with aiohttp.ClientSession() as session:
            with open(image_path, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file',
                             f,
                             filename=os.path.basename(image_path),
                             content_type='image/png')
                data.add_field('problem_key', problem_key)
                data.add_field('student_id', student_id)
                
                try:
                    async with session.post(url, data=data) as response:
                        response.raise_for_status()
                        return await response.json()
                except aiohttp.ClientError as e:
                    print(f"Error submitting solution: {e}")
                    return {"error": str(e)}

    async def get_student_results(self, student_id: str) -> Dict[str, Any]:
        """학생의 모든 채점 결과 조회"""
        url = f"{self.base_url}/students/{student_id}"  # 변경된 엔드포인트
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                print(f"Error getting student results: {e}")
                return {"error": str(e)}

    async def register_grading_criteria(self, problem_key: str, criteria: Dict) -> Dict:
        """채점 기준 등록"""
        url = f"{self.base_url}/criteria/"
        
        payload = {
            "problem_key": problem_key,
            "total_points": criteria["배점"],
            "correct_answer": criteria["정답"],
            "detailed_criteria": [
                {
                    "item": item["항목"],
                    "points": item["배점"],
                    "description": item["설명"]
                }
                for item in criteria["세부기준"]
            ]
        }
        
        print(f"Sending payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        async with aiohttp.ClientSession() as session:
            try:
                headers = {"Content-Type": "application/json"}
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 422:
                        error_detail = await response.json()
                        print(f"Validation error: {error_detail}")
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                print(f"Error registering grading criteria: {e}")
                if hasattr(e, 'status'):
                    print(f"Status code: {e.status}")
                return {"error": str(e)}

    async def get_grading_result(self, grading_id: int) -> Dict[str, Any]:
        """특정 채점 결과 조회"""
        url = f"{self.base_url}/gradings/{grading_id}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                print(f"Error getting grading result: {e}")
                return {"error": str(e)}

    async def update_grading(self, grading_id: int, updates: Dict) -> Dict[str, Any]:
        """채점 결과 업데이트"""
        url = f"{self.base_url}/gradings/{grading_id}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.patch(url, json=updates) as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                print(f"Error updating grading: {e}")
                return {"error": str(e)}

    async def submit_batch_solutions(self, student_id: str, problem_files: List[Tuple[str, str]]) -> Dict[str, Any]:
        """여러 문항 동시 제출"""
        url = f"{self.base_url}/submission/batch"
        
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            data.add_field('student_id', student_id)
            
            # 파일 데이터를 메모리에 보관
            file_data = []
            for problem_key, image_path in problem_files:
                if not os.path.exists(image_path):
                    return {"error": f"Image file not found: {image_path}"}
                    
                # 파일을 메모리에 읽어두기
                with open(image_path, 'rb') as f:
                    file_content = f.read()
                    file_data.append((problem_key, os.path.basename(image_path), file_content))
            
            # 메모리에 있는 파일 데이터를 FormData에 추가
            for problem_key, filename, content in file_data:
                data.add_field('files',
                              content,
                              filename=filename,
                              content_type='image/png')
            
            try:
                async with session.post(url, data=data) as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                print(f"Error submitting batch solutions: {e}")
                return {"error": str(e)}

async def process_student(tester: GradingAPITester, folder: str) -> Tuple[str, Dict]:
    student_id = os.path.basename(folder)
    
    # 모든 문제 파일 찾기 및 정렬
    problem_files = []
    valid_problem_numbers = {'1', '2', '3', '4', '5'}  # 유효한 문항 번호
    
    for problem_file in sorted(os.listdir(folder)):
        if not os.path.isfile(os.path.join(folder, problem_file)) or \
           not problem_file.endswith(('.png', '.jpg', '.jpeg')):
            continue
            
        # 파일 이름에서 숫자만 추출
        numbers = re.findall(r'\d+', problem_file)
        if not numbers:
            logger.warning(f"Skipping file with no number in name: {problem_file}")
            continue
            
        problem_number = numbers[0]
        if problem_number not in valid_problem_numbers:
            if 'name' not in problem_file.lower():  # name 파일이 아닌 경우만 경고
                logger.warning(f"Skipping file with invalid problem number: {problem_file}")
            continue
            
        problem_key = f"문항{problem_number}"
        file_path = os.path.join(folder, problem_file)
        problem_files.append((problem_key, file_path))
    
    if not problem_files:
        logger.error(f"No valid problem files found in folder: {folder}")
        return student_id, {"error": "No valid problem files found"}
        
    logger.info(f"Found {len(problem_files)} valid problems for student {student_id}: {[pf[0] for pf in problem_files]}")
    
    # 재시도 로직 추가
    for attempt in range(3):
        try:
            result = await tester.submit_batch_solutions(student_id, problem_files)
            if "error" not in result:
                return student_id, {
                    problem_key: {"result": res}
                    for problem_key, res in zip([pf[0] for pf in problem_files], result)
                }
            elif attempt < 2:  # 마지막 시도가 아니면 재시도
                print(f"Attempt {attempt + 1} failed for {student_id}, retrying...")
                await asyncio.sleep(1)
            else:
                logger.error(f"Final attempt failed for {student_id}: {result['error']}")
                return student_id, {"error": result["error"]}
        except Exception as e:
            logger.error(f"Exception during processing for {student_id}: {e}")
            if attempt < 2:  # 마지막 시도가 아니면 재시도
                print(f"Attempt {attempt + 1} failed for {student_id}: {e}, retrying...")
                await asyncio.sleep(1)
            else:
                logger.error(f"All attempts failed for {student_id}: {e}")
                return student_id, {"error": str(e)}

async def main():
    try:
        tester = GradingAPITester()
        await register_all_criteria(tester)
        await asyncio.sleep(3)
        
        base_path = "image/students"
        student_folders = sorted([
            os.path.join(base_path, f) for f in os.listdir(base_path) 
            if os.path.isdir(os.path.join(base_path, f))
        ])
        
        # 세마포어로 동시 처리 학생 수 제한
        semaphore = asyncio.Semaphore(3)
        
        async def process_with_semaphore(folder):
            async with semaphore:
                print(f"\n>>> 처리 시작: {os.path.basename(folder)}")
                result = await process_student(tester, folder)
                print(f"<<< 처리 완료: {os.path.basename(folder)}")
                return result
        
        # 모든 학생 처리
        tasks = [process_with_semaphore(folder) for folder in student_folders]
        results = await asyncio.gather(*tasks)
        
        # 결과 저장
        results_dict = {
            student_id: result 
            for student_id, result in results 
            if isinstance(result, dict) and "error" not in result
        }
        
        if results_dict:
            with open("grading_results.json", 'w', encoding='utf-8') as f:
                json.dump(results_dict, f, ensure_ascii=False, indent=2)
                
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        raise

async def register_all_criteria(tester: GradingAPITester):
    """모든 채점 기준을 병렬로 등록"""
    with open('grading_criteria.json', 'r', encoding='utf-8') as f:
        criteria_data = json.load(f)
    
    print("\n=== 채점 기준 일괄 등록 시작 ===\n")
    
    # 모든 채점 기준을 동시에 등록
    tasks = [
        tester.register_grading_criteria(problem_key, criteria)
        for problem_key, criteria in criteria_data.items()
    ]
    
    # 병렬로 모든 등록 처리
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 결과 확인
    for (problem_key, _), result in zip(criteria_data.items(), results):
        if isinstance(result, Exception):
            print(f"❌ {problem_key} 등록 실패: {str(result)}")
        elif "error" in result:
            print(f"❌ {problem_key} 등록 실패: {result['error']}")
        else:
            print(f"✅ {problem_key} 등록 성공")
    
    print("\n=== 채점 기준 등록 완료 ===\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n테스트가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"테스트가 오류로 인해 중단되었습니다: {e}")
    finally:
        print("\n테스트 종료")