"""데모용 샘플 데이터 넣기 (디자인 레퍼런스의 초코·보리).

실행: (backend 폴더에서)  python -m app.seed
이미 펫이 있으면 아무것도 하지 않아요. 초기화하려면 sevencare.db 파일을 지우고 다시 실행하세요.
"""
from datetime import datetime, timedelta

from sqlalchemy import func, select

from .database import Base, SessionLocal, engine
from .models import Pet, Record


def run() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(func.count(Pet.id))):
            print("이미 펫 데이터가 있어서 건너뛰어요.")
            return

        choco = Pet(
            name="초코", breed="골든리트리버", age_years=14, gender="수컷",
            weight_kg=24.1, condition="슬개골 탈구 2기", hospital="노원동물병원",
        )
        bori = Pet(
            name="보리", breed="말티즈", age_years=11, gender="암컷", neutered=True,
            weight_kg=4.3, hospital="노원동물병원",
        )
        db.add_all([choco, bori])
        db.flush()

        today = datetime.now().replace(second=0, microsecond=0)
        at = lambda h, m, days_ago=0: (today - timedelta(days=days_ago)).replace(hour=h, minute=m)  # noqa: E731

        db.add_all([
            Record(pet_id=choco.id, type="meal", recorded_at=at(8, 10), meal_amount=100),
            Record(pet_id=choco.id, type="med", recorded_at=at(9, 0), med_name="관절 영양제"),
            # 지난 기록 (리포트 탭에서 쓸 예정)
            Record(pet_id=choco.id, type="weight", recorded_at=at(9, 0, 7), weight_kg=24.4),
            Record(pet_id=choco.id, type="weight", recorded_at=at(9, 0, 1), weight_kg=24.1),
        ])
        db.commit()
        print("초코, 보리 샘플 데이터를 넣었어요.")


if __name__ == "__main__":
    run()
