"""일일 기록(식사/배변/체중/투약) CRUD API."""
from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Record
from ..schemas import REQUIRED_BY_TYPE, RecordCreate, RecordOut, RecordType, RecordUpdate
from .pets import get_pet_or_404

router = APIRouter(prefix="/api", tags=["records"])


def get_record_or_404(db: Session, record_id: int) -> Record:
    rec = db.get(Record, record_id)
    if rec is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "기록을 찾을 수 없어요")
    return rec


@router.get("/pets/{pet_id}/records", response_model=list[RecordOut])
def list_records(
    pet_id: int,
    on: Optional[date] = Query(None, description="이 날짜(YYYY-MM-DD)의 기록만"),
    start: Optional[date] = Query(None, description="기간 시작일 (포함)"),
    end: Optional[date] = Query(None, description="기간 종료일 (포함)"),
    type: Optional[RecordType] = Query(None, description="meal / poop / weight / med"),
    db: Session = Depends(get_db),
):
    """최신순으로 반환. 홈 화면은 ?on=오늘날짜 로 호출해요."""
    get_pet_or_404(db, pet_id)
    stmt = select(Record).where(Record.pet_id == pet_id)
    if on is not None:
        start = end = on
    if start is not None:
        stmt = stmt.where(Record.recorded_at >= datetime.combine(start, time.min))
    if end is not None:
        stmt = stmt.where(Record.recorded_at < datetime.combine(end + timedelta(days=1), time.min))
    if type is not None:
        stmt = stmt.where(Record.type == type)
    stmt = stmt.order_by(Record.recorded_at.desc(), Record.id.desc())
    return db.scalars(stmt).all()


@router.post(
    "/pets/{pet_id}/records", response_model=RecordOut, status_code=status.HTTP_201_CREATED
)
def create_record(pet_id: int, body: RecordCreate, db: Session = Depends(get_db)):
    get_pet_or_404(db, pet_id)
    data = body.model_dump()
    if data["recorded_at"] is None:
        data["recorded_at"] = datetime.now()
    rec = Record(pet_id=pet_id, **data)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


@router.get("/records/{record_id}", response_model=RecordOut)
def get_record(record_id: int, db: Session = Depends(get_db)):
    return get_record_or_404(db, record_id)


@router.patch("/records/{record_id}", response_model=RecordOut)
def update_record(record_id: int, body: RecordUpdate, db: Session = Depends(get_db)):
    rec = get_record_or_404(db, record_id)
    changes = body.model_dump(exclude_unset=True)
    for required in (*REQUIRED_BY_TYPE[rec.type], "recorded_at"):
        if required in changes and changes[required] is None:
            raise HTTPException(422, f"{required} 값은 비울 수 없어요")
    for key, value in changes.items():
        setattr(rec, key, value)
    db.commit()
    db.refresh(rec)
    return rec


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(record_id: int, db: Session = Depends(get_db)):
    rec = get_record_or_404(db, record_id)
    db.delete(rec)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
