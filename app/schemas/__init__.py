import os
import importlib
from pathlib import Path

# 현재 디렉토리의 모든 .py 파일 조회
current_dir = Path(__file__).parent
py_files = [
    f.stem for f in current_dir.glob("*.py")
    if f.is_file() and f.stem != "__init__"
]

# 동적으로 모든 모듈 import하고 public 클래스들 가져오기
for module_name in py_files:
    module = importlib.import_module(f".{module_name}", package="app.schemas")
    # 모든 public 속성을 현재 네임스페이스로 가져오기
    for attr in dir(module):
        if not attr.startswith("_"):  # private이 아닌 것만 가져오기
            globals()[attr] = getattr(module, attr)

# 순환 참조 해결
from .student import StudentResponse
StudentResponse.update_forward_refs()