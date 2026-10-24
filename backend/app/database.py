"""SQLite 연결 설정.

DB 파일 위치는 환경변수 SEVENCARE_DB_URL 로 바꿀 수 있어요.
기본값: backend/sevencare.db
"""
import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_URL = f"sqlite:///{BASE_DIR / 'sevencare.db'}"
DATABASE_URL = os.getenv("SEVENCARE_DB_URL", DEFAULT_DB_URL)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # FastAPI는 여러 스레드에서 세션을 씀
)


@event.listens_for(engine, "connect")
def _enable_sqlite_fk(dbapi_conn, _):
    # SQLite는 기본적으로 FK 제약이 꺼져 있어서 켜줘야 ON DELETE CASCADE가 동작해요
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
