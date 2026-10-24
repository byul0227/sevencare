"""backend/.env 파일을 읽어 환경변수로 넣어요 (추가 패키지 없이).

- 형식: 한 줄에 KEY=값 (# 으로 시작하면 주석)
- 이미 터미널에서 넣은 환경변수가 있으면 그걸 우선해요.
- .env 는 .gitignore 에 들어 있어서 Git에 올라가지 않아요. API 키는 여기에만 넣어요.
"""
import os
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def load_env(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value
