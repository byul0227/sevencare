"""세븐케어 API 진입점.

실행: (backend 폴더에서)  uvicorn app.main:app --reload
문서: http://localhost:8000/docs

배포용:
- frontend/dist (npm run build 결과)가 있으면 이 서버가 화면까지 함께 보여줘요 → 주소 하나로 접속
- SEVENCARE_DEMO_SEED=1 이면 DB가 비어 있을 때 시연용 데모 데이터를 자동으로 넣어요
"""
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .env import load_env

load_env()  # backend/.env (API 키 등) — 다른 모듈보다 먼저 읽어요

from .database import Base, engine  # noqa: E402
from .routers import ai, care, food, meds, pets, photos, play, records, report, summary, visits # noqa: E402


def _auto_seed():
    """배포 서버에서 DB가 비어 있으면 데모 데이터를 넣어요 (무료 서버는 재시작하면 DB가 초기화돼서)."""
    try:
        from fastapi.testclient import TestClient

        from seed_demo import seed  # backend/seed_demo.py
        client = TestClient(app)
        if client.get("/api/pets").json():
            return

        def call(method, path, body=None):
            r = client.request(method, "/api" + path, json=body)
            r.raise_for_status()
            return r.json() if r.content else None

        seed(call)
    except Exception as e:  # 시드 실패해도 서버는 계속 떠 있게
        print(f"[demo seed] 실패: {e!r}")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)  # 테이블이 없으면 생성
    if os.getenv("SEVENCARE_DEMO_SEED") == "1":
        threading.Thread(target=_auto_seed, daemon=True).start()
    yield


app = FastAPI(title="세븐케어 API", version="0.1.0", lifespan=lifespan)

# 개발 중엔 Vite 프록시를 쓰지만, 직접 호출할 때를 위해 CORS도 열어둬요
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pets.router)
app.include_router(records.router)
app.include_router(report.router)
app.include_router(care.router)
app.include_router(meds.router)
app.include_router(visits.router)
app.include_router(ai.router)
app.include_router(summary.router)
app.include_router(photos.router)
app.include_router(play.router)
app.include_router(food.router)


@app.get("/api/health")
def health():
    return {"ok": True}


# ---------------- 화면(프론트엔드) 함께 제공 ----------------
DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if DIST.is_dir():
    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "없는 API예요")
        f = (DIST / path).resolve()
        if path and f.is_file() and DIST in f.parents:
            return FileResponse(f)
        return FileResponse(DIST / "index.html")  # 그 외 주소는 앱 첫 화면으로
