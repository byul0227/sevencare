"""병원 지참용 리포트 데이터 (한 번에 모아서 내려줘요).

GET /api/pets/{id}/vet-summary?weeks=4

화면(프론트)이 이 데이터로 인쇄용 페이지를 그리고, 브라우저의 '인쇄 → PDF로 저장'으로 PDF를 만들어요.
(서버에서 PDF를 만들면 한글 글꼴 설정이 PC마다 달라져서, 브라우저 인쇄 방식을 택했어요.)
"""
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..med_schedule import build_schedule, is_active_on, parse_times
from ..models import CareCheck, Medication, Record, VetVisit
from .care import to_out as care_out
from .pets import get_pet_or_404, to_out as pet_out
from .report import build_report

router = APIRouter(prefix="/api", tags=["summary"])

ADHERENCE_DAYS = 14   # 복용률을 계산하는 기간
NOTABLE_DAYS = 14     # '특이 기록'을 모으는 기간


def _day_range(d: date):
    return datetime.combine(d, time.min), datetime.combine(d + timedelta(days=1), time.min)


def medication_adherence(db: Session, pet_id: int, today: date, now: datetime) -> list[dict]:
    """최근 14일 약별 복용률. 오늘은 이미 시간이 지난 슬롯만 세요."""
    meds = db.scalars(select(Medication).where(Medication.pet_id == pet_id)).all()
    start = today - timedelta(days=ADHERENCE_DAYS - 1)
    recs = db.scalars(select(Record).where(
        Record.pet_id == pet_id, Record.type == "med",
        Record.recorded_at >= datetime.combine(start, time.min),
        Record.recorded_at < datetime.combine(today + timedelta(days=1), time.min),
    )).all()

    stats = {m.id: {"taken": 0, "total": 0} for m in meds}
    for i in range(ADHERENCE_DAYS):
        d = start + timedelta(days=i)
        lo, hi = _day_range(d)
        day_recs = [r for r in recs if lo <= r.recorded_at < hi]
        for slot in build_schedule(meds, day_recs, d, now).slots:
            if d == today and slot.status in ("due", "upcoming"):
                continue  # 아직 먹일 시간이 안 됐거나 지금 먹일 시간
            stats[slot.medication_id]["total"] += 1
            if slot.status == "taken":
                stats[slot.medication_id]["taken"] += 1

    out = []
    for m in meds:
        if not is_active_on(m, today):
            continue
        s = stats[m.id]
        out.append({
            "name": m.name, "dose": m.dose, "times": parse_times(m.times), "instructions": m.instructions,
            "start_date": m.start_date,
            "taken": s["taken"], "total": s["total"],
            "adherence_pct": round(s["taken"] / s["total"] * 100) if s["total"] else None,
        })
    return out


def notable_records(db: Session, pet_id: int, today: date) -> list[dict]:
    """최근 2주 중 수의사가 볼 만한 기록: 혈변·검붉은 변·무른 변, 거의 안 먹은 식사, 메모가 있는 기록."""
    since = datetime.combine(today - timedelta(days=NOTABLE_DAYS - 1), time.min)
    recs = db.scalars(select(Record).where(Record.pet_id == pet_id, Record.recorded_at >= since)
                      .order_by(Record.recorded_at.desc())).all()
    out = []
    for r in recs:
        user_note = r.note if r.note and not r.note.startswith("[데모]") and r.note != "투약 스케줄에서 체크" else None
        reason = None
        if r.type == "poop" and (r.poop_blood or r.poop_color == "검붉은색"):
            reason = "혈변·점액" if r.poop_blood else "검붉은 변"
        elif r.type == "poop" and r.poop_firmness in ("무름", "딱딱함"):
            reason = f"변 {r.poop_firmness}"
        elif r.type == "meal" and r.meal_amount is not None and r.meal_amount <= 10:
            reason = "거의 안 먹음"
        if reason or user_note:
            out.append({"recorded_at": r.recorded_at, "type": r.type, "reason": reason, "note": user_note})
    return out[:30]


@router.get("/pets/{pet_id}/vet-summary")
def vet_summary(pet_id: int, weeks: int = Query(4, ge=1, le=12), db: Session = Depends(get_db)):
    pet = get_pet_or_404(db, pet_id)
    today, now = date.today(), datetime.now()

    care = {}
    for kind in ("cognitive", "qol", "bcs", "mobility"):
        c = db.scalar(select(CareCheck).where(CareCheck.pet_id == pet_id, CareCheck.kind == kind)
                      .order_by(CareCheck.checked_at.desc(), CareCheck.id.desc()).limit(1))
        care[kind] = care_out(c) if c else None

    visits = db.scalars(select(VetVisit).where(VetVisit.pet_id == pet_id)
                        .order_by(VetVisit.visit_date.desc(), VetVisit.id.desc()).limit(5)).all()
    upcoming = db.scalars(select(VetVisit).where(VetVisit.pet_id == pet_id, VetVisit.next_visit_date >= today)
                          .order_by(VetVisit.next_visit_date)).first()

    return {
        "generated_at": now,
        "pet": pet_out(db, pet),
        "report": build_report(db, pet, weeks),
        "medications": medication_adherence(db, pet_id, today, now),
        "adherence_days": ADHERENCE_DAYS,
        "care": care,
        "visits": [
            {"visit_date": v.visit_date, "category": v.category, "title": v.title, "hospital": v.hospital,
             "diagnosis": v.diagnosis, "treatment": v.treatment}
            for v in visits
        ],
        "next_visit": {"date": upcoming.next_visit_date, "title": upcoming.title} if upcoming else None,
        "notable_records": notable_records(db, pet_id, today),
        "notable_days": NOTABLE_DAYS,
    }
