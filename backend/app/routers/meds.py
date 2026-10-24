"""투약 스케줄 API.

GET    /api/pets/{id}/medications            약 목록
POST   /api/pets/{id}/medications            약 등록
PATCH  /api/medications/{mid}                수정 (복용 중지는 active=false)
DELETE /api/medications/{mid}                삭제 (지난 복용 기록은 남아요)
GET    /api/pets/{id}/med-schedule?on=날짜   그날의 복용 체크리스트 + 알림
POST   /api/pets/{id}/med-schedule/check     슬롯 체크 → 투약 기록(records) 생성
체크 해제는 슬롯의 record_id 로 DELETE /api/records/{id}
"""
import re
from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..med_schedule import build_schedule, parse_times
from ..models import Medication, Record
from .pets import get_pet_or_404

router = APIRouter(prefix="/api", tags=["medications"])

TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _clean_times(v: list[str]) -> list[str]:
    if not v:
        raise ValueError("복용 시간을 하나 이상 넣어 주세요")
    for t in v:
        if not TIME_RE.match(t):
            raise ValueError(f"시간 형식이 올바르지 않아요: {t} (예: 09:00)")
    v = sorted(set(v))
    if len(v) > 6:
        raise ValueError("복용 시간은 하루 6번까지 넣을 수 있어요")
    return v


# ---------------- 스키마 ----------------
class MedicationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    dose: Optional[str] = Field(default=None, max_length=30)
    times: list[str]
    instructions: Optional[str] = Field(default=None, max_length=200)
    active: bool = True
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @field_validator("times")
    @classmethod
    def _times(cls, v):
        return _clean_times(v)


class MedicationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    dose: Optional[str] = Field(default=None, max_length=30)
    times: Optional[list[str]] = None
    instructions: Optional[str] = Field(default=None, max_length=200)
    active: Optional[bool] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @field_validator("times")
    @classmethod
    def _times(cls, v):
        return None if v is None else _clean_times(v)


class MedicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pet_id: int
    name: str
    dose: Optional[str]
    times: list[str]
    instructions: Optional[str]
    active: bool
    start_date: date
    end_date: Optional[date]


class SlotOut(BaseModel):
    medication_id: int
    name: str
    dose: Optional[str]
    instructions: Optional[str]
    time: str
    status: str
    record_id: Optional[int]
    taken_at: Optional[datetime]


class ScheduleAlert(BaseModel):
    level: str
    code: str
    message: str


class ScheduleOut(BaseModel):
    date: date
    slots: list[SlotOut]
    alerts: list[ScheduleAlert]


class CheckIn(BaseModel):
    medication_id: int
    time: str
    on: Optional[date] = None


# ---------------- 헬퍼 ----------------
def med_out(m: Medication) -> MedicationOut:
    return MedicationOut(
        id=m.id, pet_id=m.pet_id, name=m.name, dose=m.dose, times=parse_times(m.times),
        instructions=m.instructions, active=m.active, start_date=m.start_date, end_date=m.end_date,
    )


def get_med_or_404(db: Session, med_id: int) -> Medication:
    med = db.get(Medication, med_id)
    if med is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "약을 찾을 수 없어요")
    return med


def schedule_for(db: Session, pet_id: int, on: date) -> ScheduleOut:
    meds = db.scalars(select(Medication).where(Medication.pet_id == pet_id)).all()
    recs = db.scalars(
        select(Record).where(
            Record.pet_id == pet_id, Record.type == "med",
            Record.recorded_at >= datetime.combine(on, time.min),
            Record.recorded_at < datetime.combine(on + timedelta(days=1), time.min),
        )
    ).all()
    s = build_schedule(meds, recs, on, datetime.now())
    return ScheduleOut(
        date=s.date,
        slots=[SlotOut(**{k: getattr(x, k) for k in SlotOut.model_fields}) for x in s.slots],
        alerts=[ScheduleAlert(**a) for a in s.alerts],
    )


# ---------------- 약 CRUD ----------------
@router.get("/pets/{pet_id}/medications", response_model=list[MedicationOut])
def list_meds(pet_id: int, db: Session = Depends(get_db)):
    get_pet_or_404(db, pet_id)
    meds = db.scalars(select(Medication).where(Medication.pet_id == pet_id)
                      .order_by(Medication.active.desc(), Medication.id)).all()
    return [med_out(m) for m in meds]


@router.post("/pets/{pet_id}/medications", response_model=MedicationOut, status_code=status.HTTP_201_CREATED)
def create_med(pet_id: int, body: MedicationCreate, db: Session = Depends(get_db)):
    get_pet_or_404(db, pet_id)
    data = body.model_dump()
    data["times"] = ",".join(data["times"])
    data["start_date"] = data["start_date"] or date.today()
    if data["end_date"] and data["end_date"] < data["start_date"]:
        raise HTTPException(422, "종료일은 시작일보다 뒤여야 해요")
    med = Medication(pet_id=pet_id, **data)
    db.add(med)
    db.commit()
    db.refresh(med)
    return med_out(med)


@router.patch("/medications/{med_id}", response_model=MedicationOut)
def update_med(med_id: int, body: MedicationUpdate, db: Session = Depends(get_db)):
    med = get_med_or_404(db, med_id)
    changes = body.model_dump(exclude_unset=True)
    for required in ("name", "times", "active", "start_date"):
        if required in changes and changes[required] is None:
            raise HTTPException(422, f"{required} 값은 비울 수 없어요")
    if "times" in changes:
        changes["times"] = ",".join(changes["times"])
    for k, v in changes.items():
        setattr(med, k, v)
    if med.end_date and med.end_date < med.start_date:
        raise HTTPException(422, "종료일은 시작일보다 뒤여야 해요")
    db.commit()
    db.refresh(med)
    return med_out(med)


@router.delete("/medications/{med_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_med(med_id: int, db: Session = Depends(get_db)):
    db.delete(get_med_or_404(db, med_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------- 오늘의 체크리스트 ----------------
@router.get("/pets/{pet_id}/med-schedule", response_model=ScheduleOut)
def get_schedule(pet_id: int, on: Optional[date] = Query(None, description="기본값: 오늘"), db: Session = Depends(get_db)):
    get_pet_or_404(db, pet_id)
    return schedule_for(db, pet_id, on or date.today())


@router.post("/pets/{pet_id}/med-schedule/check", response_model=ScheduleOut)
def check_slot(pet_id: int, body: CheckIn, db: Session = Depends(get_db)):
    """슬롯을 '복용 완료'로 체크. 그 약·그 시간으로 투약 기록을 만들어요."""
    get_pet_or_404(db, pet_id)
    med = get_med_or_404(db, body.medication_id)
    if med.pet_id != pet_id or body.time not in parse_times(med.times):
        raise HTTPException(422, "스케줄에 없는 복용 시간이에요")
    on = body.on or date.today()
    current = schedule_for(db, pet_id, on)
    if any(s.medication_id == med.id and s.time == body.time and s.record_id for s in current.slots):
        return current  # 이미 체크됨 (두 번 눌러도 중복 기록이 생기지 않게)
    hh, mm = map(int, body.time.split(":"))
    db.add(Record(pet_id=pet_id, type="med", med_name=med.name,
                  recorded_at=datetime.combine(on, time(hh, mm)), note="투약 스케줄에서 체크"))
    db.commit()
    return schedule_for(db, pet_id, on)
