"""건강 리포트 API — records 를 모아 추이·통계·경고를 계산해요.

GET  /api/pets/{id}/report          최근 N주 리포트
POST /api/pets/{id}/demo-history    (데모용) 지난 5주 기록 자동 생성
DELETE /api/pets/{id}/demo-history  (데모용) 자동 생성한 기록만 삭제
"""
import random
from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Pet, Record
from .pets import get_pet_or_404

router = APIRouter(prefix="/api/pets", tags=["report"])

DEMO_NOTE = "[데모] 자동 생성 기록"

# ---- 경고 규칙 기준값 ----
# 각 기준의 출처는 SOURCES 와 README '리포트 경고 규칙'에 정리했어요.
# 수의학 자료에 숫자가 없는 부분은 "서비스 자체 기준"으로 표시하고 이유를 적었어요.

# 체중: 5% 이상 감소 → 진단적 검사 고려, 10% 초과 감소 → 임상적으로 의미 있는 감소
WEIGHT_WARN_PCT = 5.0
WEIGHT_CRITICAL_PCT = 10.0

# 식사 거부: 24~48시간 이상 먹지 않으면 진료 권장 → 오늘+어제 식사가 모두 '거의 안먹음'
FOOD_REFUSAL_MAX_AMOUNT = 10   # 식사량 10% 이하 = '거의 안먹음'
FOOD_REFUSAL_MIN_MEALS = 2

# 식욕 감소: AAHA는 식욕 감소 자체를 연락 사유로 보지만 수치 기준은 없음 → 서비스 자체 기준
#   - 기간 3일: 먹지 못하면 3~5일 안에 영양 결핍의 악영향이 나타난다는 문헌의 하한
#   - 감소폭 20%: 개체별 평소 평균 대비 (서비스 자체 기준)
MEAL_RECENT_DAYS = 3
MEAL_DROP_RATIO = 0.8
MEAL_MIN_BASELINE = 5

# 혈변·흑색변: 한 번이라도 있으면 수의사에게 연락 권장. 7일은 알림을 보여주는 기간(서비스 기준)
POOP_ALERT_DAYS = 7
DARK_STOOL_COLORS = ("검붉은색",)   # AAHA: '검고 끈적한 변(black and tarry)'

# 무른 변: 2일 넘게 지속되면 진료 권장 → 3일 연속 '무름'
LOOSE_STOOL_DAYS = 3

SOURCES = {
    "weight_warn": ("Cortadellas, CEU Cardenal Herrera 대학 수의학과 (Schermerhorn 2017 인용)",
                    "https://vetsandclinics.com/en/library/weight-loss-in-elderly-dogs"),
    "weight_critical": ("VCA Animal Hospitals, Abnormal Weight Loss in Dogs",
                        "https://vcahospitals.com/know-your-pet/weight-loss-abnormal-in-dogs"),
    "food_refusal": ("PetMD, Dog Not Eating? (수의사 작성·감수)",
                     "https://www.petmd.com/dog/symptoms/why-my-dog-not-eating"),
    "meal_drop": ("AAHA 2023 Senior Care Guidelines, 보호자용 가정 모니터링 안내",
                  "https://www.aaha.org/wp-content/uploads/globalassets/02-guidelines/2023-aaha-senior-care-guidelines-for-dogs-and-cats/resources/aaha-senior-care-guidelines-your-senior-pet.pdf"),
    "poop_blood": ("AAHA 2023 Senior Care Guidelines, 보호자용 가정 모니터링 안내",
                   "https://www.aaha.org/wp-content/uploads/globalassets/02-guidelines/2023-aaha-senior-care-guidelines-for-dogs-and-cats/resources/aaha-senior-care-guidelines-your-senior-pet.pdf"),
    "loose_stool": ("VCA Animal Hospitals, Diarrhea in Dogs",
                    "https://vcahospitals.com/know-your-pet/diarrhea-in-dogs"),
}


# ---------------- 응답 스키마 ----------------
class WeightPoint(BaseModel):
    label: str                    # "4주 전" … "이번주"
    start: date
    end: date
    weight_kg: Optional[float]    # 그 주 평균 (기록 없으면 null)


class Alert(BaseModel):
    level: str                    # "warning" | "critical"
    code: str                     # weight_drop / food_refusal / meal_drop / poop_blood / loose_stool
    message: str
    source: str                   # 근거 자료 이름
    source_url: str


def _alert(level: str, code: str, source_key: str, message: str) -> Alert:
    name, url = SOURCES[source_key]
    return Alert(level=level, code=code, message=message, source=name, source_url=url)


class Report(BaseModel):
    pet_id: int
    start: date
    end: date
    weeks: int
    weight_series: list[WeightPoint]
    weight_change_pct: Optional[float]   # 첫 기록 대비 마지막 기록 변화율 (%)
    meal_avg_pct: Optional[int]          # 평균 식사량 (%)
    meal_count: int
    poop_normal_pct: Optional[int]       # 배변 정상 비율 (%) — 굳기 '정상' + 혈변 없음
    poop_count: int
    record_count: int
    alerts: list[Alert]


def _week_label(i: int, weeks: int) -> str:
    back = weeks - i
    return "이번주" if back == 0 else f"{back}주 전"


def _avg(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def build_report(db: Session, pet: Pet, weeks: int, today: Optional[date] = None) -> Report:
    today = today or date.today()
    # 버킷: 이번주(오늘 포함 최근 7일) + 이전 weeks 주 → weeks+1 개
    start = today - timedelta(days=7 * (weeks + 1) - 1)
    rows = db.scalars(
        select(Record)
        .where(
            Record.pet_id == pet.id,
            Record.recorded_at >= datetime.combine(start, time.min),
            Record.recorded_at < datetime.combine(today + timedelta(days=1), time.min),
        )
        .order_by(Record.recorded_at)
    ).all()

    weights = [r for r in rows if r.type == "weight"]
    meals = [r for r in rows if r.type == "meal"]
    poops = [r for r in rows if r.type == "poop"]

    # ---- 체중: 주별 평균 ----
    series = []
    for i in range(weeks + 1):
        b_start = start + timedelta(days=7 * i)
        b_end = b_start + timedelta(days=6)
        in_bucket = [w.weight_kg for w in weights if b_start <= w.recorded_at.date() <= b_end]
        avg = _avg(in_bucket)
        series.append(WeightPoint(
            label=_week_label(i, weeks), start=b_start, end=b_end,
            weight_kg=round(avg, 2) if avg is not None else None,
        ))

    weight_change = None
    if len(weights) >= 2 and weights[0].weight_kg:
        weight_change = round((weights[-1].weight_kg - weights[0].weight_kg) / weights[0].weight_kg * 100, 1)

    # ---- 식사 / 배변 통계 ----
    meal_avg = _avg([m.meal_amount for m in meals])
    poop_normal = (
        sum(1 for p in poops if p.poop_firmness == "정상" and not p.poop_blood) / len(poops)
        if poops else None
    )

    # ---- 경고 규칙 ----
    alerts: list[Alert] = []

    # 1) 체중 감소
    if weight_change is not None and weight_change <= -WEIGHT_WARN_PCT:
        drop = abs(weight_change)
        if drop > WEIGHT_CRITICAL_PCT:
            alerts.append(_alert("critical", "weight_drop", "weight_critical",
                f"그래프 기간 동안 체중이 {drop}% 줄었어요. 10%가 넘는 감소는 임상적으로 의미 있는 변화라 진료를 권해요."))
        else:
            alerts.append(_alert("warning", "weight_drop", "weight_warn",
                f"그래프 기간 동안 체중이 {drop}% 줄었어요. 5% 이상 줄면 원인 확인을 위한 검사가 필요할 수 있어요."))

    # 2) 식사 거부 (오늘+어제 모두 거의 안 먹음) → 이 경우 식욕 감소 경고는 생략
    last2 = [m.meal_amount for m in meals if m.recorded_at.date() >= today - timedelta(days=1)]
    refusing = len(last2) >= FOOD_REFUSAL_MIN_MEALS and all(a <= FOOD_REFUSAL_MAX_AMOUNT for a in last2)
    if refusing:
        alerts.append(_alert("critical", "food_refusal", "food_refusal",
            "어제부터 기록된 식사를 거의 먹지 않았어요. 24~48시간 넘게 먹지 않으면 진료를 받아보세요."))

    # 3) 식욕 감소 (개인 평균 대비)
    recent_from = today - timedelta(days=MEAL_RECENT_DAYS - 1)
    recent = [m.meal_amount for m in meals if m.recorded_at.date() >= recent_from]
    baseline = [m.meal_amount for m in meals if m.recorded_at.date() < recent_from]
    if not refusing and recent and len(baseline) >= MEAL_MIN_BASELINE:
        r_avg, b_avg = _avg(recent), _avg(baseline)
        if b_avg and r_avg <= b_avg * MEAL_DROP_RATIO:
            drop = round((1 - r_avg / b_avg) * 100)
            alerts.append(_alert("warning", "meal_drop", "meal_drop",
                f"최근 {MEAL_RECENT_DAYS}일간 식사량이 평소보다 {drop}% 줄었어요. 식욕 변화가 이어지면 수의사와 상담해 보세요."))

    # 4) 혈변·점액 / 검붉은 변
    alert_from = today - timedelta(days=POOP_ALERT_DAYS - 1)
    recent_poops = [p for p in poops if p.recorded_at.date() >= alert_from]
    blood = sum(1 for p in recent_poops if p.poop_blood)
    dark = sum(1 for p in recent_poops if p.poop_color in DARK_STOOL_COLORS)
    if blood or dark:
        parts = ([f"혈변·점액 {blood}번"] if blood else []) + ([f"검붉은 변 {dark}번"] if dark else [])
        alerts.append(_alert("critical", "poop_blood", "poop_blood",
            f"최근 {POOP_ALERT_DAYS}일 동안 {', '.join(parts)} 기록이 있어요. 수의사에게 연락해 보세요."))

    # 5) 무른 변 3일 연속 (어제나 오늘까지 이어진 경우)
    loose_days = {p.recorded_at.date() for p in poops if p.poop_firmness == "무름"}
    for end in (today, today - timedelta(days=1)):
        if all(end - timedelta(days=i) in loose_days for i in range(LOOSE_STOOL_DAYS)):
            alerts.append(_alert("warning", "loose_stool", "loose_stool",
                f"{LOOSE_STOOL_DAYS}일 연속 무른 변이 기록됐어요. 2일 넘게 이어지면 진료를 권해요."))
            break

    return Report(
        pet_id=pet.id, start=start, end=today, weeks=weeks,
        weight_series=series,
        weight_change_pct=weight_change,
        meal_avg_pct=round(meal_avg) if meal_avg is not None else None,
        meal_count=len(meals),
        poop_normal_pct=round(poop_normal * 100) if poop_normal is not None else None,
        poop_count=len(poops),
        record_count=len(rows),
        alerts=alerts,
    )


@router.get("/{pet_id}/report", response_model=Report)
def get_report(
    pet_id: int,
    weeks: int = Query(4, ge=1, le=12, description="이번주를 제외하고 몇 주 전까지 볼지"),
    db: Session = Depends(get_db),
):
    return build_report(db, get_pet_or_404(db, pet_id), weeks)


# ---------------- 데모 데이터 ----------------
class DemoResult(BaseModel):
    created: int = 0
    deleted: int = 0


def _clear_demo(db: Session, pet_id: int) -> int:
    result = db.execute(delete(Record).where(Record.pet_id == pet_id, Record.note == DEMO_NOTE))
    return result.rowcount or 0


@router.post("/{pet_id}/demo-history", response_model=DemoResult)
def create_demo_history(pet_id: int, days: int = Query(35, ge=7, le=84), db: Session = Depends(get_db)):
    """어제부터 거꾸로 N일치 기록을 만들어요. 오늘 기록과 직접 입력한 기록은 건드리지 않아요.

    노령견에게 흔한 패턴(체중이 서서히 줄고, 최근 며칠 식사량이 줄어드는 상황)을 흉내 내서
    리포트 경고가 어떻게 뜨는지 시연할 수 있게 했어요. 다시 누르면 기존 데모 기록을 지우고 새로 만들어요.
    """
    pet = get_pet_or_404(db, pet_id)
    deleted = _clear_demo(db, pet_id)
    rng = random.Random(pet_id)  # 같은 펫이면 항상 같은 데이터

    latest = db.scalar(
        select(Record.weight_kg).where(Record.pet_id == pet_id, Record.type == "weight")
        .order_by(Record.recorded_at.desc()).limit(1)
    )
    end_weight = latest or pet.weight_kg or 10.0
    start_weight = end_weight * 1.08  # 5주 동안 약 8% 감소

    today = date.today()
    new = []
    for back in range(days, 0, -1):
        day = today - timedelta(days=back)
        at = lambda h, m: datetime.combine(day, time(h, m))  # noqa: E731
        progress = (days - back) / days            # 0 → 1
        recent = back <= MEAL_RECENT_DAYS - 1      # 어제·그제: 식사량 감소 구간

        for h in (8, 18):
            amount = rng.choice([30, 50]) if recent else rng.choice([80, 100, 100])
            new.append(Record(pet_id=pet_id, type="meal", recorded_at=at(h, rng.randint(0, 30)),
                              meal_amount=amount, note=DEMO_NOTE))

        new.append(Record(pet_id=pet_id, type="poop", recorded_at=at(9, rng.randint(0, 50)),
                          poop_firmness="정상" if rng.random() < 0.85 else "무름",
                          poop_color="갈색", poop_blood=False, note=DEMO_NOTE))

        new.append(Record(pet_id=pet_id, type="med", recorded_at=at(9, 0),
                          med_name="관절 영양제", note=DEMO_NOTE))

        if back % 3 == 0:
            w = start_weight + (end_weight - start_weight) * progress + rng.uniform(-0.01, 0.01) * end_weight
            new.append(Record(pet_id=pet_id, type="weight", recorded_at=at(8, 0),
                              weight_kg=round(w, 1), note=DEMO_NOTE))

    db.add_all(new)
    db.commit()
    return DemoResult(created=len(new), deleted=deleted)


@router.delete("/{pet_id}/demo-history", response_model=DemoResult)
def delete_demo_history(pet_id: int, db: Session = Depends(get_db)):
    get_pet_or_404(db, pet_id)
    deleted = _clear_demo(db, pet_id)
    db.commit()
    return DemoResult(deleted=deleted)
